"""The answer pipeline: guardrails -> route -> retrieve -> (optional LLM) -> cite.

Every reply carries exactly one source link and a "Last updated from sources" date.
"""
import re
from dataclasses import dataclass
from datetime import date

from . import guardrails, llm
from .retriever import SCHEME_NAMES, TOPIC_KEYWORDS, Retriever, _contains

DISCLAIMER = "Facts-only. No investment advice."

# Topics whose answer differs by scheme: we must know which scheme before answering.
SCHEME_REQUIRED = {"expense_ratio", "exit_load", "min_sip", "min_lumpsum", "benchmark",
                   "redemption", "documents", "category"}
DEFINITION_RE = re.compile(r"^\s*(what is|what's|what are|define|explain|meaning of)\b", re.I)
MIN_SCORE = 0.9  # below this the corpus doesn't really cover the question


@dataclass
class Reply:
    kind: str          # answer | refusal_advice | refusal_pii | performance | clarify | out_of_scope | no_answer
    text: str
    source_title: str
    source_url: str
    as_of: str
    mode: str = "rules"

    def as_markdown(self):
        return (f"{self.text}\n\n**Source:** [{self.source_title}]({self.source_url})  \n"
                f"*Last updated from sources: {fmt_date(self.as_of)}*")


def focus(text, topics):
    """Extractive W1 step: keep only the sentences that carry the fact asked for.

    Applied when exactly one topic is detected (e.g. 'minimum SIP' keeps the SIP
    sentence, drops the lump-sum one). If nothing matches, return the chunk as is.
    """
    if len(topics) != 1:
        return text
    kws = TOPIC_KEYWORDS.get(topics[0], [])
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    keep = [x for x in sents if any(_contains(x.lower(), k) for k in kws)]
    return " ".join(keep) if keep else text


def fmt_date(iso):
    d = date.fromisoformat(iso)
    return d.strftime("%d %b %Y").lstrip("0")


class Assistant:
    def __init__(self):
        self.r = Retriever()
        self.today = "2026-11-03"  # date the corpus was last pulled from source pages

    def _reply_from_source(self, kind, text, sid, as_of=None, mode="rules"):
        s = self.r.source(sid)
        return Reply(kind, text, s["title"], s["url"], as_of or self.today, mode)

    def ask(self, question: str) -> Reply:
        q = (question or "").strip()
        if not q:
            return self._reply_from_source("clarify", "Ask me a factual question about a PPFAS scheme, e.g. the exit load of Parag Parikh Flexi Cap Fund.", "S11")

        # 1. PII: refuse and never echo or store the details
        pii = guardrails.detect_pii(q)
        if pii:
            return self._reply_from_source(
                "refusal_pii",
                "Please don't share personal details like PAN, Aadhaar, account or folio numbers, OTPs, phone numbers or emails here — "
                "I haven't stored your message. I can only answer general facts about the schemes; for your own holdings, use the AMC's statement services.",
                "S16")

        # 2. Advice / opinion: polite refusal + educational link
        if guardrails.is_advice(q):
            return self._reply_from_source(
                "refusal_advice",
                "I can only share facts from official documents, so I can't say whether to buy, sell, hold or pick a scheme. "
                "AMFI's investor-education guide explains how to think about scheme types and risk, and a SEBI-registered adviser can help with a personal decision.",
                "S19")

        # 3. Performance: never quote or compare returns -> point to the official factsheet
        if guardrails.is_performance(q):
            return self._reply_from_source(
                "performance",
                "I don't quote, calculate or compare returns or NAVs. The official monthly factsheet shows each scheme's performance against its benchmark, and the latest NAV is published on the AMC and AMFI websites.",
                "S09")

        # 4. Other AMCs are out of scope
        if guardrails.is_other_amc(q):
            return self._reply_from_source(
                "out_of_scope",
                "I only cover four PPFAS Mutual Fund schemes: Parag Parikh Flexi Cap, ELSS Tax Saver, Large Cap and Liquid Fund. "
                "For other fund houses, please check that AMC's own KIM/SID.",
                "S11")

        hits, schemes, topics = self.r.search(q)
        top = hits[0]

        # 5. Scheme-specific fact but no scheme named -> ask which one
        if not schemes and set(topics) & SCHEME_REQUIRED and top.chunk.scheme != "general":
            topic = sorted(set(topics) & SCHEME_REQUIRED)[0].replace("_", " ").replace("min ", "minimum ")
            return self._reply_from_source(
                "clarify",
                f"Which scheme do you mean? The {topic} differs by scheme — I cover Parag Parikh Flexi Cap, ELSS Tax Saver, Large Cap and Liquid Fund.",
                "S11")

        if top.score < MIN_SCORE:
            return self._reply_from_source(
                "no_answer",
                "I couldn't find that in my official sources for these PPFAS schemes. The scheme's KIM/SID is the most complete reference.",
                "S11")

        c = top.chunk
        answer, mode = llm.rewrite(q, c.text)
        text = answer or focus(c.text, topics)
        # If two schemes are named we answer the first one only: one answer, one citation.
        return Reply("answer", text, c.title, c.url, c.as_of, mode)
