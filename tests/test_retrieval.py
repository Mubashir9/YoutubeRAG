import json

from youtube_rag.retrieval import RetrievalResult, _lexical_scores, _playback_time


def test_retrieval_result_builds_safe_timestamp_url():
    result = RetrievalResult("v:0001", 0.2, "reading books", "abc", 91.8, 120.0)
    assert result.timestamp_url == "https://www.youtube.com/watch?v=abc&t=91"


def test_retrieval_result_preserves_contract_fields():
    result = RetrievalResult("v:0001", 0.2, "reading books", "abc", 91.8, 120.0)
    assert result.strategy == "dense"


def test_identity_query_ranks_relationship_passage_above_subject_name():
    documents = {"name": "Anthony talked about books", "relationship": "My girlfriend went to the beach"}
    scores = _lexical_scores("Who is Anthony's girlfriend?", documents)
    assert scores["relationship"] > scores.get("name", 0)


def test_timestamp_targets_matching_transcript_segment(tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "video.chunks.jsonl").write_text(json.dumps({"chunk_id": "video:0001", "source_segment_ids": [1, 2]}) + "\n", encoding="utf-8")
    segments = [{"segment_index": 1, "start": 100.0, "text": "Anthony discusses books"},
                {"segment_index": 2, "start": 121.5, "text": "My girlfriend went to the beach"}]
    (processed / "video.segments.jsonl").write_text("\n".join(json.dumps(row) for row in segments), encoding="utf-8")
    assert _playback_time(processed, "video:0001", "Who is Anthony's girlfriend?", 100.0) == 121.5
