"""Optional LLM rewrite step (Groq or Gemini, via plain HTTPS).

The LLM only sees ONE retrieved chunk and is asked to answer the exact fact.
Its output is accepted only if it passes checks (<=3 sentences, no new
numbers, no advice words); otherwise the caller falls back to the chunk text.
No key set -> extractive mode, which is fully functional.
"""
import os
import re

import requests

SYSTEM_PROMPT = """You are a facts-only FAQ assistant for mutual fund schemes of PPFAS Mutual Fund (Parag Parikh).
Rules:
- Answer ONLY from the CONTEXT. If the context does not contain the answer, reply exactly: NOT_IN_CONTEXT
- Answer the exact fact asked first, in plain words. Maximum 3 sentences. No bullet points.
- Copy every number, percentage, amount and date exactly as written in the context. Never compute, round or compare.
- No advice, opinions, recommendations or predictions. Never say a fund is good, bad, better or suitable.
- Do not mention returns or performance.
- Do not include any links, sources or "last updated" text; the app adds them."""

ADVICE_WORDS = re.compile(r"\b(recommend|should|suggest|better|best|ideal|good choice|suitable)\b", re.I)
NUM_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _norm_nums(text):
    return {n.replace(",", "") for n in NUM_RE.findall(text)}


def provider():
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("GEMINI_API_KEY"):
        return "gemini"
    return None


def _call_groq(question, context):
    model = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={
            "model": model,
            "temperature": 0,
            "max_tokens": 200,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"CONTEXT:\n{context}\n\nQUESTION: {question}"},
            ],
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _call_gemini(question, context):
    model = os.getenv("LLM_MODEL", "gemini-2.0-flash")
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": os.environ["GEMINI_API_KEY"]},
        json={
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": f"CONTEXT:\n{context}\n\nQUESTION: {question}"}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 200},
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def sentence_count(text):
    return len([s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s])


def validate(answer, context):
    """Return True if the LLM answer is safe to show."""
    if not answer or "NOT_IN_CONTEXT" in answer:
        return False
    if sentence_count(answer) > 3:
        return False
    if ADVICE_WORDS.search(answer):
        return False
    if "http" in answer.lower():
        return False
    # every number in the answer must exist in the context (no invented or computed figures)
    return _norm_nums(answer) <= _norm_nums(context)


def rewrite(question, context):
    """Return (answer, mode). Falls back to None if no provider / failure / failed checks."""
    p = provider()
    if not p:
        return None, "extractive"
    try:
        out = _call_groq(question, context) if p == "groq" else _call_gemini(question, context)
    except Exception:
        return None, "extractive (LLM unavailable)"
    if validate(out, context):
        return out, p
    return None, "extractive (LLM output rejected)"
