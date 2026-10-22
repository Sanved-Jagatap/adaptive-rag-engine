from app.evaluation.metrics import (
    mean_reciprocal_rank,
    precision_at_k,
    reciprocal_rank,
    recall_at_k,
)


def test_recall_at_k_full_hit():
    retrieved = ["a", "b", "c"]
    relevant = {"a", "b"}
    assert recall_at_k(retrieved, relevant, k=3) == 1.0


def test_recall_at_k_partial_hit():
    retrieved = ["a", "x", "y"]
    relevant = {"a", "b"}
    assert recall_at_k(retrieved, relevant, k=3) == 0.5


def test_recall_at_k_respects_k_cutoff():
    # relevant chunk is ranked #3, but k=2 shouldn't see it.
    retrieved = ["x", "y", "a"]
    relevant = {"a"}
    assert recall_at_k(retrieved, relevant, k=2) == 0.0
    assert recall_at_k(retrieved, relevant, k=3) == 1.0


def test_recall_at_k_empty_relevant_set_returns_zero_not_vacuous_one():
    assert recall_at_k(["a", "b"], set(), k=5) == 0.0


def test_precision_at_k_basic():
    retrieved = ["a", "x", "y"]
    relevant = {"a", "b"}
    # 1 of top-3 retrieved is relevant
    assert precision_at_k(retrieved, relevant, k=3) == 1 / 3


def test_precision_at_k_empty_retrieved_returns_zero():
    assert precision_at_k([], {"a"}, k=5) == 0.0


def test_reciprocal_rank_first_position():
    assert reciprocal_rank(["a", "x", "y"], {"a"}) == 1.0


def test_reciprocal_rank_third_position():
    assert reciprocal_rank(["x", "y", "a"], {"a"}) == 1 / 3


def test_reciprocal_rank_no_match_returns_zero():
    assert reciprocal_rank(["x", "y"], {"a"}) == 0.0


def test_mean_reciprocal_rank_averages_correctly():
    assert mean_reciprocal_rank([1.0, 0.5, 0.0]) == 0.5


def test_mean_reciprocal_rank_empty_list_returns_zero():
    assert mean_reciprocal_rank([]) == 0.0
