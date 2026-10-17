from youtube_rag.answering import DraftAnswer, answer_question
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


def test_weak_evidence_abstains_without_calling_provider():
    result = answer_question("Unknown", [evidence(0.9)], Provider(DraftAnswer("claim", ("chunk-1",))))
    assert result.insufficient_evidence is True
    assert not result.citations


def test_no_provider_is_honest_retrieval_only_mode():
    result = answer_question("What changed?", [evidence()])
    assert result.insufficient_evidence is True
    assert result.citations[0].chunk_id == "chunk-1"
