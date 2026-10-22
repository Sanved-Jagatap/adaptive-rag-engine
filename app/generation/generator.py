"""
app/generation/generator.py

Phase 4 scope: structured, citation-aware generation. Instead of a plain
answer string, the LLM returns JSON naming which source numbers it
actually used — this is what evidence validation (next step) checks
against, and what surfaces a wrong/hallucinated citation instead of
silently trusting it.

The generation result also preserves Ollama's native usage/timing metadata
so evaluation code can measure token usage and latency without making a
second generation request.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.core.ollama_client import OllamaClient
from app.retrieval.types import RetrievedChunk

_log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a helpful assistant that answers questions using
ONLY the provided context. If the context does not contain enough
information to answer confidently, say so explicitly rather than guessing
or relying on outside knowledge.

Respond ONLY with JSON, no preamble, no markdown fences:
{"answer": "...", "cited_sources": [1, 3], "sufficient_evidence": true}

CITATION REQUIREMENT — IMPORTANT:

If the context contains enough information to answer the question,
you MUST cite at least one source.

Every factual answer MUST include the source number that supports it.

Before producing the JSON, perform this check internally:

1. Determine whether the context contains enough information to answer.
2. Identify which [Source N] contains the supporting evidence.
3. Put every supporting source number in "cited_sources".
4. Set "sufficient_evidence" to true only when at least one valid
   supporting source has been identified.

Never return:
"sufficient_evidence": true
with:
"cited_sources": []

If the context supports the answer, do NOT omit the citation.

If the context does not support the answer:
- "sufficient_evidence" must be false.
- "cited_sources" must be [].
- Explain briefly that the available context does not contain enough
  information.

The two fields must never contradict each other:
- If cited_sources is non-empty, sufficient_evidence MUST be true.
- If sufficient_evidence is false, cited_sources MUST be empty.

CITATION BOUNDARY ? CRITICAL:

The only valid source numbers are the [Source N] labels that actually
appear in the Context provided to you.

The context is numbered sequentially starting at [Source 1].

You MUST NOT invent, guess, or extrapolate a source number.

For example, if the context contains:

[Source 1]
...
[Source 2]
...
[Source 3]
...
[Source 4]
...
[Source 5]
...

then the ONLY valid citation numbers are:

[1], [2], [3], [4], [5]

A citation such as [6], [7], [99], or any other number not present in
the provided context is INVALID and MUST NOT be returned.

Before writing "cited_sources", verify every citation number against the
actual [Source N] labels in the context.

If only one source supports the answer, cite only that source.

If multiple sources support different parts of the answer, cite the
corresponding valid source numbers.

Never cite a source merely because it is related to the topic.

sufficient_evidence and cited_sources must be actual JSON types:
a real boolean and a real array, never quoted as strings.

SEMANTIC / CONCEPTUAL ANSWERING — IMPORTANT:

For "why", "how", "explain", "what is the purpose of", "what does this
mean", and similar conceptual questions, do NOT require the context to
use the exact words from the question.

If a retrieved source directly explains the underlying concept, reason,
principle, relationship, trade-off, or purpose being asked about, treat
that explanation as sufficient evidence.

A semantic question can be answered when the context explains the idea
even if the question uses different wording.

For example, if the question asks why multiple security controls should
be evaluated together, and a source explains that no single mechanism
provides complete protection and that authentication, authorization,
input validation, secret protection, least privilege, and security
monitoring provide complementary protections, that source is sufficient
evidence.

In that situation:
- Do NOT abstain merely because the source does not repeat the exact
  wording of the question.
- Answer the conceptual question using the explanation in the source.
- Cite the source containing that explanation.
- Set "sufficient_evidence" to true.

Only abstain from a semantic question when the retrieved context does
not actually provide the underlying explanation needed to answer it.

For semantic or conceptual questions, cite the source containing the
explanation, not merely a source containing a related keyword.

For example:

Question:
Why can caching reduce database load?

If Source 1 explains that cached responses can serve repeated requests
without repeatedly querying the database, the response MUST be:

{
  "answer": "Caching can reduce database load because cached responses
  can serve repeated requests without querying the database each time.",
  "cited_sources": [1],
  "sufficient_evidence": true
}

For multi-part questions, every distinct requested item must be answered.
Do not answer only one part of a question when the context contains
evidence for multiple parts.

Before producing the answer, identify each distinct item requested by
the question and check whether the provided context supports each one.

If all requested items are supported:
- Answer every item explicitly.
- Include the relevant configuration/entity name for each item when
  applicable.
- Cite the source number supporting each item.
- Keep all requested items in the same "answer".

For example, if the question asks for both a retry limit and an access
token lifetime, and the context supports both, the answer must contain
both values:
"MAX_RETRY_LIMIT defaults to 3 retries. ACCESS_TOKEN_TTL_SECONDS defaults
to 900 seconds (15 minutes)."
with:
"cited_sources": [1, 2]

Do not omit a supported part merely because another part is easier to
answer.

If one or more requested items are not supported by the context, do not
guess the missing item. State which information cannot be determined and
leave sufficient_evidence false with cited_sources empty.

When the answer is a configuration value, don't return a bare number —
include the configuration name, the value, and its unit or
human-readable equivalent when the context supports one:

BAD:
"900"

GOOD:
"ACCESS_TOKEN_TTL_SECONDS defaults to 900 seconds (15 minutes)."

BAD:
"3"

GOOD:
"MAX_RETRY_LIMIT defaults to 3 retries."

Do not invent units, conversions, configuration names, or human-readable
equivalents that are not supported by the provided context — only
restate what the context itself says.

FINAL CHECK BEFORE JSON:

If you wrote an answer containing information from Source 1, Source 1
must appear in cited_sources.

If you wrote an answer containing information from Source 2, Source 2
must appear in cited_sources.

If you cannot identify a supporting source, do not claim sufficient
evidence.
"""


