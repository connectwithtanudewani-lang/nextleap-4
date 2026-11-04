# MF Facts — a facts-only FAQ assistant for PPFAS schemes

**Product track:** Groww · **AMC:** PPFAS Mutual Fund (Parag Parikh) · **Milestone 1:** Mutual Fund FAQs (facts-only Q&A)

A small RAG assistant that answers factual questions — expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, statements — from **21 official AMC / AMFI / SEBI pages**. Every answer is ≤3 sentences, cites exactly one source link, and ends with *Last updated from sources: <date>*. It refuses advice, never quotes returns, and never accepts PII.

**Live prototype:** https://nextleap-4-nvuvylhlyne8bhaj8gmqme.streamlit.app/

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

## Source list

21 official public pages — PPFAS AMC, AMFI and SEBI only. No third-party blogs. Machine-readable copy: `data/sources.csv`.

| # | Publisher | Page | Type | Scheme |
|---|---|---|---|---|
| S01 | PPFAS AMC | [Parag Parikh Flexi Cap Fund – scheme page (facts + exit load)](https://amc.ppfas.com/schemes/parag-parikh-flexi-cap-fund/) | Scheme page | Flexi Cap |
| S02 | PPFAS AMC | [Parag Parikh ELSS Tax Saver Fund – Scheme Facts](https://amc.ppfas.com/schemes/parag-parikh-elss-tax-saver-fund/scheme-facts/) | Scheme page | ELSS |
| S03 | PPFAS AMC | [Parag Parikh ELSS Tax Saver Fund – Entry and Exit Loads](https://amc.ppfas.com/schemes/parag-parikh-elss-tax-saver-fund/entry-exit-load/) | Fees/charges | ELSS |
| S04 | PPFAS AMC | [Parag Parikh ELSS Tax Saver Fund – FAQs](https://amc.ppfas.com/schemes/parag-parikh-elss-tax-saver-fund/faqs/) | Scheme FAQ | ELSS |
| S05 | PPFAS AMC | [Parag Parikh Large Cap Fund – Scheme Facts](https://amc.ppfas.com/schemes/parag-parikh-large-cap-fund/scheme-facts/) | Scheme page | Large Cap |
| S06 | PPFAS AMC | [Parag Parikh Liquid Fund – Scheme Features (incl. exit load)](https://amc.ppfas.com/schemes/parag-parikh-liquid-fund/) | Scheme page | Liquid |
| S07 | PPFAS AMC | [Digital Factsheet – September 2026](https://amc.ppfas.com/downloads/digital-factsheet/2026/september-2026/) | Factsheet | All |
| S08 | PPFAS AMC | [Factsheet PDF – September 2026](https://amc.ppfas.com/downloads/factsheet/2026/ppfas-mf-factsheet-for-September-2026.pdf) | Factsheet | All |
| S09 | PPFAS AMC | [Monthly Factsheets (archive)](https://amc.ppfas.com/downloads/factsheet/) | Factsheet | All |
| S10 | PPFAS AMC | [Total Expense Ratio (TER) of Schemes](https://amc.ppfas.com/statutory-disclosures/total-expense-ratio-TER/) | Fees/charges | All |
| S11 | PPFAS AMC | [KIM, SID and SAI downloads](https://amc.ppfas.com/downloads/kim-sid-and-sai/) | Offer documents | All |
| S12 | PPFAS AMC | [KIM – Parag Parikh Flexi Cap Fund](https://amc.ppfas.com/downloads/parag-parikh-flexi-cap-fund/KIM_PPFCF.pdf) | KIM | Flexi Cap |
| S13 | PPFAS AMC | [SID – Parag Parikh ELSS Tax Saver Fund](https://amc.ppfas.com/downloads/parag-parikh-tax-saver-fund/sid-parag-parikh-tax-saver-fund.pdf) | SID | ELSS |
| S14 | PPFAS AMC | [SID – Parag Parikh Large Cap Fund](https://amc.ppfas.com/downloads/parag-parikh-large-cap-fund/sid-parag-parikh-large-cap-fund.pdf) | SID | Large Cap |
| S15 | PPFAS AMC | [KIM – Parag Parikh Liquid Fund](https://amc.ppfas.com/downloads/parag-parikh-liquid-fund/kim-parag-parikh-liquid-fund.pdf) | KIM | Liquid |
| S16 | PPFAS AMC | [Account Statement via 'Missed Call'](https://amc.ppfas.com/investor-desk/statement-via-missed-call/) | Statement guide | All |
| S17 | AMFI (Mutual Funds Sahi Hai) | [How to Get Capital Gain Statement for Mutual Funds](https://www.mutualfundssahihai.com/en/how-get-capital-gain-statement-mutual-funds) | Statement/tax guide | All |
| S18 | AMFI (Mutual Funds Sahi Hai) | [ELSS Fund – Tax Saving Mutual Fund](https://www.mutualfundssahihai.com/en/elss-fund-tax-saving-mutual-fund) | Investor education | ELSS |
| S19 | AMFI (Mutual Funds Sahi Hai) | [What is a Mutual Fund?](https://www.mutualfundssahihai.com/en/what-is-a-mutual-fund) | Investor education | All |
| S20 | SEBI | [Circular: Product Labeling in Mutual Fund schemes – Risk-o-meter (Oct 5 2020)](https://www.sebi.gov.in/legal/circulars/oct-2020/circular-on-product-labeling-in-mutual-fund-schemes-risk-o-meter_47796.html) | Riskometer note | All |
| S21 | SEBI (hosted by AMFI) | [Circular: Categorization and Rationalization of MF Schemes (Oct 6 2017)](https://www.amfiindia.com/Themes/Theme1/downloads/1507291273374.pdf) | Category/benchmark note | All |

## Sample Q&A

Generated by `python -m scripts.make_docs` — these are the assistant's real outputs (extractive mode, no LLM key). Includes 7 factual answers and 3 guardrail cases.

#### 1. What is the expense ratio of Parag Parikh Flexi Cap Fund?
*Type: answer*

As per the September 2026 factsheet, the base expense ratio of Parag Parikh Flexi Cap Fund is 1.05% for the Regular Plan and 0.53% for the Direct Plan (as on the last business day of the month). The full Total Expense Ratio disclosure is on the AMC's TER page.

**Source:** [Digital Factsheet – September 2026](https://amc.ppfas.com/downloads/digital-factsheet/2026/september-2026/)  
*Last updated from sources: 30 Sep 2026*

---

#### 2. What is the exit load of Parag Parikh Flexi Cap Fund?
*Type: answer*

For each purchase or switch-in, 10% of units can be redeemed without exit load; units above that limit attract 2% if redeemed within 365 days of allotment and 1% if redeemed after 365 but within 730 days. There is no exit load after 730 days, and none on switches between the Regular and Direct plans.

**Source:** [Parag Parikh Flexi Cap Fund – scheme page (facts + exit load)](https://amc.ppfas.com/schemes/parag-parikh-flexi-cap-fund/)  
*Last updated from sources: 3 Nov 2026*

---

#### 3. ELSS lock-in?
*Type: answer*

Parag Parikh ELSS Tax Saver Fund has a lock-in of 3 years from the date of investment, applied to each instalment separately.

**Source:** [Parag Parikh ELSS Tax Saver Fund – Scheme Facts](https://amc.ppfas.com/schemes/parag-parikh-elss-tax-saver-fund/scheme-facts/)  
*Last updated from sources: 3 Nov 2026*

---

#### 4. What is the minimum SIP for Parag Parikh ELSS Tax Saver Fund?
*Type: answer*

The minimum monthly SIP is ₹1,000 (multiples of ₹500, at least 6 instalments) and the minimum quarterly SIP is ₹3,000 (multiples of ₹500, at least 4 instalments).

**Source:** [Parag Parikh ELSS Tax Saver Fund – Scheme Facts](https://amc.ppfas.com/schemes/parag-parikh-elss-tax-saver-fund/scheme-facts/)  
*Last updated from sources: 3 Nov 2026*

---

#### 5. What is the riskometer and benchmark of Parag Parikh Large Cap Fund?
*Type: answer*

The riskometer of Parag Parikh Large Cap Fund is 'Very High' as of 30 September 2026, and its benchmark (NIFTY 100 TRI) is also rated 'Very High'.

**Source:** [Digital Factsheet – September 2026](https://amc.ppfas.com/downloads/digital-factsheet/2026/september-2026/)  
*Last updated from sources: 30 Sep 2026*

---

#### 6. What is the exit load of Parag Parikh Liquid Fund?
*Type: answer*

Parag Parikh Liquid Fund charges a graded exit load only if you exit within 7 days: 0.0070% on day 1, falling by 0.0005% a day to 0.0045% on day 6. From day 7 onwards the exit load is nil.

**Source:** [Parag Parikh Liquid Fund – Scheme Features (incl. exit load)](https://amc.ppfas.com/schemes/parag-parikh-liquid-fund/)  
*Last updated from sources: 3 Nov 2026*

---

#### 7. How do I download my capital-gains statement?
*Type: answer*

To get a capital-gains statement, log in on the fund house's website and download the capital gains report, or use the registrar portals. On CAMS (camsonline.com) go to Statements → Capital Gain/Loss Statement, enter PAN and registered email, pick up to three financial years, and an encrypted PDF is emailed to you. On KFintech (mfs.kfintech.com) go to Investor Statement and Report → Capital Gains Statement → Consolidated Capital Gains Statement.

**Source:** [How to Get Capital Gain Statement for Mutual Funds](https://www.mutualfundssahihai.com/en/how-get-capital-gain-statement-mutual-funds)  
*Last updated from sources: 3 Nov 2026*

---

#### 8. Should I buy Parag Parikh Flexi Cap Fund now?
*Type: refusal_advice*

I can only share facts from official documents, so I can't say whether to buy, sell, hold or pick a scheme. AMFI's investor-education guide explains how to think about scheme types and risk, and a SEBI-registered adviser can help with a personal decision.

**Source:** [What is a Mutual Fund?](https://www.mutualfundssahihai.com/en/what-is-a-mutual-fund)  
*Last updated from sources: 3 Nov 2026*

---

#### 9. What were the 5-year returns of the ELSS fund?
*Type: performance*

I don't quote, calculate or compare returns or NAVs. The official monthly factsheet shows each scheme's performance against its benchmark, and the latest NAV is published on the AMC and AMFI websites.

**Source:** [Monthly Factsheets (archive)](https://amc.ppfas.com/downloads/factsheet/)  
*Last updated from sources: 3 Nov 2026*

---

#### 10. My PAN is ABCDE1234F, can you check my folio?
*Type: refusal_pii*

Please don't share personal details like PAN, Aadhaar, account or folio numbers, OTPs, phone numbers or emails here — I haven't stored your message. I can only answer general facts about the schemes; for your own holdings, use the AMC's statement services.

**Source:** [Account Statement via 'Missed Call'](https://amc.ppfas.com/investor-desk/statement-via-missed-call/)  
*Last updated from sources: 3 Nov 2026*

---

## Disclaimer used in the UI

**Badge (shown under the heading):**

> Facts-only. No investment advice.

**Scope line (shown under the badge):**

> Covers PPFAS Mutual Fund: Parag Parikh Flexi Cap, ELSS Tax Saver, Large Cap and Liquid Fund. Sources: PPFAS AMC, AMFI and SEBI pages only. Please don't enter PAN, Aadhaar, account numbers, OTPs, emails or phone numbers.

**Refusal text for opinion/portfolio questions:**

> I can only share facts from official documents, so I can't say whether to buy, sell, hold or pick a scheme. AMFI's investor-education guide explains how to think about scheme types and risk, and a SEBI-registered adviser can help with a personal decision.

This assistant is an independent study prototype built for the Groww track of the milestone. It is not affiliated with or endorsed by Groww, PPFAS Mutual Fund, AMFI or SEBI. Mutual fund investments are subject to market risks; read all scheme-related documents carefully.
