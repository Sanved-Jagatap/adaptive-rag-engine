"""
scripts/run_evaluation.py

Ingests an evaluation corpus into a fresh in-memory index, runs the
evaluation dataset against both baseline (vector-only) and adaptive
(full router: strategy selection + optional rerank) retrieval, and
prints Recall@K / Precision@K / MRR comparison.

The script also runs the generation pipeline and writes detailed
per-query generation diagnostics to:

    experiments/generation_diagnostics_v2.jsonl

Two run modes:

  --stub
      No network required. Uses deterministic stub components.
      Numbers are NOT meaningful for reporting.

  default
      Real sentence-transformers embedder + real cross-encoder +
      real Ollama for the router and generation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from app.core.ollama_client import ChatResult, OllamaClient
from app.core.qdrant_store import QdrantStore

from app.evaluation.faithfulness import judge_faithfulness

from app.evaluation.runner import (
    GenerationEvalResult,
    aggregate_generation_results,
    aggregate_results,
    load_eval_dataset,
    run_evaluation,
)

from app.evaluation.timing import StageTimer

from app.generation.confidence import compute_confidence
from app.generation.finalize import finalize_answer
from app.generation.generator import generate_answer
from app.generation.validator import validate_generation

from app.ingestion.chunker import chunk_document
from app.ingestion.loader import load_directory

from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.types import RetrievedChunk
from app.retrieval.vector import VectorRetriever

from app.routing.query_router import (
    RoutingLogger,
    Strategy,
    route_query,
)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_CORPUS_DIR = (
    REPO_ROOT / "data" / "raw"
)

DEFAULT_EVAL_DATASET = (
    REPO_ROOT / "experiments" / "eval_dataset_v1.jsonl"
)

DEFAULT_ROUTING_LOG = (
    REPO_ROOT / "experiments" / "eval_routing_log.jsonl"
)

DEFAULT_RESULTS_PATH = (
    REPO_ROOT / "experiments" / "latest_results.json"
)

DEFAULT_GENERATION_DIAGNOSTICS_PATH = (
    REPO_ROOT / "experiments" / "generation_diagnostics_v2.jsonl"
)


# ---------------------------------------------------------------------------
# Stub components
# ---------------------------------------------------------------------------

class StubReranker:
    """Pass-through reranker for --stub mode."""

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


def _stub_llm_router(messages: list[dict]) -> str:
    """
    Always routes to hybrid and enables reranking.

    Stub mode does not perform real query rewriting.
    """

    return (
        '{"strategy": "hybrid", '
        '"rewrite": null, '
        '"rerank": true}'
    )


class StubOllamaClient(OllamaClient):
    """
    Canned generation/judge responses for --stub mode.

    This verifies that the evaluation machinery works end-to-end.
    The resulting generation quality numbers are not meaningful.
    """

    def __init__(self):
        pass

    async def chat_with_usage(
        self,
        messages: list[dict],
        temperature: float = 0.0,
    ) -> ChatResult:

        system_content = (
            messages[0]["content"]
            if messages
            else ""
        )

        if "faithfulness" in system_content.lower():
            content = (
                '{"faithfulness": 1.0, '
                '"relevance": 1.0, '
                '"reasoning": "stub mode - not a real judgment"}'
            )
        else:
            content = (
                '{"answer": "stub answer", '
                '"cited_sources": [1], '
                '"sufficient_evidence": true}'
            )

        return ChatResult(
            content=content,
            prompt_tokens=10,
            completion_tokens=5,
            total_duration_ns=1_000_000,
            load_duration_ns=0,
            eval_duration_ns=1_000_000,
        )

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.0,
    ) -> str:

        result = await self.chat_with_usage(
            messages,
            temperature=temperature,
        )

        return result.content


# ---------------------------------------------------------------------------
# Index building
# ---------------------------------------------------------------------------

def build_index(
    corpus_dir: Path,
    vector_retriever: VectorRetriever,
    bm25_retriever: BM25Retriever,
) -> int:

    documents = load_directory(corpus_dir)

    all_chunks = []

    for doc in documents:
        all_chunks.extend(
            chunk_document(doc)
        )

    vector_retriever.index_chunks(
        all_chunks
    )

    bm25_retriever.index_chunks(
        all_chunks
    )

    return len(all_chunks)


# ---------------------------------------------------------------------------
# Baseline retrieval
# ---------------------------------------------------------------------------

def make_baseline_fn(
    vector_retriever: VectorRetriever,
    k: int,
):

    def baseline_fn(
        query: str,
    ) -> list[str]:

        results = vector_retriever.search(
            query,
            top_k=k,
        )

        return [
            r.chunk.chunk_id
            for r in results
        ]

    return baseline_fn


# ---------------------------------------------------------------------------
# Adaptive retrieval
# ---------------------------------------------------------------------------

def make_adaptive_fn(
    vector_retriever: VectorRetriever,
    bm25_retriever: BM25Retriever,
    hybrid_retriever: HybridRetriever,
    reranker,
    llm_call_fn,
    routing_logger: RoutingLogger,
    k: int,
):

    def adaptive_fn(
        query: str,
    ) -> list[str]:

        plan = route_query(
            query,
            llm_call_fn=llm_call_fn,
            logger=routing_logger,
        )

        used_query = (
            plan.rewritten_query
            or query
        )

        if plan.strategy == Strategy.VECTOR:

            retrieved = vector_retriever.search(
                used_query,
                top_k=k,
            )

        elif plan.strategy == Strategy.BM25:

            retrieved = bm25_retriever.search(
                used_query,
                top_k=k,
            )

        else:

            retrieved = hybrid_retriever.search(
                used_query,
                top_k=k,
            )

        if plan.rerank and retrieved:

            retrieved = reranker.rerank(
                used_query,
                retrieved,
            )[:k]

        return [
            r.chunk.chunk_id
            for r in retrieved
        ]

    return adaptive_fn


# ---------------------------------------------------------------------------
# Retrieval comparison output
# ---------------------------------------------------------------------------

def print_comparison_table(
    baseline_agg: dict,
    adaptive_agg: dict,
    k: int,
):

    print(
        f"\n{'':22}"
        f"Recall@{k}   "
        f"Precision@{k}   "
        f"MRR      "
        f"N"
    )

    print("-" * 60)

    for name, agg in [
        ("Vector RAG (baseline)", baseline_agg),
        ("Adaptive RAG", adaptive_agg),
    ]:

        o = agg["overall"]

        print(
            f"{name:22}"
            f"{o['recall_at_k']:.3f}      "
            f"{o['precision_at_k']:.3f}         "
            f"{o['mrr']:.3f}    "
            f"{o['num_queries']}"
        )

    print("\nAdaptive RAG by category:")

    print(
        f"{'':14}"
        f"Recall@{k}   "
        f"Precision@{k}   "
        f"MRR      "
        f"N"
    )

    print("-" * 55)

    for cat, metrics in sorted(
        adaptive_agg["by_category"].items()
    ):

        print(
            f"{cat:14}"
            f"{metrics['recall_at_k']:.3f}      "
            f"{metrics['precision_at_k']:.3f}         "
            f"{metrics['mrr']:.3f}    "
            f"{metrics['num_queries']}"
        )


# ---------------------------------------------------------------------------
# Generation diagnostics
# ---------------------------------------------------------------------------

def build_generation_diagnostic(
    eq,
    plan,
    used_query: str,
    retrieved: list[RetrievedChunk],
    validated,
    confidence,
    final_answer: str,
    judge_result,
    timer: StageTimer,
    prompt_tokens,
    completion_tokens,
    raw_response: str,
) -> dict:

    return {
        "query_id": eq.query_id,

        "category": eq.category,

        "original_query": eq.query,

        "used_query": used_query,

        "was_rewritten": bool(
            plan.rewritten_query
        ),

        "strategy": plan.strategy.value,

        "rerank": bool(
            plan.rerank
        ),

        "retrieved_chunk_ids": [
            r.chunk.chunk_id
            for r in retrieved
        ],

        "retrieved_scores": [
            r.score
            for r in retrieved
        ],

        "cited_sources": (
            validated.cited_sources
        ),

        "invalid_citations": (
            validated.invalid_citations
        ),

        "sufficient_evidence": (
            validated.sufficient_evidence
        ),

        "answer": final_answer,

        # Temporary diagnostic field.
        # This is the raw response already returned by Ollama.
        # No second Ollama request is made.
        "raw_response": raw_response,

        "confidence": confidence.level,

        "faithfulness": (
            judge_result.faithfulness
        ),

        "relevance": (
            judge_result.relevance
        ),

        "judge_skipped": (
            judge_result.skipped
        ),

        "prompt_tokens": prompt_tokens,

        "completion_tokens": completion_tokens,

        "routing_ms": timer.timings_ms.get(
            "routing",
            0.0,
        ),

        "retrieval_ms": timer.timings_ms.get(
            "retrieval",
            0.0,
        ),

        "rerank_ms": timer.timings_ms.get(
            "rerank",
            0.0,
        ),

        "generation_ms": timer.timings_ms.get(
            "generation",
            0.0,
        ),

        "judge_ms": timer.timings_ms.get(
            "judge",
            0.0,
        ),

        "total_ms": timer.total_ms,
    }


def write_generation_diagnostics(
    diagnostics: list[dict],
    output_path: Path,
) -> None:

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:

        for record in diagnostics:

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(
        f"Saved generation diagnostics to "
        f"{output_path}"
    )


# ---------------------------------------------------------------------------
# Per-query generation evaluation
# ---------------------------------------------------------------------------

async def evaluate_one_query_generation(
    eq,
    vector_retriever: VectorRetriever,
    bm25_retriever: BM25Retriever,
    hybrid_retriever: HybridRetriever,
    reranker,
    llm_call_fn,
    routing_logger: RoutingLogger,
    ollama_client: OllamaClient,
    k: int,
) -> tuple[GenerationEvalResult, dict]:

    """
    Runs the same pipeline exposed by /query:

        route
        retrieve
        rerank
        generate
        validate
        confidence
        judge

    The function returns:

        1. GenerationEvalResult
        2. Detailed per-query diagnostic dictionary
    """

    timer = StageTimer()

    # ---------------------------------------------------------------
    # Routing
    # ---------------------------------------------------------------

    with timer.track("routing"):

        plan = route_query(
            eq.query,
            llm_call_fn=llm_call_fn,
            logger=routing_logger,
        )

    used_query = (
        plan.rewritten_query
        or eq.query
    )

    # ---------------------------------------------------------------
    # Retrieval
    # ---------------------------------------------------------------

    with timer.track("retrieval"):

        if plan.strategy == Strategy.VECTOR:

            retrieved = vector_retriever.search(
                used_query,
                top_k=k,
            )

        elif plan.strategy == Strategy.BM25:

            retrieved = bm25_retriever.search(
                used_query,
                top_k=k,
            )

        else:

            retrieved = hybrid_retriever.search(
                used_query,
                top_k=k,
            )

    # ---------------------------------------------------------------
    # Reranking
    # ---------------------------------------------------------------

    if plan.rerank and retrieved:

        with timer.track("rerank"):

            retrieved = reranker.rerank(
                used_query,
                retrieved,
            )[:k]

    # ---------------------------------------------------------------
    # Generation
    # ---------------------------------------------------------------

    prompt_tokens = None
    completion_tokens = None

    with timer.track("generation"):

        gen_result = await generate_answer(
            used_query,
            retrieved,
            ollama_client,
        )

        # generate_answer() performs the single Ollama generation call
        # and preserves Ollama's native usage metadata on
        # GenerationResult.
        #
        # Do not make a second generation request just to collect
        # metrics.

        prompt_tokens = gen_result.prompt_tokens
        completion_tokens = gen_result.completion_tokens

    # ---------------------------------------------------------------
    # Validation
    # ---------------------------------------------------------------

    validated = validate_generation(
        gen_result,
        num_sources=len(retrieved),
    )

    # ---------------------------------------------------------------
    # Confidence
    # ---------------------------------------------------------------

    confidence = compute_confidence(
        cited_sources=(
            validated.cited_sources
        ),

        invalid_citations=(
            validated.invalid_citations
        ),

        sufficient_evidence=(
            validated.sufficient_evidence
        ),

        retrieved=retrieved,
    )

    final_answer = finalize_answer(
        validated
    )

    # ---------------------------------------------------------------
    # Faithfulness / relevance judge
    # ---------------------------------------------------------------

    cited_texts = [
        retrieved[s - 1].chunk.text
        for s in validated.cited_sources
        if 0 <= s - 1 < len(retrieved)
    ]

    with timer.track("judge"):

        judge_result = await judge_faithfulness(
            used_query,
            final_answer,
            cited_texts,
            ollama_client,
        )

    # ---------------------------------------------------------------
    # Existing aggregate result
    # ---------------------------------------------------------------

    result = GenerationEvalResult(
        query_id=eq.query_id,

        category=eq.category,

        sufficient_evidence=(
            validated.sufficient_evidence
        ),

        confidence_level=confidence.level,

        faithfulness=(
            judge_result.faithfulness
        ),

        relevance=(
            judge_result.relevance
        ),

        judge_skipped=(
            judge_result.skipped
        ),

        prompt_tokens=prompt_tokens,

        completion_tokens=completion_tokens,

        routing_ms=timer.timings_ms.get(
            "routing",
            0.0,
        ),

        retrieval_ms=timer.timings_ms.get(
            "retrieval",
            0.0,
        ),

        rerank_ms=timer.timings_ms.get(
            "rerank",
            0.0,
        ),

        generation_ms=timer.timings_ms.get(
            "generation",
            0.0,
        ),

        judge_ms=timer.timings_ms.get(
            "judge",
            0.0,
        ),

        total_ms=timer.total_ms,
    )

    # ---------------------------------------------------------------
    # Detailed diagnostic result
    # ---------------------------------------------------------------

    diagnostic = build_generation_diagnostic(
        eq=eq,
        plan=plan,
        used_query=used_query,
        retrieved=retrieved,
        validated=validated,
        confidence=confidence,
        final_answer=final_answer,
        judge_result=judge_result,
        timer=timer,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        raw_response=gen_result.raw_response,
    )

    return result, diagnostic


# ---------------------------------------------------------------------------
# Run generation evaluation
# ---------------------------------------------------------------------------

async def run_generation_eval(
    eval_queries,
    *args,
    **kwargs,
) -> tuple[
    list[GenerationEvalResult],
    list[dict],
]:

    # Sequential execution is intentional.
    # Local Ollama is being evaluated as a single-serving model.
    # Concurrent requests would make latency measurements less useful.

    results = []

    diagnostics = []

    for eq in eval_queries:

        result, diagnostic = (
            await evaluate_one_query_generation(
                eq,
                *args,
                **kwargs,
            )
        )

        results.append(result)

        diagnostics.append(
            diagnostic
        )

    return results, diagnostics


# ---------------------------------------------------------------------------
# Generation summary
# ---------------------------------------------------------------------------

def print_generation_summary(
    agg: dict,
    k: int,
):

    o = agg["overall"]

    print(
        f"\nAdaptive RAG generation quality "
        f"(top-{k}):"
    )

    print(
        f"  Sufficient evidence rate: "
        f"{o['sufficient_evidence_rate']:.2f}"
    )

    print(
        f"  Avg faithfulness:         "
        f"{o['avg_faithfulness']:.2f}  "
        f"(n={o['num_judged']} judged)"
    )

    print(
        f"  Avg relevance:            "
        f"{o['avg_relevance']:.2f}"
    )

    if o["avg_prompt_tokens"] is not None:

        print(
            f"  Avg tokens "
            f"(prompt/completion): "
            f"{o['avg_prompt_tokens']:.0f} / "
            f"{o['avg_completion_tokens']:.0f}"
        )

    print(
        f"  Avg total latency:        "
        f"{o['avg_total_ms']:.0f}ms  "
        f"(generation: "
        f"{o['avg_generation_ms']:.0f}ms)"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Run baseline vs adaptive RAG evaluation"
        )
    )

    parser.add_argument(
        "--k",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=DEFAULT_CORPUS_DIR,
    )

    parser.add_argument(
        "--eval-dataset",
        type=Path,
        default=DEFAULT_EVAL_DATASET,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_RESULTS_PATH,
        help=(
            "Path to save JSON results. "
            "The frontend evaluation dashboard reads this file."
        ),
    )

    parser.add_argument(
        "--stub",
        action="store_true",
        help=(
            "Use network-free stub "
            "embedder/reranker/router-LLM."
        ),
    )

    parser.add_argument(
        "--skip-generation",
        action="store_true",
        help=(
            "Only run retrieval metrics; "
            "skip generation/faithfulness/latency."
        ),
    )

    args = parser.parse_args()

    # ---------------------------------------------------------------
    # Components
    # ---------------------------------------------------------------

    if args.stub:

        from tests.stub_embedder import StubEmbedder
        from app.retrieval.reranker import CrossEncoderReranker

        embedder = StubEmbedder()

        reranker = StubReranker()

        llm_call_fn = _stub_llm_router

        ollama_client = StubOllamaClient()

        print(
            "Running in --stub mode: "
            "numbers below are NOT meaningful; "
            "this only verifies the pipeline "
            "runs end to end.\n"
        )

    else:

        from app.ingestion.embedder import (
            SentenceTransformerEmbedder,
        )

        from app.retrieval.reranker import (
            CrossEncoderReranker,
        )

        embedder = SentenceTransformerEmbedder()

        reranker = CrossEncoderReranker()

        # route_query will use the configured Ollama
        # router client when this is None.

        llm_call_fn = None

        ollama_client = OllamaClient()

    # ---------------------------------------------------------------
    # Retrievers
    # ---------------------------------------------------------------

    store = QdrantStore(
        collection_name="eval_run",
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

    routing_logger = RoutingLogger(
        log_path=str(
            DEFAULT_ROUTING_LOG
        )
    )

    # ---------------------------------------------------------------
    # Index corpus
    # ---------------------------------------------------------------

    num_chunks = build_index(
        args.corpus_dir,
        vector_retriever,
        bm25_retriever,
    )

    print(
        f"Indexed {num_chunks} chunks "
        f"from {args.corpus_dir}"
    )

    # ---------------------------------------------------------------
    # Load evaluation queries
    # ---------------------------------------------------------------

    eval_queries = load_eval_dataset(
        args.eval_dataset
    )

    print(
        f"Loaded {len(eval_queries)} eval queries "
        f"from {args.eval_dataset}"
    )

    # ---------------------------------------------------------------
    # Retrieval evaluation
    # ---------------------------------------------------------------

    baseline_fn = make_baseline_fn(
        vector_retriever,
        args.k,
    )

    adaptive_fn = make_adaptive_fn(
        vector_retriever,
        bm25_retriever,
        hybrid_retriever,
        reranker,
        llm_call_fn,
        routing_logger,
        args.k,
    )

    baseline_results = run_evaluation(
        eval_queries,
        baseline_fn,
        k=args.k,
    )

    adaptive_results = run_evaluation(
        eval_queries,
        adaptive_fn,
        k=args.k,
    )

    baseline_agg = aggregate_results(
        baseline_results
    )

    adaptive_agg = aggregate_results(
        adaptive_results
    )

    print_comparison_table(
        baseline_agg,
        adaptive_agg,
        args.k,
    )

    # ---------------------------------------------------------------
    # Generation evaluation
    # ---------------------------------------------------------------

    generation_agg = None

    generation_diagnostics = []

    if not args.skip_generation:

        (
            generation_results,
            generation_diagnostics,
        ) = asyncio.run(
            run_generation_eval(
                eval_queries,
                vector_retriever,
                bm25_retriever,
                hybrid_retriever,
                reranker,
                llm_call_fn,
                routing_logger,
                ollama_client,
                args.k,
            )
        )

        generation_agg = (
            aggregate_generation_results(
                generation_results
            )
        )

        print_generation_summary(
            generation_agg,
            args.k,
        )

        # -----------------------------------------------------------
        # Save per-query diagnostics
        # -----------------------------------------------------------

        write_generation_diagnostics(
            generation_diagnostics,
            DEFAULT_GENERATION_DIAGNOSTICS_PATH,
        )

    # ---------------------------------------------------------------
    # Save aggregate results
    # ---------------------------------------------------------------

    if args.output:

        output_data = {
            "k": args.k,

            "stub_mode": args.stub,

            "generated_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),

            "baseline": baseline_agg,

            "adaptive": adaptive_agg,

            "generation": generation_agg,
        }

        args.output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        args.output.write_text(
            json.dumps(
                output_data,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(
            f"\nSaved results to "
            f"{args.output}"
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()