"""Small-corpus retriever: rule-based scheme/topic routing + TF-IDF ranking.

The corpus is ~40 hand-verified chunks, each tied to exactly one official URL.
Routing on (scheme, topic) gives precise hits for the common questions; TF-IDF
handles phrasing it doesn't anticipate. Each chunk carries its own source, so
whatever chunk wins, the citation is correct by construction.
"""
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA = Path(__file__).resolve().parent.parent / "data"

SCHEME_ALIASES = {
    "flexi": ["flexi cap", "flexicap", "flexi-cap", "flexi", "ppfcf", "long term equity"],
    "elss": ["elss", "tax saver", "taxsaver", "tax saving", "pptsf", "80c fund"],
    "largecap": ["large cap", "largecap", "large-cap", "pplcf", "bluechip"],
    "liquid": ["liquid", "pplf"],
}
SCHEME_NAMES = {
    "flexi": "Parag Parikh Flexi Cap Fund",
    "elss": "Parag Parikh ELSS Tax Saver Fund",
    "largecap": "Parag Parikh Large Cap Fund",
    "liquid": "Parag Parikh Liquid Fund",
}

TOPIC_KEYWORDS = {
    "expense_ratio": ["expense ratio", "expense", "ter", "charges", "fee", "fees", "cost"],
    "exit_load": ["exit load", "exit-load", "load", "redemption charge", "penalty", "exit fee"],
    "lock_in": ["lock-in", "lock in", "lockin", "locked", "lock period"],
    "min_sip": ["sip", "systematic investment"],
    "min_lumpsum": ["lump sum", "lumpsum", "lump-sum", "minimum investment", "minimum amount",
                    "one-time", "one time", "minimum purchase", "min investment", "purchase"],
    "riskometer": ["riskometer", "risk-o-meter", "risk o meter", "risk level", "risky", "risk"],
    "benchmark": ["benchmark", "index", "tri"],
    "capital_gains": ["capital gain", "capital-gain", "capital gains", "tax statement", "tax report"],
    "statement": ["statement", "account statement", "cas", "download"],
    "tax_80c": ["80c", "tax benefit", "tax deduction", "deduction", "tax saving", "save tax",
                "save", "tax", "old regime"],
    "factsheet": ["factsheet", "holdings", "portfolio", "aum", "fund manager", "fund managers", "managed by",
                  "manages", "manager", "managers"],
    "documents": ["kim", "sid", "scheme information document", "key information memorandum",
                  "offer document", "sai"],
    "redemption": ["insta", "instant redemption", "instant", "redeem", "redemption", "withdraw"],
    "category": ["category", "type of scheme", "type of fund", "what kind"],
}


@dataclass
class Chunk:
    id: str
    scheme: str
    topics: list
    source: str
    as_of: str
    text: str
    url: str
    title: str
    publisher: str


@dataclass
class Hit:
    chunk: Chunk
    score: float


def _contains(q: str, phrase: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", q) is not None


def detect_schemes(query: str):
    q = query.lower()
    found = []
    for key, aliases in SCHEME_ALIASES.items():
        positions = [q.find(a) for a in aliases if _contains(q, a)]
        if positions:
            found.append((min(positions), key))
    return [k for _, k in sorted(found)]


def detect_topics(query: str):
    q = query.lower()
    # scheme names contain topic words ("ELSS *Tax Saver*"): blank them out first
    for aliases in SCHEME_ALIASES.values():
        for a in aliases:
            q = re.sub(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])", " ", q)
    topics = [t for t, kws in TOPIC_KEYWORDS.items() if any(_contains(q, k) for k in kws)]
    # "minimum SIP" vs plain "minimum": a bare "minimum" means lump sum + SIP both live in min_* chunks
    if "minimum" in q and not any(t in topics for t in ("min_sip", "min_lumpsum")):
        topics.append("min_lumpsum")
    # capital-gains questions are a more specific kind of statement question
    if "capital_gains" in topics and "statement" in topics:
        topics.remove("statement")
    # "exit load" also matches "load"; "lock-in" questions shouldn't pull exit load unless asked
    return topics


class Retriever:
    def __init__(self):
        sources = {}
        with open(DATA / "sources.csv", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                sources[row["id"]] = row
        raw = json.loads((DATA / "corpus.json").read_text(encoding="utf-8"))
        self.chunks = []
        for r in raw:
            s = sources[r["source"]]
            self.chunks.append(Chunk(r["id"], r["scheme"], r["topics"], r["source"], r["as_of"],
                                     r["text"], s["url"], s["title"], s["publisher"]))
        self.sources = sources
        docs = [f"{c.text} {' '.join(c.topics).replace('_', ' ')} {SCHEME_NAMES.get(c.scheme, '')}"
                for c in self.chunks]
        self.vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
        self.matrix = self.vec.fit_transform(docs)

    def source(self, sid: str):
        return self.sources[sid]

    def search(self, query: str, k: int = 3):
        schemes = detect_schemes(query)
        topics = detect_topics(query)
        sims = cosine_similarity(self.vec.transform([query]), self.matrix)[0]
        hits = []
        for c, sim in zip(self.chunks, sims):
            score = float(sim)
            matched = set(c.topics) & set(topics)
            topic_match = bool(matched)
            score += 1.0 * len(matched)          # answers covering more of the asked facts win
            if topics and c.topics[0] in topics:
                score += 0.2                     # a chunk whose main topic is the asked one wins ties
            if schemes:
                if c.scheme == schemes[0]:
                    # right scheme but wrong topic shouldn't beat a general chunk on the right topic
                    score += 1.0 if (topic_match or not topics) else 0.3
                elif c.scheme != "general":
                    score -= 1.0
            elif c.scheme == "general":
                score += 0.3  # no scheme named: prefer general explainers
            # ELSS lock-in / 80C without naming a PPFAS scheme -> generic ELSS facts are fine
            hits.append(Hit(c, score))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k], schemes, topics