@dataclass
class GenerationResult:
    answer: str
    cited_sources: list[int]
    sufficient_evidence: bool
    raw_response: str

    # Ollama usage/timing metadata.
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_duration_ns: int | None = None
    load_duration_ns: int | None = None
    eval_duration_ns: int | None = None


def build_prompt(
    query: str,
    retrieved: list[RetrievedChunk],
) -> list[dict]:

    context_blocks = "\n\n".join(
        f"[Source {i+1}] {r.chunk.text}"
        for i, r in enumerate(retrieved)
    )

    user_content = (
        f"Context:\n{context_blocks}\n\n"
        f"Question: {query}\n\n"
        "Answer using only the context above."
    )

    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_content,
        },
    ]


def _coerce_bool(value) -> bool:
    """Defensive conversion for boolean values returned by the LLM."""

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() == "true"

    return bool(value)


def _coerce_citations(value) -> list[int]:
    """Normalize citation values returned by the LLM.

    Accepts:

        1
        "1"
        "Source 1"
        "source 1"

    Invalid citation values are ignored here and are still subject
    to normal evidence validation later.
    """

    if not isinstance(value, list):
        return []

    citations: list[int] = []

    for item in value:

        if isinstance(item, bool):
            continue

        if isinstance(item, int):
            citations.append(item)
            continue

        if isinstance(item, str):

            cleaned = item.strip()

            if cleaned.lower().startswith("source "):
                cleaned = cleaned[7:].strip()

            try:
                citations.append(int(cleaned))
            except ValueError:
                continue

    return citations


def _normalize_malformed_citations(raw: str) -> str:
    """Normalize citation syntax that small local LLMs sometimes emit.

    The expected JSON is:

        "cited_sources": [1, 2]

    Some models instead produce:

        "cited_sources": [Source 1, Source 2]

    That is not valid JSON. Convert only this specific citation field
    into a valid JSON integer array before json.loads().

    This does not decide whether citations are valid evidence. That
    remains the responsibility of validate_generation().
    """

    pattern = (
        r'("cited_sources"\s*:\s*)'
        r'\[\s*'
        r'((?:Source\s+\d+\s*,?\s*)*)'
        r'\]'
    )

    def replace(match: re.Match) -> str:

        prefix = match.group(1)
        citation_text = match.group(2)

        numbers = re.findall(
            r"Source\s+(\d+)",
            citation_text,
            flags=re.IGNORECASE,
        )

        return (
            prefix
            + "["
            + ", ".join(numbers)
            + "]"
        )

    return re.sub(
        pattern,
        replace,
        raw,
        flags=re.IGNORECASE,
    )


def _parse_response(raw: str) -> GenerationResult:
    """Parse the model's structured JSON response.

    The parser accepts both valid JSON citations and the specific
    malformed citation syntax occasionally produced by local models.

    Falls back to a safe, honest default on other parse failures.
    """

    try:

        cleaned = (
            raw.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )

        # Small local models sometimes return:
        #
        #     "cited_sources": [Source 1]
        #
        # instead of valid JSON:
        #
        #     "cited_sources": [1]
        #
        # Normalize that specific field before JSON parsing.
        cleaned = _normalize_malformed_citations(
            cleaned
        )

        data = json.loads(cleaned)

        return GenerationResult(
            answer=str(
                data.get(
                    "answer",
                    "",
                )
            ),

            cited_sources=_coerce_citations(
                data.get(
                    "cited_sources",
                    [],
                )
            ),

            sufficient_evidence=_coerce_bool(
                data.get(
                    "sufficient_evidence",
                    False,
                )
            ),

            raw_response=raw,
        )

    except (
        json.JSONDecodeError,
        ValueError,
        TypeError,
    ):

        return GenerationResult(
            answer=(
                "I wasn't able to generate a reliably structured "
                "answer for this query."
            ),

            cited_sources=[],

            sufficient_evidence=False,

            raw_response=raw,
        )


async def generate_answer(
    query: str,
    retrieved: list[RetrievedChunk],
    client: OllamaClient,
) -> GenerationResult:
    """Generate a structured answer using the retrieved context.

    Only one Ollama request is made.

    The returned GenerationResult contains both the parsed answer and
    Ollama's native usage/timing metadata. This allows the evaluation
    harness to record token counts and latency without issuing a second
    generation request.
    """

    if not retrieved:

        return GenerationResult(
            answer=(
                "I don't have enough context to answer that — "
                "no relevant chunks were retrieved."
            ),

            cited_sources=[],

            sufficient_evidence=False,

            raw_response="",
        )

    messages = build_prompt(
        query,
        retrieved,
    )

    # One Ollama call.
    chat_result = await client.chat_with_usage(
        messages
    )

    raw = chat_result.content

    _log.debug(
        "raw ollama generation response: %r",
        raw,
    )

    result = _parse_response(
        raw
    )

    # Preserve Ollama's native usage/timing metadata.

    result.prompt_tokens = (
        chat_result.prompt_tokens
    )

    result.completion_tokens = (
        chat_result.completion_tokens
    )

    result.total_duration_ns = (
        chat_result.total_duration_ns
    )

    result.load_duration_ns = (
        chat_result.load_duration_ns
    )

    result.eval_duration_ns = (
        chat_result.eval_duration_ns
    )

    return result