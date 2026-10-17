"""Persistent Chroma indexing and evidence retrieval."""
from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence
import re
from urllib.parse import urlencode

from .chunking import Chunk


class Embedder(Protocol):
    model_name: str
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    score: float
    excerpt: str
    video_id: str
    start_sec: float
    end_sec: float
    strategy: str = "dense"
    playback_sec: float | None = None

    @property
    def play_time(self) -> float:
        return self.start_sec if self.playback_sec is None else self.playback_sec

    @property
    def timestamp_url(self) -> str:
        return "https://www.youtube.com/watch?" + urlencode({"v": self.video_id, "t": max(0, int(self.play_time))})


class ChromaIndex:
    def __init__(self, directory: Path, embedder: Embedder, collection_name: str = "transcript_chunks") -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("Install the project dependencies to use the persistent index: pip install -e .") from exc
        self.directory, self.embedder = directory, embedder
        self.client = chromadb.PersistentClient(path=str(directory))
        self.collection = self.client.get_or_create_collection(
            collection_name, metadata={"embedding_model": embedder.model_name, "hnsw:space": "cosine"}
        )
        existing_model = (self.collection.metadata or {}).get("embedding_model")
        if existing_model and existing_model != embedder.model_name:
            raise ValueError(f"Index uses embedding model {existing_model!r}; rebuild it for {embedder.model_name!r}.")

    def upsert(self, chunks: Sequence[Chunk]) -> int:
        if not chunks:
            return 0
        self.collection.upsert(
            ids=[c.chunk_id for c in chunks], embeddings=self.embedder.embed([c.text for c in chunks]),
            documents=[c.text for c in chunks], metadatas=[{
                "video_id": c.video_id, "video_url": c.video_url, "start_sec": c.start_sec,
                "end_sec": c.end_sec, "video_title": c.video_title or "", "published_at": c.published_at or "",
            } for c in chunks],
        )
        return len(chunks)

    def stats(self) -> dict[str, object]:
        return {"count": self.collection.count(), "embedding_model": self.embedder.model_name, "directory": str(self.directory)}

    def query(self, text: str, top_k: int = 5) -> list[RetrievalResult]:
        count = self.collection.count()
        if count == 0:
            return []
        dense = self.collection.query(
            query_embeddings=self.embedder.embed([text]), n_results=min(max(top_k * 4, 20), count)
        )
        all_rows = self.collection.get(include=["documents", "metadatas"])
        rows = {chunk_id: (doc, meta) for chunk_id, doc, meta in zip(
            all_rows["ids"], all_rows["documents"], all_rows["metadatas"]
        )}
        lexical = _lexical_scores(text, {chunk_id: doc for chunk_id, (doc, _) in rows.items()})
        dense_ids = dense["ids"][0]
        dense_distances = dict(zip(dense_ids, dense["distances"][0]))
        lexical_ids = sorted(lexical, key=lambda chunk_id: lexical[chunk_id], reverse=True)
        # Reciprocal rank fusion lets exact terms be found even when the dense
        # candidate set misses them entirely. Distances stay as actual cosine
        # distances; fusion rank is never presented as a distance.
        fused = {}
        for rank, chunk_id in enumerate(dense_ids, 1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 1 / (60 + rank)
        for rank, chunk_id in enumerate(lexical_ids, 1):
            fused[chunk_id] = fused.get(chunk_id, 0.0) + 2 / (60 + rank)
        ranked_ids = sorted(fused, key=lambda chunk_id: fused[chunk_id], reverse=True)[:top_k]
        return [RetrievalResult(
            chunk_id, float(dense_distances.get(chunk_id, 1.0)), rows[chunk_id][0],
            str(rows[chunk_id][1]["video_id"]), float(rows[chunk_id][1]["start_sec"]),
            float(rows[chunk_id][1]["end_sec"]), "hybrid",
            _playback_time(self.directory.parent / "processed", chunk_id, text, float(rows[chunk_id][1]["start_sec"])),
        ) for chunk_id in ranked_ids]

    def save_stats(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.stats(), indent=2) + "\n", encoding="utf-8")


_STOPWORDS = {"a", "an", "and", "are", "do", "does", "for", "his", "how", "in", "is", "of", "s", "the", "to", "was", "what", "who"}


def _terms(text: str) -> list[str]:
    return [term for term in re.findall(r"[a-z0-9]+", text.lower()) if term not in _STOPWORDS]


def _lexical_scores(question: str, documents: dict[str, str]) -> dict[str, float]:
    terms = _query_terms(question)
    if not terms or not documents:
        return {}
    tokenized = {chunk_id: Counter(_terms(doc)) for chunk_id, doc in documents.items()}
    lengths = {chunk_id: sum(tokens.values()) for chunk_id, tokens in tokenized.items()}
    avg_length = sum(lengths.values()) / len(lengths)
    document_frequency = {term: sum(term in tokens for tokens in tokenized.values()) for term in terms}
    scores = {}
    for chunk_id, tokens in tokenized.items():
        score = 0.0
        for term in terms:
            frequency = tokens[term]
            if frequency:
                idf = math.log(1 + (len(documents) - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
                score += idf * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * lengths[chunk_id] / avg_length))
        if score:
            scores[chunk_id] = score
    return scores


def _playback_time(processed_dir: Path, chunk_id: str, question: str, default: float) -> float:
    video_id = chunk_id.split(":", 1)[0]
    chunk_path = processed_dir / f"{video_id}.chunks.jsonl"
    segments_path = processed_dir / f"{video_id}.segments.jsonl"
    if not chunk_path.is_file() or not segments_path.is_file():
        return default
    terms = _query_terms(question)
    if not terms:
        return default
    chunks = (json.loads(line) for line in chunk_path.read_text(encoding="utf-8").splitlines() if line.strip())
    source_ids = next((set(row["source_segment_ids"]) for row in chunks if row["chunk_id"] == chunk_id), set())
    if not source_ids:
        return default
    matches = []
    for line in segments_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        segment = json.loads(line)
        if segment["segment_index"] in source_ids:
            overlap = len(terms & set(_terms(segment["text"])))
            if overlap:
                matches.append((overlap, float(segment["start"])))
    return sorted(matches, key=lambda item: (-item[0], item[1]))[0][1] if matches else default


def _query_terms(question: str) -> set[str]:
    # In identity questions the possessive owner provides context; the role
    # after it is the useful exact-match term (e.g. "Anthony's girlfriend").
    if re.match(r"\s*who\s+is\b", question, re.IGNORECASE):
        question = re.sub(r"\b[a-z0-9]+['’]s\b", " ", question, flags=re.IGNORECASE)
    return set(_terms(question))
