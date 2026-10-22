"""
app/retrieval/reranker.py

Reranks retrieval candidates with a cross-encoder, which scores (query,
chunk) pairs jointly rather than via separate embeddings — more accurate
than the initial retrieval score, more expensive, which is why it only
runs on a small candidate set (typically 10-20) rather than the whole
corpus. Defined as a Protocol for the same reason as Embedder: testable
without downloading model weights.
"""

from __future__ import annotations

from typing import Protocol

from app.retrieval.types import RetrievedChunk

DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]: ...


class CrossEncoderReranker:
    """Real reranker, backed by sentence-transformers' CrossEncoder.
    Downloads model weights from Hugging Face on first use — see
    embedder.py's docstring for the same network-dependency note."""

    def __init__(self, model_name: str = DEFAULT_RERANKER_MODEL):
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not candidates:
            return []

        model = self._load()
        pairs = [(query, c.chunk.text) for c in candidates]
        scores = model.predict(pairs)

        reranked = [
            RetrievedChunk(chunk=c.chunk, score=c.score, rerank_score=float(s))
            for c, s in zip(candidates, scores)
        ]
        reranked.sort(key=lambda r: r.rerank_score, reverse=True)
        return reranked
