from app.generation.finalize import INSUFFICIENT_EVIDENCE_MESSAGE, finalize_answer
from app.generation.validator import ValidatedGeneration


def test_sufficient_evidence_true_passes_answer_through_unchanged():
    validated = ValidatedGeneration(
        answer="It's 3.", cited_sources=[1], invalid_citations=[], sufficient_evidence=True, raw_response=""
    )
    assert finalize_answer(validated) == "It's 3."


def test_sufficient_evidence_false_overrides_whatever_answer_text_was():
    # Even though the LLM's original answer text sounds confident, the
    # final answer must be the standardized message once sufficient_evidence
    # is False — this is exactly the inconsistency this module prevents.
    validated = ValidatedGeneration(
        answer="It's definitely 3, no doubt about it.",
        cited_sources=[],
        invalid_citations=[9],
        sufficient_evidence=False,
        raw_response="",
    )
    assert finalize_answer(validated) == INSUFFICIENT_EVIDENCE_MESSAGE
