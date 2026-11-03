"""Input guardrails: PII, advice, performance and scope checks.

Every check is rule-based so the decision to answer vs. refuse is
deterministic and testable (W1: decide answer vs. refuse before retrieval).
"""
import re

# ---------- PII ----------
PII_PATTERNS = {
    "PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I),
    "Aadhaar": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    "phone number": re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "OTP": re.compile(r"\botp\b\D{0,15}\d{4,8}|\b\d{4,8}\b\D{0,10}\botp\b", re.I),
    "account/folio number": re.compile(
        r"(?:folio|a/?c|account)\s*(?:no\.?|number|#)?\s*[:#-]?\s*\d{5,}|\b\d{9,18}\b", re.I
    ),
}


def detect_pii(text: str):
    """Return the list of PII types found (empty list if none)."""
    return [label for label, pat in PII_PATTERNS.items() if pat.search(text)]


# ---------- Advice / opinion ----------
ADVICE_PATTERNS = [
    r"\bshould (i|we|one)\b",
    r"\bshall i\b",
    r"\b(buy|sell|hold)\b",
    r"\bis (it|this|this fund|.*fund) (a )?(good|bad|safe|worth)",
    r"\bworth (it|investing|buying)\b",
    r"\bgood (time|fund|investment|option|choice)\b",
    r"\b(recommend|suggest|advise|advice)\b",
    r"\b(better|best|safest|ideal)\b",
    r"\bright (scheme|fund|choice|time)\b",
    r"\bwhich (one|fund|scheme)\b",
    r"\bmy portfolio\b",
    r"\ballocat",
    r"\bhow much (should|to|can) i invest\b",
    r"\b(will|would|could) (it|the fund|nav) (go|grow|rise|fall|give|beat|double)",
    r"\b(predict|forecast|outlook|target)\b",
    r"\b(redeem|exit|switch|stop|start) (now|today|or not)\b",
]
ADVICE_RE = re.compile("|".join(ADVICE_PATTERNS), re.I)

# ---------- Performance ----------
PERF_RE = re.compile(
    r"\b(returns?|performance|performed|cagr|xirr|yield|gains? (in|over|last)|"
    r"how much (did|has) it (made|make|grow|earn)|outperform|underperform|nav (growth|history|today)|"
    r"current nav|latest nav|\bnav\b)\b",
    re.I,
)

# ---------- Out-of-scope AMCs ----------
OTHER_AMC_RE = re.compile(
    r"\b(hdfc|sbi|icici|axis|kotak|nippon|mirae|uti|tata|quant|motilal|dsp|aditya birla|"
    r"franklin|canara|edelweiss|invesco|bandhan|hsbc|groww mutual|navi|zerodha fund|whiteoak)\b"
    r"(?!.*parag parikh)",
    re.I,
)


def is_advice(text: str) -> bool:
    return bool(ADVICE_RE.search(text))


def is_performance(text: str) -> bool:
    return bool(PERF_RE.search(text))


def is_other_amc(text: str) -> bool:
    return bool(OTHER_AMC_RE.search(text))
