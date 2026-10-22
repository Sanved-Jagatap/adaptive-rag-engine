from app.generation.confidence import compute_confidence
from app.models.schemas import Chunk
from app.retrieval.types import RetrievedChunk


def make_retrieved(rerank_scores: list[float | None]) -> list[RetrievedChunk]:
    result = []
    for i, rs in enumerate(rerank_scores):
        chunk = Chunk(chunk_id=f"c{i+1}", doc_id="d", text=f"text {i+1}", chunk_index=i, token_count=2)
        result.append(RetrievedChunk(chunk=chunk, score=0.5, rerank_score=rs))
    return result


def test_no_sufficient_evidence_is_level_none():
    result = compute_confidence(
        cited_sources=[], invalid_citations=[], sufficient_evidence=False, retrieved=make_retrieved([0.9])
    )
    assert result.level == "none"


def test_empty_cited_sources_is_level_none_even_if_sufficient_evidence_true():
    result = compute_confidence(
        cited_sources=[], invalid_citations=[], sufficient_evidence=True, retrieved=make_retrieved([0.9])
    )
    assert result.level == "none"


def test_partial_hallucination_is_level_low():
    # 1 real citation, 1 hallucinated — coverage is 0.5, not full.
    result = compute_confidence(
        cited_sources=[1], invalid_citations=[9], sufficient_evidence=True, retrieved=make_retrieved([0.9])
    )
    assert result.level == "low"
    assert result.citation_coverage == 0.5


def test_full_coverage_with_positive_rerank_score_is_high():
    result = compute_confidence(
        cited_sources=[1], invalid_citations=[], sufficient_evidence=True, retrieved=make_retrieved([0.8])
    )
    assert result.level == "high"
    assert result.citation_coverage == 1.0
    assert result.avg_rerank_score == 0.8


def test_full_coverage_with_negative_rerank_score_is_medium():
    result = compute_confidence(
        cited_sources=[1], invalid_citations=[], sufficient_evidence=True, retrieved=make_retrieved([-0.3])
    )
    assert result.level == "medium"


def test_full_coverage_without_reranking_falls_back_to_medium():
    # rerank_score is None — reranking wasn't applied for this query.
    result = compute_confidence(
        cited_sources=[1], invalid_citations=[], sufficient_evidence=True, retrieved=make_retrieved([None])
    )
    assert result.level == "medium"
    assert result.avg_rerank_score is None


def test_multiple_cited_sources_averages_rerank_scores():
    result = compute_confidence(
        cited_sources=[1, 2],
        invalid_citations=[],
        sufficient_evidence=True,
        retrieved=make_retrieved([0.6, 0.4]),
    )
    assert result.avg_rerank_score == 0.5
    assert result.level == "high"
