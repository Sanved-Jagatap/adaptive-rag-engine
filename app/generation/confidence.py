"""
app/generation/confidence.py

Confidence scoring, deliberately NOT built by averaging raw retrieval
scores across strategies. Vector cosine similarity, BM25 scores, and
cross-encoder rerank scores live on different, non-comparable scales — the
same reason hybrid.py fuses on rank position (RRF) rather than raw score.
Pretending they're comparable would produce a confidence number that looks
precise but means nothing.

Instead this uses two signals that ARE meaningful regardless of which
retrieval strategy was used:

  1. citation_coverage — of the sources the model claimed to cite, what
     fraction actually exist? This is strategy-agnostic by construction.
  2. avg_rerank_score — only available when reranking was applied (all
     candidates scored by the same cross-encoder, so genuinely comparable).
     When reranking wasn't applied, this is None and the level falls back
     to the coarser coverage-only signal.

No calibrated numeric threshold exists for "how high a rerank score means
high confidence" — per docs/evaluation-plan.md, thresholds get swept
against real eval data once it exists, not guessed. For now this uses
sign only (positive vs non-positive) as a coarse split, which is honest
about being coarse rather than presenting false precision.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.retrieval.types import RetrievedChunk


@dataclass
class ConfidenceResult:
    level: str  # "none" | "low" | "medium" | "high"
    citation_coverage: float  # valid citations / total citations claimed, 0.0-1.0
    avg_rerank_score: float | None  # None if reranking wasn't applied to the cited sources


def compute_confidence(
    cited_sources: list[int],
    invalid_citations: list[int],
    sufficient_evidence: bool,
    retrieved: list[RetrievedChunk],
) -> ConfidenceResult:
    total_claimed = len(cited_sources) + len(invalid_citations)
    coverage = (len(cited_sources) / total_claimed) if total_claimed > 0 else 0.0

    if not sufficient_evidence or not cited_sources:
        return ConfidenceResult(level="none", citation_coverage=coverage, avg_rerank_score=None)

    rerank_scores = [
        retrieved[s - 1].rerank_score
        for s in cited_sources
        if 0 <= s - 1 < len(retrieved) and retrieved[s - 1].rerank_score is not None
    ]
    avg_rerank = sum(rerank_scores) / len(rerank_scores) if rerank_scores else None

    if coverage < 1.0:
        # Some of what the model claimed to cite was real, some wasn't —
        # partial hallucination. Don't call this "high" even if the real
        # part scores well.
        level = "low"
    elif avg_rerank is not None:
        level = "high" if avg_rerank > 0 else "medium"
    else:
        # No reranking applied — coverage is complete but we have no
        # comparable graded score to split further.
        level = "medium"

    return ConfidenceResult(level=level, citation_coverage=coverage, avg_rerank_score=avg_rerank)
