from unittest.mock import MagicMock, patch

from app.models.schemas import Chunk
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.types import RetrievedChunk


def make_candidates():
    chunks = [
        Chunk(chunk_id="c1", doc_id="d", text="low relevance text", chunk_index=0, token_count=3),
        Chunk(chunk_id="c2", doc_id="d", text="high relevance text", chunk_index=1, token_count=3),
        Chunk(chunk_id="c3", doc_id="d", text="medium relevance text", chunk_index=2, token_count=3),
    ]
    # Initial retrieval scores deliberately in a DIFFERENT order than the
    # rerank scores below, so a passing test actually proves reranking
    # changed the order rather than just preserving input order.
    return [
        RetrievedChunk(chunk=chunks[0], score=0.9),
        RetrievedChunk(chunk=chunks[1], score=0.5),
        RetrievedChunk(chunk=chunks[2], score=0.7),
    ]


def test_rerank_reorders_by_cross_encoder_score_not_original_score():
    candidates = make_candidates()
    reranker = CrossEncoderReranker()

    fake_model = MagicMock()
    # Cross-encoder scores: c1 (low), c2 (high), c3 (medium) — matches the
    # chunk text labels, inverse of the original retrieval score order.
    fake_model.predict.return_value = [0.1, 0.9, 0.5]

    with patch.object(reranker, "_load", return_value=fake_model):
        results = reranker.rerank("some query", candidates)

    assert [r.chunk.chunk_id for r in results] == ["c2", "c3", "c1"]
    assert results[0].rerank_score == 0.9
    # Original retrieval score should be preserved alongside rerank_score.
    assert results[0].score == 0.5


def test_rerank_on_empty_candidates_returns_empty_without_loading_model():
    reranker = CrossEncoderReranker()
    with patch.object(reranker, "_load") as mock_load:
        results = reranker.rerank("query", [])
    assert results == []
    mock_load.assert_not_called()


def test_model_is_loaded_lazily_not_at_construction():
    reranker = CrossEncoderReranker()
    assert reranker._model is None  # no network call has happened yet
