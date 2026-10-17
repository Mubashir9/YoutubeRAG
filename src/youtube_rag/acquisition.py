"""Obtain timestamped YouTube captions without downloading media."""
from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


class CaptionAcquisitionError(RuntimeError):
    """A YouTube ID could not be resolved or captions could not be fetched."""


@dataclass(frozen=True)
class AcquisitionResult:
    video_id: str
    source_url: str
    caption_count: int
    language: str | None
    caption_kind: str | None


def resolve_video_id(value: str) -> str:
    """Resolve a YouTube URL or bare 11-character video ID safely."""
    value = value.strip()
    if VIDEO_ID_RE.fullmatch(value):
        return value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}:
        raise CaptionAcquisitionError("Provide a YouTube URL or an 11-character video ID.")
    if parsed.netloc.lower() == "youtu.be":
        candidate = parsed.path.strip("/").split("/")[0]
    elif parsed.path == "/watch":
        candidate = parse_qs(parsed.query).get("v", [""])[0]
    else:
        candidate = parsed.path.strip("/").split("/")[-1]
    if not VIDEO_ID_RE.fullmatch(candidate):
        raise CaptionAcquisitionError("The YouTube URL does not contain a valid video ID.")
    return candidate


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def fetch_captions(source: str, output_dir: Path) -> AcquisitionResult:
    """Fetch available captions and save raw timestamped JSON plus provenance."""
    video_id = resolve_video_id(source)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)
        rows = transcript.to_raw_data() if hasattr(transcript, "to_raw_data") else list(transcript)
        language = getattr(transcript, "language_code", None)
        caption_kind = "generated" if getattr(transcript, "is_generated", False) else "uploaded"
    except ImportError as exc:
        raise CaptionAcquisitionError("Caption access is not installed; install project dependencies first.") from exc
    except Exception as exc:
        raise CaptionAcquisitionError(f"Captions unavailable or blocked for {video_id}: {exc}") from exc
    records = []
    for index, row in enumerate(rows):
        try:
            text, start, duration = row["text"], row["start"], row["duration"]
        except (KeyError, TypeError):
            raise CaptionAcquisitionError(f"Caption service returned an invalid record at index {index}.")
        records.append({"text": text, "start": start, "duration": duration})
    if not records:
        raise CaptionAcquisitionError(f"No captions were available for {video_id}.")
    result = AcquisitionResult(video_id, f"https://www.youtube.com/watch?v={video_id}", len(records), language, caption_kind)
    target = output_dir / f"{video_id}.json"
    _atomic_write(target, json.dumps(records, ensure_ascii=False, indent=2) + "\n")
    _atomic_write(output_dir / f"{video_id}.meta.json", json.dumps(asdict(result), indent=2) + "\n")
    return result
