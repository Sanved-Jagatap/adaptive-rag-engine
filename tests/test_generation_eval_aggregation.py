from app.evaluation.runner import GenerationEvalResult, aggregate_generation_results


def make_result(**overrides) -> GenerationEvalResult:
    defaults = dict(
        query_id="q1",
        category="lexical",
        sufficient_evidence=True,
        confidence_level="high",
        faithfulness=0.9,
        relevance=0.9,
        judge_skipped=False,
        prompt_tokens=100,
        completion_tokens=20,
        routing_ms=1.0,
        retrieval_ms=5.0,
        rerank_ms=2.0,
        generation_ms=50.0,
        judge_ms=30.0,
        total_ms=88.0,
    )
    defaults.update(overrides)
    return GenerationEvalResult(**defaults)


def test_aggregate_averages_faithfulness_and_relevance():
    results = [make_result(faithfulness=1.0, relevance=1.0), make_result(faithfulness=0.5, relevance=0.5)]
    agg = aggregate_generation_results(results)
    assert agg["overall"]["avg_faithfulness"] == 0.75
    assert agg["overall"]["avg_relevance"] == 0.75
    assert agg["overall"]["num_judged"] == 2


def test_skipped_judgments_excluded_from_faithfulness_average():
    # One real judgment (0.5) and one skipped (abstention, faithfulness=1.0
    # by convention but should NOT count toward the average).
    results = [
        make_result(faithfulness=0.5, relevance=0.5, judge_skipped=False),
        make_result(faithfulness=1.0, relevance=0.0, judge_skipped=True, sufficient_evidence=False),
    ]
    agg = aggregate_generation_results(results)
    assert agg["overall"]["avg_faithfulness"] == 0.5
    assert agg["overall"]["num_judged"] == 1


def test_sufficient_evidence_rate_computed_correctly():
    results = [
        make_result(sufficient_evidence=True),
        make_result(sufficient_evidence=True),
        make_result(sufficient_evidence=False, judge_skipped=True),
    ]
    agg = aggregate_generation_results(results)
    assert agg["overall"]["sufficient_evidence_rate"] == 2 / 3


def test_none_token_counts_are_excluded_not_treated_as_zero():
    results = [make_result(prompt_tokens=100), make_result(prompt_tokens=None)]
    agg = aggregate_generation_results(results)
    # Should average only the present value (100), not (100 + 0) / 2 = 50.
    assert agg["overall"]["avg_prompt_tokens"] == 100.0


def test_all_none_token_counts_returns_none_not_zero():
    results = [make_result(prompt_tokens=None), make_result(prompt_tokens=None)]
    agg = aggregate_generation_results(results)
    assert agg["overall"]["avg_prompt_tokens"] is None


def test_by_category_breakdown():
    results = [
        make_result(category="lexical", faithfulness=1.0),
        make_result(category="semantic", faithfulness=0.0),
    ]
    agg = aggregate_generation_results(results)
    assert agg["by_category"]["lexical"]["avg_faithfulness"] == 1.0
    assert agg["by_category"]["semantic"]["avg_faithfulness"] == 0.0


def test_empty_results_does_not_crash():
    agg = aggregate_generation_results([])
    assert agg["overall"]["num_queries"] == 0
    assert agg["overall"]["avg_faithfulness"] == 0.0
    assert agg["overall"]["avg_prompt_tokens"] is None
    assert agg["by_category"] == {}
