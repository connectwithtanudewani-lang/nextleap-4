# MF Facts — a facts-only FAQ assistant for PPFAS schemes

**Product track:** Groww · **AMC:** PPFAS Mutual Fund (Parag Parikh) · **Milestone 1:** Mutual Fund FAQs (facts-only Q&A)

A small RAG assistant that answers factual questions — expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, statements — from **21 official AMC / AMFI / SEBI pages**. Every answer is ≤3 sentences, cites exactly one source link, and ends with *Last updated from sources: <date>*. It refuses advice, never quotes returns, and never accepts PII.

**Live prototype:** https://nextleap-4-ppfas-mf-facts.streamlit.app/

## Scope

| Scheme | SEBI category | Why it's in the corpus |
|---|---|---|
| Parag Parikh Flexi Cap Fund | Flexi Cap | Graded exit load (10% free units, 2% / 1% / nil) |
| Parag Parikh ELSS Tax Saver Fund | ELSS | 3-year lock-in per instalment, Sec 80C |
| Parag Parikh Large Cap Fund | Large Cap | New scheme (Feb 2026), Nifty 100 TRI |
| Parag Parikh Liquid Fund | Liquid | Day-wise graded exit load, insta redemption |

Facts are as published on the source pages on **3 Nov 2026**; factsheet figures (expense ratio, riskometer, benchmark) are **as of 30 Sep 2026**.

## How it works

```
question
  └─ 1. Guardrails (rules, before any retrieval)
       PII (PAN, Aadhaar, phone, email, OTP, account/folio no.) → refuse, mask, store nothing
       Advice / opinion ("should I", "better", "recommend")      → polite refusal + AMFI education link
       Returns / NAV / performance                              → no numbers, link to official factsheet
       Other AMCs                                               → out of scope
  └─ 2. Route: detect scheme (aliases) + topic (keyword map)
       scheme-specific fact but no scheme named → ask which scheme
  └─ 3. Retrieve: TF-IDF over 41 hand-verified chunks + scheme/topic boosts
       each chunk = ≤3 sentences tied to ONE source URL → citation is correct by construction
  └─ 4. Answer
       extractive (default): keep only the sentences carrying the asked fact
       LLM (optional, Groq or Gemini): rephrase from the single top chunk; output rejected and
       replaced by the extractive answer if it has >3 sentences, advice words, links,
       or ANY number not present in the chunk
  └─ 5. Append one source link + "Last updated from sources: <date>"
```

Why a curated chunk store instead of crawling full PDFs: the brief rewards accurate citations over coverage. A 66-page SID chunked blindly produces "relevant" passages that cite the wrong page or a superseded figure. Each chunk here was read off the live official page and paraphrased, so the source link always points at the page that states the fact.

## Setup

```bash
git clone <your-repo-url> && cd mf-faq-assistant
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Works with no API key (extractive mode). To turn on LLM phrasing, set **one** key:

```bash
export GROQ_API_KEY=...        # default model llama-3.3-70b-versatile
# or
export GEMINI_API_KEY=...      # default model gemini-2.0-flash
export LLM_MODEL=...           # optional override if the default model is retired
```

On Streamlit Community Cloud: push the repo to GitHub → *New app* → pick `app.py` → add the key under *Settings → Secrets* as `GROQ_API_KEY = "..."`.

**CLI and tests**

```bash
python -m scripts.ask "Exit load of Parag Parikh Liquid Fund?"
python -m pytest -q                 # 24 tests: answers, refusals, PII, 1 link + ≤3 sentences on every reply
python -m scripts.make_docs         # regenerates SAMPLE_QA.md and SOURCES.md from the live assistant
```

## Repo map

```
app.py                 Streamlit UI: ChatGPT-style violet chat (hero + 4 suggestion cards, then conversation; disclaimer under the input)
rag/guardrails.py      PII / advice / performance / scope rules
rag/retriever.py       scheme + topic routing, TF-IDF ranking
rag/assistant.py       pipeline, refusals, citation + date footer
rag/llm.py             optional Groq/Gemini rewrite with output validation
data/corpus.json       41 verified fact chunks (each → one source id, as_of date)
data/sources.csv       21 source URLs
tests/                 pytest suite
```

## Known limits

- **Static snapshot.** Expense ratios and riskometers change monthly; the corpus reflects the September 2026 factsheet. Refresh `data/corpus.json` each month (the TER page and factsheet archive are in the sources).
- **Base expense ratio, not total TER.** The factsheet publishes base TER; the full TER (incl. GST/additional expenses) is linked, not quoted.
- **Four schemes only.** Conservative Hybrid, Arbitrage and Dynamic Asset Allocation are out of scope; other AMCs are refused.
- **One citation per answer.** If two schemes are named, it answers the first one. Comparisons should be asked separately.
- **Rule-based intent.** Advice and PII detection are regex rules — transparent and testable, but an unusual phrasing can slip through or be over-refused (e.g. "hold" in a factual question).
- **No NAV or holdings data.** NAV, returns, holdings and fund-manager questions are routed to the official factsheet rather than answered.
- **Statements guide is generic.** Capital-gains steps come from AMFI's guide (CAMS / KFintech / AMC login); the assistant can't fetch anyone's statement and never asks for PAN or email.
- **Not affiliated** with Groww, PPFAS, AMFI or SEBI.
