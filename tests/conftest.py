import pytest


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    """Tests run the deterministic extractive path, never a live LLM."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
