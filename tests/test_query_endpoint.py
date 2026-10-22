"""
tests/test_query_endpoint.py

Integration test for POST /query. Everything else in tests/ verifies one
module in isolation; this is the only test that actually exercises the
wiring in app/api/routes/query.py — router picks a strategy, the matching
retriever runs, reranking applies if the router says to, generation
produces an answer.

All external dependencies (embeddings, reranking, Ollama) are swapped for
network-free doubles via dependency_overrides and mock.patch, so this runs
without any live service.
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.dependencies import (
    get_bm25_retriever,
    get_hybrid_retriever,
    get_reranker,
    get_routing_logger,
    get_vector_retriever,
)
from app.core.ollama_client import ChatResult
from app.core.qdrant_store import QdrantStore
from app.ingestion.chunker import chunk_document
from app.main import app
from app.models.schemas import Document, DocumentType
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.types import RetrievedChunk
from app.retrieval.vector import VectorRetriever
from app.routing.query_router import RoutingLogger
from tests.stub_embedder import StubEmbedder


class StubReranker:
    """Pass-through reranker — copies score into rerank_score without any
    model, so /query's rerank step is exercised without a network call."""

    def rerank(
        self,
        query: str,
        candidates: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        reranked = [
            RetrievedChunk(
                chunk=c.chunk,
                score=c.score,
                rerank_score=c.score,
            )
            for c in candidates
        ]

        reranked.sort(
            key=lambda r: r.rerank_score,
            reverse=True,
        )

        return reranked


def make_chat_result(content: str) -> ChatResult:
    """Create a deterministic Ollama response for tests.

    The real Ollama client returns usage/timing metadata alongside the
    generated content. Tests should therefore mock the complete response
    shape rather than only mocking a plain string.
    """
    return ChatResult(
        content=content,
        prompt_tokens=100,
        completion_tokens=20,
        total_duration_ns=1_000_000,
        load_duration_ns=100_000,
        eval_duration_ns=800_000,
    )


def _seeded_chunks():
    doc = Document(
        doc_id="doc1",
        source_path="doc1.txt",
        doc_type=DocumentType.TEXT,
        raw_text=(
            "The payment service retries failed requests using exponential "
            "backoff. MAX_RETRY_LIMIT controls the maximum number of "
            "attempts before giving up and routing to a dead-letter queue."
        ),
    )

    return chunk_document(
        doc,
        chunk_size_tokens=20,
        chunk_overlap_tokens=5,
    )


def _build_overrides(tmp_path):
    embedder = StubEmbedder()

    store = QdrantStore(
        collection_name="test_query_endpoint",
        vector_size=embedder.dimension,
        in_memory=True,
    )

    vector_retriever = VectorRetriever(
        embedder=embedder,
        store=store,
    )

    bm25_retriever = BM25Retriever()

    hybrid_retriever = HybridRetriever(
        vector_retriever=vector_retriever,
        bm25_retriever=bm25_retriever,
    )

    chunks = _seeded_chunks()

    vector_retriever.index_chunks(chunks)
    bm25_retriever.index_chunks(chunks)

    routing_logger = RoutingLogger(
        log_path=str(tmp_path / "routing_log.jsonl")
    )

    return {
        get_vector_retriever: lambda: vector_retriever,
        get_bm25_retriever: lambda: bm25_retriever,
        get_hybrid_retriever: lambda: hybrid_retriever,
        get_reranker: lambda: StubReranker(),
        get_routing_logger: lambda: routing_logger,
    }


def test_query_endpoint_returns_answer_and_routing_metadata(tmp_path):
    app.dependency_overrides.update(_build_overrides(tmp_path))

    try:
        with patch(
            "app.core.ollama_client.OllamaClient.chat_with_usage",
            new_callable=AsyncMock,
            return_value=make_chat_result(
                '{"answer": "MAX_RETRY_LIMIT controls the retry count.", '
                '"cited_sources": [1], '
                '"sufficient_evidence": true}'
            ),
        ):
            client = TestClient(app)

            resp = client.post(
                "/query",
                json={
                    "query": "What controls MAX_RETRY_LIMIT?",
                    "top_k": 3,
                },
            )

        assert resp.status_code == 200

        body = resp.json()

        assert body["answer"] == (
            "MAX_RETRY_LIMIT controls the retry count."
        )

        assert body["cited_sources"] == [1]
        assert body["invalid_citations"] == []
        assert body["sufficient_evidence"] is True

        assert body["confidence_level"] in {
            "none",
            "low",
            "medium",
            "high",
        }

        assert 0.0 <= body["citation_coverage"] <= 1.0

        assert body["strategy"] in {
            "vector",
            "bm25",
            "hybrid",
        }

        assert body["decided_by"] in {
            "rule",
            "llm_fallback",
            "llm_fallback_error_default",
        }

        assert isinstance(body["sources"], list)
        assert len(body["sources"]) > 0

        assert "used_query" in body

    finally:
        app.dependency_overrides.clear()


def test_query_endpoint_lexical_query_routes_to_bm25_without_llm(
    tmp_path,
):
    # An identifier-heavy query should be confident enough for the
    # rule-based router to decide without needing the LLM fallback at all —
    # this is the case that should never touch Ollama for routing.

    app.dependency_overrides.update(_build_overrides(tmp_path))

    try:
        with patch(
            "app.core.ollama_client.OllamaClient.chat_with_usage",
            new_callable=AsyncMock,
            return_value=make_chat_result(
                '{"answer": "Answer.", '
                '"cited_sources": [1], '
                '"sufficient_evidence": true}'
            ),
        ):
            client = TestClient(app)

            resp = client.post(
                "/query",
                json={
                    "query": "MAX_RETRY_LIMIT config value",
                    "top_k": 3,
                },
            )

        assert resp.status_code == 200

        body = resp.json()

        assert body["strategy"] == "bm25"
        assert body["decided_by"] == "rule"

    finally:
        app.dependency_overrides.clear()


def test_query_endpoint_downgrades_hallucinated_citations(
    tmp_path,
    caplog,
):
    # The LLM claims a confident answer citing [Source 99], which doesn't
    # exist among the (at most 3) retrieved chunks — the endpoint should
    # come back with sufficient_evidence=False and the fabricated citation
    # surfaced in invalid_citations, not silently passed through.

    app.dependency_overrides.update(_build_overrides(tmp_path))

    try:
        with patch(
            "app.core.ollama_client.OllamaClient.chat_with_usage",
            new_callable=AsyncMock,
            return_value=make_chat_result(
                '{"answer": "Confidently wrong.", '
                '"cited_sources": [99], '
                '"sufficient_evidence": true}'
            ),
        ):
            client = TestClient(app)

            with caplog.at_level("WARNING"):
                resp = client.post(
                    "/query",
                    json={
                        "query": "MAX_RETRY_LIMIT config value",
                        "top_k": 3,
                    },
                )

        assert resp.status_code == 200

        body = resp.json()

        assert body["cited_sources"] == []
        assert body["invalid_citations"] == [99]
        assert body["sufficient_evidence"] is False
        assert body["confidence_level"] == "none"

        assert body["answer"] == (
            "I don't have enough reliable information in the retrieved "
            "context to answer this confidently."
        )

        # The observability signal this is really testing: a hallucinated
        # citation must be visible in logs, not just in the response body.
        assert any(
            "hallucinated citations" in record.message
            for record in caplog.records
        )

    finally:
        app.dependency_overrides.clear()