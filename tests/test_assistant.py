import json
import re
from pathlib import Path

import pytest

from rag import llm
from rag.assistant import Assistant
from rag.guardrails import detect_pii

ALLOWED_HOSTS = ("amc.ppfas.com", "www.sebi.gov.in", "www.amfiindia.com", "www.mutualfundssahihai.com")


@pytest.fixture(scope="module")
def bot():
    return Assistant()


def sentences(t):
    return len([s for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s])


@pytest.mark.parametrize("q,expect_url_part,expect_text", [
    ("Expense ratio of Parag Parikh Flexi Cap Fund?", "digital-factsheet", "1.05%"),
    ("ELSS lock-in?", "elss-tax-saver-fund/scheme-facts", "3 years"),
    ("Minimum SIP for the ELSS fund?", "elss-tax-saver-fund/scheme-facts", "₹1,000"),
    ("Exit load of liquid fund", "parag-parikh-liquid-fund", "0.0070%"),
    ("Benchmark of the large cap fund", "large-cap-fund/scheme-facts", "Nifty 100 TRI"),
    ("Riskometer of Parag Parikh Liquid Fund", "digital-factsheet", "Low to Moderate"),
    ("How do I download my capital-gains statement?", "mutualfundssahihai", "CAMS"),
    ("Account statement?", "statement-via-missed-call", "missed call"),
])
def test_factual_answers(bot, q, expect_url_part, expect_text):
    r = bot.ask(q)
    assert r.kind == "answer"
    assert expect_url_part in r.source_url
    assert expect_text in r.text


@pytest.mark.parametrize("q", [
    "Should I buy Parag Parikh Flexi Cap?",
    "Which is better, ELSS or flexi cap?",
    "Is it a good time to invest in the liquid fund?",
    "Recommend a fund for my portfolio",
])
def test_advice_refused(bot, q):
    r = bot.ask(q)
    assert r.kind == "refusal_advice"
    assert "mutualfundssahihai" in r.source_url


@pytest.mark.parametrize("q", ["My PAN is ABCDE1234F", "aadhaar 1234 5678 9012", "call 9876543210",
                               "mail me at a@b.com", "my OTP is 445566", "folio no 12345678"])
def test_pii_refused(bot, q):
    assert detect_pii(q)
    assert bot.ask(q).kind == "refusal_pii"


def test_no_false_pii_on_amounts():
    assert not detect_pii("Is the minimum SIP ₹1000 or ₹5000 for the liquid fund?")


def test_performance_goes_to_factsheet(bot):
    r = bot.ask("What are the 3 year returns of the flexi cap fund?")
    assert r.kind == "performance" and "factsheet" in r.source_url
    assert "%" not in r.text


def test_clarify_when_scheme_missing(bot):
    assert bot.ask("What is the exit load?").kind == "clarify"


def test_every_reply_has_one_official_link_and_short_text(bot):
    qs = ["Expense ratio of ELSS", "lock in large cap", "what is a riskometer", "who is the CEO of Groww?",
          "Should I sell?", "HDFC flexi cap exit load", "top holdings of flexi cap", ""]
    for q in qs:
        r = bot.ask(q)
        assert r.source_url.startswith("https://") and any(h in r.source_url for h in ALLOWED_HOSTS)
        assert sentences(r.text) <= 3, (q, r.text)
        md = r.as_markdown()
        assert md.count("](http") == 1 and "Last updated from sources:" in md


def test_corpus_chunks_are_short_and_sourced():
    corpus = json.loads((Path(__file__).parent.parent / "data/corpus.json").read_text())
    for c in corpus:
        assert sentences(c["text"]) <= 3, c["id"]
        assert c["source"].startswith("S")


def test_llm_validation_rejects_invented_numbers():
    ctx = "The base expense ratio is 1.05% for the Regular Plan and 0.53% for the Direct Plan."
    assert llm.validate("The Direct Plan expense ratio is 0.53%.", ctx)
    assert not llm.validate("The Direct Plan expense ratio is 0.50%.", ctx)
    assert not llm.validate("It is low, so you should invest.", ctx)
    assert not llm.validate("NOT_IN_CONTEXT", ctx)
