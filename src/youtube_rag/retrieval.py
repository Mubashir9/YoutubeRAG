"""Persistent Chroma indexing and evidence retrieval."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol, Sequence
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

    @property
    def timestamp_url(self) -> str:
        return "https://www.youtube.com/watch?" + urlencode({"v": self.video_id, "t": max(0, int(self.start_sec))})


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
        result = self.collection.query(query_embeddings=self.embedder.embed([text]), n_results=top_k)
        ids, distances = result["ids"][0], result["distances"][0]
        docs, metas = result["documents"][0], result["metadatas"][0]
        return [RetrievalResult(i, float(d), doc, str(meta["video_id"]), float(meta["start_sec"]), float(meta["end_sec"]))
                for i, d, doc, meta in zip(ids, distances, docs, metas)]

    def save_stats(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.stats(), indent=2) + "\n", encoding="utf-8")
