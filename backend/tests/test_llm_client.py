from app.services.llm_client import OfflineLLMClient, get_llm_client
from app.services.rag import retrieve_relevant_chunks


def test_get_llm_client_defaults_to_offline_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from app.config import get_settings

    get_settings.cache_clear()
    client = get_llm_client()
    assert client.source == "offline"
    get_settings.cache_clear()


def test_offline_summary_is_deterministic_and_flags_offline_mode():
    client = OfflineLLMClient()
    summary = client.generate_summary("Overall ESG score: 60/100")
    assert "Offline mode" in summary
    assert "ANTHROPIC_API_KEY" in summary


def test_offline_chat_echoes_context():
    client = OfflineLLMClient()
    reply = client.chat("The company disclosed Scope 1 emissions of 12500 tCO2e.", [], "What are the emissions?")
    assert "12500" in reply
    assert "Offline mode" in reply


def test_rag_retrieves_most_relevant_chunk():
    chunks = [
        "The company's total Scope 1 emissions were 12500 tonnes CO2e this year.",
        "Employee wellbeing coverage reached 92 percent across the workforce.",
        "CSR spend during the year was INR 18 crore across 14 projects.",
    ]
    results = retrieve_relevant_chunks(chunks, "What were the company's carbon emissions?", top_k=2)
    assert results, "expected at least one retrieved chunk"
    best_idx, best_text, best_score = results[0]
    assert best_idx == 0
    assert "emissions" in best_text.lower()


def test_rag_handles_empty_chunks():
    assert retrieve_relevant_chunks([], "any question") == []
