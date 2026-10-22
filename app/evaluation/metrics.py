"""
app/evaluation/metrics.py

Core retrieval metrics, as pure functions: given the set of relevant chunk
IDs for a query (from the eval dataset) and the ranked list of chunk IDs
actually retrieved, compute Recall@K / Precision@K / MRR. Kept independent
of the retrieval/generation stack entirely — these functions don't know
about Qdrant, BM25, or the router, so they're trivial to unit test and
reusable for any retrieval system, not just this one.
"""

from __future__ import annotations


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Fraction of relevant chunks that appear in the top-k retrieved.
    Returns 0.0 if there are no relevant chunks for this query — an empty
    ground truth can't be "recalled," and treating it as 1.0 (vacuously
    true) would silently inflate the average across a dataset."""
    if not relevant_ids:
        return 0.0
    top_k = set(retrieved_ids[:k])
    hits = len(top_k & relevant_ids)
    return hits / len(relevant_ids)


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Fraction of the top-k retrieved chunks that are actually relevant.
    Returns 0.0 if nothing was retrieved (nothing to be precise about)."""
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = len(set(top_k) & relevant_ids)
    return hits / len(top_k)


def reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    """1 / rank of the first relevant chunk in the retrieved list (rank is
    1-indexed). 0.0 if no relevant chunk appears at all. This is the
    per-query value that gets averaged into MRR across a dataset."""
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def mean_reciprocal_rank(per_query_rr: list[float]) -> float:
    """Averages reciprocal_rank() values across queries. Separated from
    reciprocal_rank() itself so the runner can log per-query RR (useful for
    slicing by category later) and only average at the end."""
    if not per_query_rr:
        return 0.0
    return sum(per_query_rr) / len(per_query_rr)
