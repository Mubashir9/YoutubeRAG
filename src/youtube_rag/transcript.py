"""Validation, conservative cleaning, and diagnostics for transcript captions."""
from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

VIDEO_ID = "n_jHmfOgpA0"
MARKER_RE = re.compile(r"\[(?:music|applause|laughter|inaudible)\]", re.IGNORECASE)


class TranscriptValidationError(ValueError):
    """Raised when a transcript cannot be safely ingested."""


@dataclass(frozen=True)
class CanonicalSegment:
    segment_index: int
    original_text: str
    text: str
    start: float
    duration: float


@dataclass(frozen=True)
class Diagnostics:
    video_id: str
    input_count: int
    kept_count: int
    dropped_count: int
    start_sec: float | None
    end_sec: float | None
    input_word_count: int
    kept_word_count: int
    dropped_marker_only_count: int
    warnings: list[str]


def clean_text(value: str) -> str:
    """Remove known caption markers and normalize whitespace only."""
    return " ".join(MARKER_RE.sub(" ", value).split())


def validate_and_clean(payload: Any, video_id: str = VIDEO_ID) -> tuple[list[CanonicalSegment], Diagnostics]:
    if not isinstance(payload, list):
        raise TranscriptValidationError("Transcript top level must be a JSON list of records.")
    segments: list[CanonicalSegment] = []
    warnings: list[str] = []
    previous_start = -1.0
    dropped = 0
    marker_only = 0
    input_words = 0
    for index, record in enumerate(payload):
        if not isinstance(record, dict):
            raise TranscriptValidationError(f"Record {index} must be an object.")
        missing = [field for field in ("text", "start", "duration") if field not in record]
        if missing:
            raise TranscriptValidationError(f"Record {index} is missing required field(s): {', '.join(missing)}.")
        text, start, duration = record["text"], record["start"], record["duration"]
        if not isinstance(text, str):
            raise TranscriptValidationError(f"Record {index} field 'text' must be a string.")
        if isinstance(start, bool) or not isinstance(start, (int, float)):
            raise TranscriptValidationError(f"Record {index} field 'start' must be numeric.")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
            raise TranscriptValidationError(f"Record {index} field 'duration' must be a positive number.")
        if start < 0:
            raise TranscriptValidationError(f"Record {index} field 'start' cannot be negative.")
        if start < previous_start:
            warnings.append(f"Record {index} start time is earlier than the preceding record.")
        previous_start = float(start)
        input_words += len(text.split())
        cleaned = clean_text(text)
        if not cleaned:
            dropped += 1
            if text.strip(): marker_only += 1
            continue
        segments.append(CanonicalSegment(index, text, cleaned, float(start), float(duration)))
    start_sec = segments[0].start if segments else None
    end_sec = max((s.start + s.duration for s in segments), default=None)
    diagnostics = Diagnostics(video_id, len(payload), len(segments), dropped, start_sec, end_sec,
                              input_words, sum(len(s.text.split()) for s in segments), marker_only, warnings)
    return segments, diagnostics


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def process_transcript(source: Path, raw_target: Path, segments_target: Path, diagnostics_target: Path,
                       video_id: str = VIDEO_ID) -> Diagnostics:
    payload = json.loads(source.read_text(encoding="utf-8"))
    segments, diagnostics = validate_and_clean(payload, video_id)
    _atomic_write(raw_target, source.read_text(encoding="utf-8"))
    segment_lines = "".join(json.dumps(asdict(segment), ensure_ascii=False, separators=(",", ":")) + "\n" for segment in segments)
    _atomic_write(segments_target, segment_lines)
    _atomic_write(diagnostics_target, json.dumps(asdict(diagnostics), indent=2, ensure_ascii=False) + "\n")
    return diagnostics
