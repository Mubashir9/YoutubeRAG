"""Local Sentence Transformers embedding adapter."""
from __future__ import annotations

from typing import Sequence


class LocalEmbedder:
    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("Install the project dependencies to use embeddings: pip install -e .") from exc
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return self._model.encode(list(texts), normalize_embeddings=True).tolist()
