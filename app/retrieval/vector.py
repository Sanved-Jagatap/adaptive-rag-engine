"""
app/retrieval/vector.py

Semantic vector retrieval: embed the query, search Qdrant, return chunks
ranked by similarity. This is the "vector" leg of the adaptive router's
three strategies (vector/bm25/hybrid).
"""

from __future__ import annotations

from app.core.qdrant_store import QdrantStore
from app.ingestion.embedder import Embedder
from app.models.schemas import Chunk
from app.retrieval.types import RetrievedChunk


class VectorRetriever:
    def __init__(self, embedder: Embedder, store: QdrantStore):
        self.embedder = embedder
        self.store = store

    def index_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        vectors = self.embedder.embed([c.text for c in chunks])
        payloads = [
            {
                "doc_id": c.doc_id,
                "text": c.text,
                "chunk_index": c.chunk_index,
                "token_count": c.token_count,
                **c.metadata,
            }
            for c in chunks
        ]
        chunk_ids = [c.chunk_id for c in chunks]
        self.store.ensure_collection()
        self.store.upsert_chunks(chunk_ids, vectors, payloads)

    def search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        query_vector = self.embedder.embed([query])[0]
        results = self.store.search(query_vector, top_k=top_k)

        retrieved = []
        for point in results:
            payload = point.payload or {}
            chunk = Chunk(
                chunk_id=payload.get("chunk_id", str(point.id)),
                doc_id=payload.get("doc_id", ""),
                text=payload.get("text", ""),
                chunk_index=payload.get("chunk_index", 0),
                token_count=payload.get("token_count", 0),
                metadata={k: v for k, v in payload.items() if k not in {"doc_id", "text", "chunk_index", "token_count", "chunk_id"}},
            )
            retrieved.append(RetrievedChunk(chunk=chunk, score=point.score))
        return retrieved
