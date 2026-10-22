"""
app/api/routes/query.py

POST /query — the adaptive path. Uses query_router.route_query() to pick
vector/bm25/hybrid, retrieves with whichever strategy was chosen, reranks
if the router says to, then generates a grounded answer.

route_query() is synchronous (its LLM fallback uses a blocking HTTP call
via OllamaRouterClient) — run it in FastAPI's threadpool via
run_in_threadpool so it doesn't block the event loop for other requests.

Response includes routing metadata (strategy, decided_by, was_rewritten)
alongside the answer — not just for debugging, but because this is exactly
what needs to be visible once you're comparing baseline vs adaptive RAG
in the Phase 5 evaluation.
"""

import logging
import time

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.core.dependencies import (
    get_bm25_retriever,
    get_hybrid_retriever,
    get_reranker,
    get_routing_logger,
    get_vector_retriever,
)
from app.core.ollama_client import ollama_client
from app.generation.confidence import compute_confidence
from app.generation.finalize import finalize_answer
from app.generation.generator import generate_answer
from app.generation.validator import validate_generation
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.vector import VectorRetriever
from app.routing.query_router import RoutingLogger, Strategy, route_query

router = APIRouter()
# Named _log, not "logger" — the endpoint below already has a `logger`
# parameter (the RoutingLogger dependency), and shadowing would be a
# confusing bug waiting to happen.
_log = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    recent_context: str = ""


class QueryResponse(BaseModel):
    answer: str
    cited_sources: list[int]
    invalid_citations: list[int]
    sufficient_evidence: bool
    confidence_level: str
    citation_coverage: float
    sources: list[dict]
    strategy: str
    decided_by: str
    was_rewritten: bool
    used_query: str


@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    vector_retriever: VectorRetriever = Depends(get_vector_retriever),
    bm25_retriever: BM25Retriever = Depends(get_bm25_retriever),
    hybrid_retriever: HybridRetriever = Depends(get_hybrid_retriever),
    reranker: CrossEncoderReranker = Depends(get_reranker),
    logger: RoutingLogger = Depends(get_routing_logger),
):
    start = time.perf_counter()
    plan = await run_in_threadpool(route_query, request.query, None, request.recent_context, logger)
    _log.info(
        "routing decision query=%r strategy=%s decided_by=%s rewritten=%s",
        request.query,
        plan.strategy.value,
        plan.decided_by,
        plan.query_rewrite,
    )

    used_query = plan.rewritten_query or request.query

    if plan.strategy == Strategy.VECTOR:
        retrieved = vector_retriever.search(used_query, top_k=request.top_k)
    elif plan.strategy == Strategy.BM25:
        retrieved = bm25_retriever.search(used_query, top_k=request.top_k)
    else:
        retrieved = hybrid_retriever.search(used_query, top_k=request.top_k)

    if plan.rerank and retrieved:
        retrieved = reranker.rerank(used_query, retrieved)[: request.top_k]

    result = await generate_answer(used_query, retrieved, ollama_client)
    validated = validate_generation(result, num_sources=len(retrieved))
    confidence = compute_confidence(
        cited_sources=validated.cited_sources,
        invalid_citations=validated.invalid_citations,
        sufficient_evidence=validated.sufficient_evidence,
        retrieved=retrieved,
    )

    if validated.invalid_citations:
        # Real observability signal: the model cited sources that don't
        # exist. Worth a WARNING, not just carrying the count silently in
        # the response body — this is exactly the kind of thing you'd want
        # an alert on on in production if the rate climbed.
        _log.warning(
            "hallucinated citations query=%r invalid_citations=%s",
            request.query,
            validated.invalid_citations,
        )

    elapsed_ms = (time.perf_counter() - start) * 1000
    _log.info(
        "query completed query=%r confidence=%s sufficient_evidence=%s elapsed_ms=%.0f",
        request.query,
        confidence.level,
        validated.sufficient_evidence,
        elapsed_ms,
    )

    return QueryResponse(
        answer=finalize_answer(validated),
        cited_sources=validated.cited_sources,
        invalid_citations=validated.invalid_citations,
        sufficient_evidence=validated.sufficient_evidence,
        confidence_level=confidence.level,
        citation_coverage=confidence.citation_coverage,
        sources=[
            {
                "chunk_id": r.chunk.chunk_id,
                "text": r.chunk.text,
                "score": r.score,
                "rerank_score": r.rerank_score,
            }
            for r in retrieved
        ],
        strategy=plan.strategy.value,
        decided_by=plan.decided_by,
        was_rewritten=plan.query_rewrite,
        used_query=used_query,
    )