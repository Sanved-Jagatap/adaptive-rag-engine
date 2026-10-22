"""
app/retrieval/types.py

Shared types across retrieval strategies, so vector.py, bm25.py, and
hybrid.py all produce/consume the same shape and hybrid.py can fuse results
from the other two without any conversion.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.schemas import Chunk


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float
    rerank_score: float | None = None  # set by the reranker, if applied
