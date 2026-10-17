import json
from pathlib import Path
import pytest
from youtube_rag.transcript import TranscriptValidationError, clean_text, validate_and_clean, process_transcript

def test_cleaning_drops_marker_only_and_keeps_mixed_text():
    segments, diagnostics = validate_and_clean([
        {"text": "[music]", "start": 0, "duration": 1},
        {"text": "  hello   [music] world ", "start": 1, "duration": 2},
    ])
    assert clean_text("  hello   [music] world ") == "hello world"
    assert [s.text for s in segments] == ["hello world"]
    assert segments[0].segment_index == 1
    assert diagnostics.dropped_marker_only_count == 1

def test_invalid_records_have_actionable_errors():
    with pytest.raises(TranscriptValidationError, match="duration.*positive"):
        validate_and_clean([{"text": "x", "start": 0, "duration": 0}])

def test_processing_is_deterministic_and_writes_outputs(tmp_path: Path):
    source = tmp_path / "transcript.json"
    source.write_text(json.dumps([{ "text": "hello", "start": 0.5, "duration": 1.0 }]), encoding="utf-8")
    a = process_transcript(source, tmp_path / "raw.json", tmp_path / "segments.jsonl", tmp_path / "diag.json")
    first = (tmp_path / "segments.jsonl").read_bytes()
    b = process_transcript(source, tmp_path / "raw.json", tmp_path / "segments.jsonl", tmp_path / "diag.json")
    assert a == b
    assert first == (tmp_path / "segments.jsonl").read_bytes()
    assert (tmp_path / "raw.json").read_bytes() == source.read_bytes()
