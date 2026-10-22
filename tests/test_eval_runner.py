from pathlib import Path

from app.evaluation.runner import (
    EvalQuery,
    aggregate_results,
    load_eval_dataset,
    run_evaluation,
)

REAL_EVAL_DATASET = Path(__file__).resolve().parent.parent / "experiments" / "eval_dataset_v1.jsonl"


def test_load_eval_dataset_reads_the_real_seed_dataset():
    queries = load_eval_dataset(REAL_EVAL_DATASET)
    assert len(queries) == 15
    categories = {q.category for q in queries}
    assert categories == {"lexical", "semantic", "hybrid", "ambiguous"}
    # spot-check one specific entry rather than just counting
    q1 = next(q for q in queries if q.query_id == "q_001")
    assert q1.relevant_chunk_ids == {"09450365c3b1564a_chunk_000"}


def make_fake_queries():
    return [
        EvalQuery(query_id="q1", query="find a", category="lexical", relevant_chunk_ids={"a"}),
        EvalQuery(query_id="q2", query="find b", category="lexical", relevant_chunk_ids={"b"}),
        EvalQuery(query_id="q3", query="find c", category="semantic", relevant_chunk_ids={"c"}),
    ]


def test_run_evaluation_perfect_retrieval_gives_perfect_scores():
    def perfect_retrieval(query: str) -> list[str]:
        return {"find a": ["a", "x"], "find b": ["b", "x"], "find c": ["c", "x"]}[query]

    results = run_evaluation(make_fake_queries(), perfect_retrieval, k=5)
    agg = aggregate_results(results)

    assert agg["overall"]["recall_at_k"] == 1.0
    assert agg["overall"]["mrr"] == 1.0
    assert agg["overall"]["num_queries"] == 3


def test_run_evaluation_no_matches_gives_zero_scores():
    def useless_retrieval(query: str) -> list[str]:
        return ["irrelevant_1", "irrelevant_2"]

    results = run_evaluation(make_fake_queries(), useless_retrieval, k=5)
    agg = aggregate_results(results)

    assert agg["overall"]["recall_at_k"] == 0.0
    assert agg["overall"]["mrr"] == 0.0


def test_aggregate_results_slices_by_category_correctly():
    # lexical queries retrieve perfectly, semantic query retrieves nothing —
    # this is the case the category breakdown exists to catch, since the
    # overall average alone would obscure it.
    def mixed_retrieval(query: str) -> list[str]:
        return {"find a": ["a"], "find b": ["b"], "find c": ["irrelevant"]}[query]

    results = run_evaluation(make_fake_queries(), mixed_retrieval, k=5)
    agg = aggregate_results(results)

    assert agg["by_category"]["lexical"]["recall_at_k"] == 1.0
    assert agg["by_category"]["lexical"]["num_queries"] == 2
    assert agg["by_category"]["semantic"]["recall_at_k"] == 0.0
    assert agg["by_category"]["semantic"]["num_queries"] == 1
    # overall should be the average across all 3, not equal to either category
    assert agg["overall"]["recall_at_k"] == 2 / 3


def test_aggregate_results_on_empty_list_does_not_crash():
    agg = aggregate_results([])
    assert agg["overall"]["num_queries"] == 0
    assert agg["overall"]["recall_at_k"] == 0.0
    assert agg["by_category"] == {}
