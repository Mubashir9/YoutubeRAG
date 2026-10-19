"""Isolated deterministic helpers for the notebook retrieval baseline."""
from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


STOPWORDS = {"a", "an", "and", "are", "do", "does", "for", "his", "how", "in", "is", "of", "s", "the", "to", "was", "what", "who"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def terms(text: str) -> list[str]:
    return [term for term in re.findall(r"[a-z0-9]+", text.lower()) if term not in STOPWORDS]


def lexical_scores(question: str, documents: dict[str, str]) -> dict[str, float]:
    """Repository BM25-style lexical score, implemented locally for experiments."""
    query_terms = set(terms(question))
    if not query_terms or not documents:
        return {}
    tokenized = {key: Counter(terms(doc)) for key, doc in documents.items()}
    lengths = {key: sum(counts.values()) for key, counts in tokenized.items()}
    average_length = sum(lengths.values()) / len(lengths)
    df = {term: sum(term in row for row in tokenized.values()) for term in query_terms}
    scores: dict[str, float] = {}
    for key, counts in tokenized.items():
        score = 0.0
        for term in query_terms:
            frequency = counts[term]
            if frequency:
                idf = math.log(1 + (len(documents) - df[term] + 0.5) / (df[term] + 0.5))
                score += idf * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * lengths[key] / average_length))
        if score:
            scores[key] = score
    return scores


@dataclass
class RunConfig:
    video_id: str = "DPqiIzK97K0"
    target_words: int = 200
    overlap_words: int = 35
    max_words: int = 300
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    k: int = 5
    dense_candidate_depth: int = 20
    rrf_constant: int = 60
    dense_rrf_weight: float = 1.0
    lexical_rrf_weight: float = 2.0
    strategy: str = "hybrid_dense_lexical_rrf"


class HybridIndex:
    """Persistent, video/config-specific Chroma index and hybrid retriever."""

    def __init__(self, directory: Path, model: SentenceTransformer, config: RunConfig):
        self.directory = directory
        self.model = model
        self.config = config
        directory.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(directory))
        self.collection_name = "baseline_chunks"
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.client.create_collection(self.collection_name, metadata={"hnsw:space": "cosine"})

    def build(self, chunks: list[dict[str, Any]]) -> float:
        texts = [chunk["text"] for chunk in chunks]
        started = time.perf_counter()
        vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=True).tolist()
        batch_size = 256
        for offset in range(0, len(chunks), batch_size):
            batch = chunks[offset:offset + batch_size]
            self.collection.add(
                ids=[row["chunk_id"] for row in batch],
                embeddings=vectors[offset:offset + batch_size],
                documents=[row["text"] for row in batch],
                metadatas=[{"video_id": row["video_id"], "start_sec": row["start_sec"], "end_sec": row["end_sec"], "source_segment_ids": json.dumps(row["source_segment_ids"])} for row in batch],
            )
        return time.perf_counter() - started

    def retrieve(self, question: str) -> tuple[list[dict[str, Any]], float]:
        count = self.collection.count()
        depth = min(max(self.config.dense_candidate_depth, self.config.k), count)
        started = time.perf_counter()
        query_embedding = self.model.encode([question], normalize_embeddings=True).tolist()[0]
        dense = self.collection.query(query_embeddings=[query_embedding], n_results=depth, include=["distances"])
        rows = self.collection.get(include=["documents", "metadatas"])
        docs = {key: doc for key, doc in zip(rows["ids"], rows["documents"])}
        metadata = {key: meta for key, meta in zip(rows["ids"], rows["metadatas"])}
        lexical = lexical_scores(question, docs)
        dense_ids = dense["ids"][0]
        lexical_ids = sorted(lexical, key=lambda key: (-lexical[key], key))
        fused: dict[str, float] = {}
        for rank, key in enumerate(dense_ids, 1):
            fused[key] = fused.get(key, 0.0) + self.config.dense_rrf_weight / (self.config.rrf_constant + rank)
        for rank, key in enumerate(lexical_ids, 1):
            fused[key] = fused.get(key, 0.0) + self.config.lexical_rrf_weight / (self.config.rrf_constant + rank)
        dense_distance = dict(zip(dense_ids, dense["distances"][0]))
        ranked = sorted(fused, key=lambda key: (-fused[key], key))[:self.config.k]
        results = [{
            "chunk_id": key,
            "score": float(fused[key]),
            "cosine_distance": float(dense_distance.get(key, 1.0)),
            "start_sec": float(metadata[key]["start_sec"]),
            "end_sec": float(metadata[key]["end_sec"]),
            "source_segment_ids": json.loads(metadata[key]["source_segment_ids"]),
            "excerpt": docs[key],
        } for key in ranked]
        return results, time.perf_counter() - started


