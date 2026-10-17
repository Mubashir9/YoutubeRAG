from youtube_rag.retrieval import RetrievalResult


def test_retrieval_result_builds_safe_timestamp_url():
    result = RetrievalResult("v:0001", 0.2, "reading books", "abc", 91.8, 120.0)
    assert result.timestamp_url == "https://www.youtube.com/watch?v=abc&t=91"


def test_retrieval_result_preserves_contract_fields():
    result = RetrievalResult("v:0001", 0.2, "reading books", "abc", 91.8, 120.0)
    assert result.strategy == "dense"
