"""
app/retrieval/hybrid.py

Hybrid retrieval: run vector and BM25 search in parallel, fuse results with
Reciprocal Rank Fusion (RRF). RRF is used instead of a weighted score
combination because cosine similarity and BM25 scores live on different,
non-comparable scales — RRF sidesteps that by fusing on rank position
rather than raw score, which is the standard approach for this reason.
"""

from __future__ import annotations

from collections import defaultdict

from app.retrieval.bm25 import BM25Retriever
from app.retrieval.types import RetrievedChunk
from app.retrieval.vector import VectorRetriever

DEFAULT_RRF_K = 60  # standard default from the original RRF paper; dampens
# the influence of any single top-ranked result


def reciprocal_rank_fusion(
    result_lists: list[list[RetrievedChunk]], k: int = DEFAULT_RRF_K
) -> list[RetrievedChunk]:
    fused_scores: dict[str, float] = defaultdict(float)
    chunk_lookup = {}

    for results in result_lists:
        for rank, r in enumerate(results):
            fused_scores[r.chunk.chunk_id] += 1.0 / (k + rank + 1)
            chunk_lookup[r.chunk.chunk_id] = r.chunk

    ranked_ids = sorted(fused_scores.items(), key=lambda item: item[1], reverse=True)
    return [
        RetrievedChunk(chunk=chunk_lookup[chunk_id], score=score)
        for chunk_id, score in ranked_ids
    ]


class HybridRetriever:
    def __init__(self, vector_retriever: VectorRetriever, bm25_retriever: BM25Retriever):
        self.vector_retriever = vector_retriever
        self.bm25_retriever = bm25_retriever

    def search(self, query: str, top_k: int = 5, overfetch_multiplier: int = 3) -> list[RetrievedChunk]:
        # Overfetch from each leg before fusion — RRF needs a reasonable
        # candidate pool per source to produce a meaningful fused ranking,
        # not just the final top_k from each.
        fetch_k = top_k * overfetch_multiplier
        vector_results = self.vector_retriever.search(query, top_k=fetch_k)
        bm25_results = self.bm25_retriever.search(query, top_k=fetch_k)

        fused = reciprocal_rank_fusion([vector_results, bm25_results])
        return fused[:top_k]
