"""
app/evaluation/runner.py

Runs the eval dataset (experiments/eval_dataset_v1.jsonl) against a
retrieval function and aggregates metrics.py's Recall@K/Precision@K/MRR,
both overall and sliced by query category (lexical/semantic/hybrid/
ambiguous) — the category slicing is what actually answers "does adaptive
routing help," not just an aggregate number.

Deliberately decoupled from the real vector/BM25/router stack:
run_evaluation() takes a retrieval_fn: (query: str) -> list[str] (ranked
chunk_ids), not a concrete retriever. That's what makes this runner
testable with a fake retrieval function (see tests/test_eval_runner.py)
independent of whether Qdrant/BM25/Ollama are actually available. Wiring
in the real baseline (vector-only) and adaptive (full router) retrieval
functions is a separate script (scripts/run_evaluation.py) built on top of
this module, not part of it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app.evaluation.metrics import mean_reciprocal_rank, precision_at_k, recall_at_k, reciprocal_rank

RetrievalFn = Callable[[str], list[str]]


@dataclass
class EvalQuery:
    query_id: str
    query: str
    category: str
    relevant_chunk_ids: set[str]
    notes: str = ""


@dataclass
class EvalResult:
    query_id: str
    category: str
    recall: float
    precision: float
    rr: float
    retrieved_ids: list[str] = field(default_factory=list)


def load_eval_dataset(path: str | Path) -> list[EvalQuery]:
    path = Path(path)
    queries = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            queries.append(
                EvalQuery(
                    query_id=data["query_id"],
                    query=data["query"],
                    category=data["category"],
                    relevant_chunk_ids=set(data["relevant_chunk_ids"]),
                    notes=data.get("notes", ""),
                )
            )
    return queries


def run_evaluation(
    eval_queries: list[EvalQuery], retrieval_fn: RetrievalFn, k: int = 5
) -> list[EvalResult]:
    results = []
    for eq in eval_queries:
        retrieved_ids = retrieval_fn(eq.query)
        results.append(
            EvalResult(
                query_id=eq.query_id,
                category=eq.category,
                recall=recall_at_k(retrieved_ids, eq.relevant_chunk_ids, k),
                precision=precision_at_k(retrieved_ids, eq.relevant_chunk_ids, k),
                rr=reciprocal_rank(retrieved_ids, eq.relevant_chunk_ids),
                retrieved_ids=retrieved_ids,
            )
        )
    return results


def aggregate_results(results: list[EvalResult]) -> dict:
    """Overall metrics plus a per-category breakdown. Per-category is the
    part that matters for this project's actual research question — an
    aggregate Recall@5 can look fine while hiding that the router is doing
    great on lexical queries and terribly on ambiguous ones."""

    def _avg(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    overall = {
        "recall_at_k": _avg([r.recall for r in results]),
        "precision_at_k": _avg([r.precision for r in results]),
        "mrr": mean_reciprocal_rank([r.rr for r in results]),
        "num_queries": len(results),
    }

    by_category: dict[str, dict] = {}
    categories = sorted({r.category for r in results})
    for cat in categories:
        cat_results = [r for r in results if r.category == cat]
        by_category[cat] = {
            "recall_at_k": _avg([r.recall for r in cat_results]),
            "precision_at_k": _avg([r.precision for r in cat_results]),
            "mrr": mean_reciprocal_rank([r.rr for r in cat_results]),
            "num_queries": len(cat_results),
        }

    return {"overall": overall, "by_category": by_category}


@dataclass
class GenerationEvalResult:
    """Per-query result from running the full retrieve -> rerank ->
    generate -> validate -> judge pipeline, not just retrieval. Separate
    from EvalResult (which is retrieval-metrics-only) because faithfulness/
    relevance/confidence/latency only exist once generation actually runs —
    conflating the two would force every retrieval-only eval to also pay
    for LLM calls it doesn't need."""

    query_id: str
    category: str
    sufficient_evidence: bool
    confidence_level: str
    faithfulness: float
    relevance: float
    judge_skipped: bool
    prompt_tokens: int | None
    completion_tokens: int | None
    routing_ms: float
    retrieval_ms: float
    rerank_ms: float
    generation_ms: float
    judge_ms: float
    total_ms: float


def aggregate_generation_results(results: list[GenerationEvalResult]) -> dict:
    """Mirrors aggregate_results()'s overall + by_category shape, but for
    generation-side metrics. Faithfulness/relevance are averaged only over
    non-skipped judgments (judge_skipped=True means no sources were cited —
    typically an abstention — and averaging in a placeholder 1.0/0.0 pair
    for those would distort the faithfulness signal for queries that DID
    get judged)."""

    def _avg(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    def _avg_optional(values: list[int | None]) -> float | None:
        present = [v for v in values if v is not None]
        return (sum(present) / len(present)) if present else None

    def _summarize(subset: list[GenerationEvalResult]) -> dict:
        judged = [r for r in subset if not r.judge_skipped]
        return {
            "sufficient_evidence_rate": _avg([1.0 if r.sufficient_evidence else 0.0 for r in subset]),
            "avg_faithfulness": _avg([r.faithfulness for r in judged]),
            "avg_relevance": _avg([r.relevance for r in judged]),
            "num_judged": len(judged),
            "avg_prompt_tokens": _avg_optional([r.prompt_tokens for r in subset]),
            "avg_completion_tokens": _avg_optional([r.completion_tokens for r in subset]),
            "avg_total_ms": _avg([r.total_ms for r in subset]),
            "avg_generation_ms": _avg([r.generation_ms for r in subset]),
            "num_queries": len(subset),
        }

    overall = _summarize(results)
    by_category = {cat: _summarize([r for r in results if r.category == cat]) for cat in sorted({r.category for r in results})}

    return {"overall": overall, "by_category": by_category}
