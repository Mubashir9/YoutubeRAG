import pytest

from youtube_rag.answering import DraftAnswer, GroqProvider, answer_question
from youtube_rag.retrieval import RetrievalResult


def evidence(score=0.2):
    return RetrievalResult("chunk-1", score, "books changed my thinking", "abc123", 12.4, 20)


class Provider:
    def __init__(self, draft): self.draft = draft
    def generate(self, question, evidence): return self.draft


def test_answer_validates_ids_and_constructs_trusted_citation():
    result = answer_question("What changed?", [evidence()], Provider(DraftAnswer("Reading changed it.", ("invented", "chunk-1"))))
    assert result.insufficient_evidence is False
    assert result.citations[0].url == "https://www.youtube.com/watch?v=abc123&t=12"


def test_invented_only_citations_abstain():
    result = answer_question("What changed?", [evidence()], Provider(DraftAnswer("A claim", ("invented",))))
    assert result.insufficient_evidence is True
    assert result.text == "Not found in indexed videos."


def test_distance_alone_does_not_discard_provider_supported_evidence():
    result = answer_question("What changed?", [evidence(0.9)], Provider(DraftAnswer("Reading changed it.", ("chunk-1",))))
    assert result.insufficient_evidence is False
    assert result.citations[0].chunk_id == "chunk-1"


def test_insufficient_answer_preserves_explanation_and_citation():
    result = answer_question("Who?", [evidence()], Provider(DraftAnswer("The transcript does not name her.", ("chunk-1",), True)))
    assert result.insufficient_evidence is True
    assert result.text == "The transcript does not name her."
    assert result.citations[0].chunk_id == "chunk-1"


def test_no_provider_is_honest_retrieval_only_mode():
    result = answer_question("What changed?", [evidence()])
    assert result.insufficient_evidence is True
    assert result.citations[0].chunk_id == "chunk-1"

def test_groq_provider_uses_compatible_endpoint_and_forwards_bounded_evidence(monkeypatch):
    calls = {}
    class Completions:
        def create(self, **kwargs):
            calls.update(kwargs)
            return type("Response", (), {"choices": [type("Choice", (), {"message": type("Message", (), {"content": '{"text":"Reading changed it.","citation_ids":["chunk-1"]}'})()})()]})()
    class Client:
        chat = type("Chat", (), {"completions": Completions()})()
    def fake_client(api_key, model, base_url=None):
        calls["api_key"], calls["model"], calls["base_url"] = api_key, model, base_url
        return Client()
    monkeypatch.setattr("youtube_rag.answering._client", fake_client)
    result = GroqProvider("secret", "openai/gpt-oss-20b").generate("What changed?", [evidence()])
    assert result.citation_ids == ("chunk-1",)
    assert calls["base_url"] == "https://api.groq.com/openai/v1"
    assert calls["model"] == "openai/gpt-oss-20b"
    assert "books changed my thinking" in calls["messages"][1]["content"]

def test_provider_api_errors_are_actionable(monkeypatch):
    def fail(*args, **kwargs): raise RuntimeError("rate limit")
    monkeypatch.setattr("youtube_rag.answering._client", fail)
    with pytest.raises(RuntimeError, match="rate limit"):
        GroqProvider("secret").generate("Question", [evidence()])