def relevant_chunk_spans(chunks: list[dict[str, Any]], question: dict[str, Any]) -> dict[int, list[str]]:
    """Map stable source evidence spans to relevant chunk indices for this chunker."""
    result: dict[int, list[str]] = {}
    for span_index, span in enumerate(question["evidence_spans"]):
        evidence_ids = set(span["source_segment_ids"])
        for chunk_index, chunk in enumerate(chunks):
            source_match = bool(evidence_ids.intersection(chunk["source_segment_ids"]))
            time_match = chunk["start_sec"] <= span["end_sec"] and chunk["end_sec"] >= span["start_sec"]
            if source_match and time_match:
                result.setdefault(chunk_index, []).append(f"span_{span_index + 1}")
    return result


def score_question(question: dict[str, Any], rankings: list[dict[str, Any]], chunks: list[dict[str, Any]], k: int) -> dict[str, Any]:
    relevant = relevant_chunk_spans(chunks, question)
    rank_by_chunk = {row["chunk_id"]: rank for rank, row in enumerate(rankings, 1)}
    relevant_ranks = sorted(rank_by_chunk[chunk_id] for chunk_id in (chunks[i]["chunk_id"] for i in relevant) if chunk_id in rank_by_chunk)
    answerable = question["answerability"] == "answerable"
    found_spans = {span for row in rankings[:k] for i, spans in relevant.items() if chunks[i]["chunk_id"] == row["chunk_id"] for span in spans}
    expected_spans = {f"span_{i + 1}" for i in range(len(question["evidence_spans"]))}
    return {
        "question_id": question["id"],
        "question": question["question"],
        "answerability": question["answerability"],
        "scored": answerable,
        "hit_at_k": bool(relevant_ranks and relevant_ranks[0] <= k) if answerable else None,
        "reciprocal_rank": 1.0 / relevant_ranks[0] if relevant_ranks and answerable else (0.0 if answerable else None),
        "relevant_evidence_units": len(expected_spans),
        "evidence_units_found_at_k": len(found_spans),
        "recall_at_k": len(found_spans) / len(expected_spans) if expected_spans and answerable else None,
        "timestamp_overlap_at_k": bool(found_spans) if answerable else None,
        "rankings": rankings[:k],
        "relevant_chunk_ids": [chunks[i]["chunk_id"] for i in relevant],
    }


def aggregate_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [row for row in rows if row["scored"]]
    def mean(values: list[float]) -> float | None:
        return sum(values) / len(values) if values else None
    return {
        "answerable_question_count": len(scored),
        "hit_at_k": mean([float(row["hit_at_k"]) for row in scored]),
        "recall_at_k": mean([row["recall_at_k"] for row in scored if row["recall_at_k"] is not None]),
        "mrr": mean([row["reciprocal_rank"] for row in scored]),
        "timestamp_overlap_rate_at_k": mean([float(row["timestamp_overlap_at_k"]) for row in scored]),
        "ambiguous_excluded": sum(row["answerability"] == "ambiguous" for row in rows),
        "unanswerable_reported_separately": sum(row["answerability"] == "unanswerable" for row in rows),
    }
