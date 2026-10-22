"""
app/core/qdrant_store.py

Thin wrapper around qdrant-client. Supports two modes:
  - Real server (host/port from settings) — used in Docker/production.
  - In-memory (location=":memory:") — used in tests, so vector search logic
    can be verified without a running Qdrant instance or network access.
    Data doesn't persist across process restarts in this mode, which is
    exactly what you want for a test fixture.
"""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    ScoredPoint,
    VectorParams,
)

from app.core.config import settings


class QdrantStore:
    def __init__(
        self,
        collection_name: str | None = None,
        vector_size: int | None = None,
        in_memory: bool = False,
    ):
        self.collection_name = collection_name or settings.qdrant_collection
        self.vector_size = vector_size or 384  # matches default embedder dim

        if in_memory:
            self.client = QdrantClient(location=":memory:")
        else:
            self.client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

    def ensure_collection(self) -> None:
        existing = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )

    def upsert_chunks(self, chunk_ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> None:
        if not (len(chunk_ids) == len(vectors) == len(payloads)):
            raise ValueError("chunk_ids, vectors, and payloads must be the same length")

        points = [
            PointStruct(id=_stable_point_id(chunk_id), vector=vector, payload={**payload, "chunk_id": chunk_id})
            for chunk_id, vector, payload in zip(chunk_ids, vectors, payloads)
        ]
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self, query_vector: list[float], top_k: int = 5) -> list[ScoredPoint]:
        return self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
        )


def _stable_point_id(chunk_id: str) -> int:
    # Qdrant point IDs must be int or UUID, not arbitrary strings — derive a
    # stable int from the chunk_id so re-ingesting the same chunk upserts
    # rather than duplicates.
    import hashlib

    return int(hashlib.sha256(chunk_id.encode()).hexdigest()[:12], 16)
