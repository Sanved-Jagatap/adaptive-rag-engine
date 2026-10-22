"""
app/generation/finalize.py

Ensures the final answer text and sufficient_evidence flag can never
disagree. Without this, a downgrade in validator.py (e.g. all citations
turned out to be hallucinated) would flip sufficient_evidence to False
while leaving the LLM's original, possibly confident-sounding answer text
untouched — a client reading just the answer field would see something
that contradicts the flag right next to it.
"""

from __future__ import annotations

from app.generation.validator import ValidatedGeneration

INSUFFICIENT_EVIDENCE_MESSAGE = (
    "I don't have enough reliable information in the retrieved context to "
    "answer this confidently."
)


def finalize_answer(validated: ValidatedGeneration) -> str:
    if not validated.sufficient_evidence:
        return INSUFFICIENT_EVIDENCE_MESSAGE
    return validated.answer
