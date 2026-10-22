"""
app/generation/validator.py

Evidence validation: the LLM self-reports cited_sources and
sufficient_evidence in generator.py, but self-reporting isn't verification
— a model can name [Source 7] when only 3 sources were retrieved, or claim
sufficient_evidence=true while citing nothing real. This module checks the
self-report against what was actually retrieved, rather than trusting it.

sufficient_evidence is fully DERIVED from validated citations, not merely
downgraded from the model's self-report. Originally this only forced
True->False when every citation was fake (guarding against confident
hallucination). Real-world testing against a small local model
(llama3.2:latest) surfaced the opposite failure just as often: the model
would correctly cite a genuinely valid source, then separately — and
inconsistently — report sufficient_evidence=false anyway. Prompt
instructions telling the model to keep the two fields consistent did not
reliably fix this (see generator.py's SYSTEM_PROMPT), because it's asking
a small model to enforce a joint constraint across two fields in one
generation, which these models frequently fail regardless of how the
instruction is worded.

The fix: treat "does at least one valid citation exist" as the ONE
ground-truth signal, since that's the only part of the model's output we
can actually verify against real data. The model's own sufficient_evidence
boolean is no longer trusted in either direction — a valid citation always
implies sufficient evidence, and no valid citation always implies
insufficient evidence, regardless of what the model separately claimed.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.generation.generator import GenerationResult


@dataclass
class ValidatedGeneration:
    answer: str
    cited_sources: list[int]  # filtered to only sources that actually exist
    invalid_citations: list[int]  # source numbers the model cited that don't exist — a hallucination signal worth logging/measuring, not just discarding
    sufficient_evidence: bool
    raw_response: str


def validate_generation(result: GenerationResult, num_sources: int) -> ValidatedGeneration:
    valid = [s for s in result.cited_sources if 1 <= s <= num_sources]
    invalid = [s for s in result.cited_sources if not (1 <= s <= num_sources)]

    # Derived, not cross-checked: a valid citation is the ground truth for
    # "sufficient evidence exists," regardless of what the model's own
    # sufficient_evidence field separately claimed. See module docstring —
    # this direction (overriding a false-negative False) is the fix for a
    # real, observed failure mode, not just the pre-existing hallucination
    # guard (which only handled the false-positive True direction).
    sufficient_evidence = len(valid) > 0

    return ValidatedGeneration(
        answer=result.answer,
        cited_sources=valid,
        invalid_citations=invalid,
        sufficient_evidence=sufficient_evidence,
        raw_response=result.raw_response,
    )
