import json
from pathlib import Path

from youtube_rag.chunking import SequentialWordChunker, load_segments, write_chunks


def segments(count=12):
    return [{"segment_index": i, "text": "word " * 20, "start": i * 2.0, "duration": 2.0} for i in range(count)]


def test_chunks_have_traceable_times_ids_and_overlap():
    chunker = SequentialWordChunker(target_words=50, overlap_words=20, max_words=70)
    chunks, stats = chunker.chunk(segments(), "video")
    assert len(chunks) > 1
    assert chunks[0].chunk_id == "video:0000"
    assert all(c.start_sec <= c.end_sec and c.text and c.source_segment_ids for c in chunks)
    assert set(chunks[0].source_segment_ids) & set(chunks[1].source_segment_ids)
    assert stats.maximum_words <= 70


def test_chunking_and_serialization_are_deterministic(tmp_path: Path):
    chunker = SequentialWordChunker()
    first, stats = chunker.chunk(segments(30), "video")
    second, _ = chunker.chunk(segments(30), "video")
    assert first == second
    path = tmp_path / "chunks.jsonl"
    write_chunks(path, first)
    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()][0]["chunk_id"] == "video:0000"


def test_load_segments_ignores_blank_lines(tmp_path: Path):
    path = tmp_path / "segments.jsonl"
    path.write_text(json.dumps(segments(1)[0]) + "\n\n", encoding="utf-8")
    assert len(load_segments(path)) == 1
