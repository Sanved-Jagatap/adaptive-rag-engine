"""
app/ingestion/embedder.py

Embedding generation for chunks/queries. Defined as a Protocol so
retrieval/ingestion code depends on "something that embeds text," not
specifically on sentence-transformers — that's what makes the vector
pipeline testable without downloading model weights (see
tests/test_vector_retrieval.py, which injects a deterministic stub).

SentenceTransformerEmbedder is the real implementation used in
production/Docker, where network access to Hugging Face is available.
"""

from __future__ import annotations

from typing import Protocol

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_DIM = 384  # matches all-MiniLM-L6-v2's output size


class Embedder(Protocol):
    """Anything that turns text into fixed-size vectors."""

    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    """Real embedder, backed by sentence-transformers. Downloads model
    weights from Hugging Face on first use — requires network access and a
    writable cache dir, which Docker/production environments have but this
    dev sandbox does not. Lazily loaded so importing this module doesn't
    itself require network access; only calling .embed() does."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name
        self.dimension = DEFAULT_EMBEDDING_DIM
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self.dimension = self._model.get_sentence_embedding_dimension()
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return vectors.tolist()
