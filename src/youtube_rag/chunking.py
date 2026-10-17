"""Deterministic timestamp-aware chunking for cleaned transcript segments."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Protocol

from .transcript import _atomic_write


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    video_id: str
    video_title: str | None
    video_url: str
    published_at: str | None
    start_sec: float
    end_sec: float
    text: str
    source_segment_ids: list[int]


@dataclass(frozen=True)
class ChunkStats:
    video_id: str
    input_segments: int
    chunk_count: int
    word_count: int
    average_words: float
    maximum_words: int
    overlap_words: int


class Chunker(Protocol):
    def chunk(self, segments: Iterable[dict], video_id: str) -> tuple[list[Chunk], ChunkStats]: ...


class SequentialWordChunker:
    """Group adjacent segments into bounded word windows with deterministic overlap."""

    def __init__(self, target_words: int = 200, overlap_words: int = 35, max_words: int = 300) -> None:
        if not 1 <= overlap_words < target_words <= max_words:
            raise ValueError("Require 1 <= overlap_words < target_words <= max_words.")
        self.target_words = target_words
        self.overlap_words = overlap_words
        self.max_words = max_words

    def chunk(self, segments: Iterable[dict], video_id: str) -> tuple[list[Chunk], ChunkStats]:
        items = list(segments)
        if not items:
            return [], ChunkStats(video_id, 0, 0, 0, 0.0, 0, self.overlap_words)
        chunks: list[Chunk] = []
        start = 0
        while start < len(items):
            end = start
            words = 0
            while end < len(items) and (words < self.target_words or end == start):
                next_words = len(str(items[end]["text"]).split())
                if end > start and words + next_words > self.max_words:
                    break
                words += next_words
                end += 1
            # If the target falls mid-topic, include short trailing segments up to max_words.
            while end < len(items) and words < self.target_words:
                next_words = len(str(items[end]["text"]).split())
                if words + next_words > self.max_words:
                    break
                words += next_words
                end += 1
            selected = items[start:end]
            ids = [int(s["segment_index"]) for s in selected]
            chunk_number = len(chunks)
            chunks.append(Chunk(
                chunk_id=f"{video_id}:{chunk_number:04d}", video_id=video_id,
                video_title=None, video_url=f"https://www.youtube.com/watch?v={video_id}",
                published_at=None, start_sec=float(selected[0]["start"]),
                end_sec=max(float(s["start"]) + float(s["duration"]) for s in selected),
                text=" ".join(str(s["text"]).strip() for s in selected),
                source_segment_ids=ids,
            ))
            if end >= len(items):
                break
            # Carry whole segments backwards until the requested word overlap is met.
            overlap = 0
            next_start = end
            while next_start > start and overlap < self.overlap_words:
                next_start -= 1
                overlap += len(str(items[next_start]["text"]).split())
            start = next_start if next_start > start else end
        word_counts = [len(c.text.split()) for c in chunks]
        stats = ChunkStats(video_id, len(items), len(chunks), sum(word_counts),
                           sum(word_counts) / len(word_counts) if word_counts else 0.0,
                           max(word_counts, default=0), self.overlap_words)
        return chunks, stats


def load_segments(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_chunks(path: Path, chunks: list[Chunk]) -> None:
    content = "".join(json.dumps(asdict(chunk), ensure_ascii=False, separators=(",", ":")) + "\n" for chunk in chunks)
    _atomic_write(path, content)
