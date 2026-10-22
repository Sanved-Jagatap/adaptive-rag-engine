from app.generation.generator import GenerationResult
from app.generation.validator import validate_generation


def test_valid_citations_pass_through_unchanged():
    result = GenerationResult(
        answer="It's 3.", cited_sources=[1, 2], sufficient_evidence=True, raw_response=""
    )
    validated = validate_generation(result, num_sources=3)

    assert validated.cited_sources == [1, 2]
    assert validated.invalid_citations == []
    assert validated.sufficient_evidence is True


def test_out_of_range_citation_is_flagged_as_invalid():
    result = GenerationResult(
        answer="It's 3.", cited_sources=[1, 7], sufficient_evidence=True, raw_response=""
    )
    validated = validate_generation(result, num_sources=3)

    assert validated.cited_sources == [1]
    assert validated.invalid_citations == [7]
    # Still has one valid citation, so the confident claim stands.
    assert validated.sufficient_evidence is True


def test_zero_citation_source_is_invalid_since_sources_are_1_indexed():
    result = GenerationResult(
        answer="answer", cited_sources=[0], sufficient_evidence=True, raw_response=""
    )
    validated = validate_generation(result, num_sources=3)

    assert validated.cited_sources == []
    assert validated.invalid_citations == [0]


def test_sufficient_evidence_downgraded_when_all_citations_are_hallucinated():
    result = GenerationResult(
        answer="Confidently wrong.", cited_sources=[9, 10], sufficient_evidence=True, raw_response=""
    )
    validated = validate_generation(result, num_sources=3)

    assert validated.cited_sources == []
    assert validated.invalid_citations == [9, 10]
    # This is the core case this module exists for: don't let a confident
    # claim through when nothing it cited actually exists.
    assert validated.sufficient_evidence is False


def test_sufficient_evidence_false_with_no_citations_stays_false():
    result = GenerationResult(
        answer="Not enough info.", cited_sources=[], sufficient_evidence=False, raw_response=""
    )
    validated = validate_generation(result, num_sources=3)
    assert validated.sufficient_evidence is False


def test_model_false_negative_overridden_when_a_valid_citation_exists():
    # The real bug this fix addresses: llama3.2 correctly cited a genuinely
    # valid source, but separately (and inconsistently) reported
    # sufficient_evidence=false anyway. sufficient_evidence is derived from
    # citation validity, not the model's separate self-report, so a valid
    # citation always overrides a false claim of insufficiency.
    result = GenerationResult(
        answer="I don't have enough reliable information to answer this confidently.",
        cited_sources=[1],
        sufficient_evidence=False,
        raw_response="",
    )
    validated = validate_generation(result, num_sources=3)
    assert validated.cited_sources == [1]
    assert validated.sufficient_evidence is True


def test_no_sources_retrieved_at_all():
    result = GenerationResult(
        answer="No context.", cited_sources=[], sufficient_evidence=False, raw_response=""
    )
    validated = validate_generation(result, num_sources=0)
    assert validated.cited_sources == []
    assert validated.sufficient_evidence is False
