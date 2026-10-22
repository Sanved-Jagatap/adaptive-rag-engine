"""
app/evaluation/faithfulness.py

Faithfulness/relevance scoring via LLM-as-judge. This is a genuinely
different check than validator.py's evidence validation: validator.py
checks that a cited source NUMBER actually exists among retrieved chunks
(structural). This checks that the answer's actual CLAIMS are supported by
that source's TEXT (semantic) — a citation can be structurally valid
(source 1 exists) while the answer still says something source 1 doesn't
support. Only a judge that reads both the answer and the source text can
catch that.

Faithfulness: are the answer's factual claims supported by the cited
source text, with nothing drawn from outside it?
Relevance: does the answer actually address the question asked?

Both scored 0.0-1.0 by the judge model, not computed algorithmically —
these are inherently semantic judgments. As with the router's LLM
fallback, malformed judge output degrades to a safe default rather than
crashing evaluation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.core.ollama_client import OllamaClient

JUDGE_SYSTEM_PROMPT = """You are evaluating whether an AI-generated answer
is faithful to its cited sources and relevant to the question asked.

Faithful means every factual claim in the answer is directly supported by
the provided source text — no unsupported claims, nothing drawn from
outside the given sources.

Relevant means the answer actually addresses the question asked, not just
tangentially related information.

Respond ONLY with JSON, no preamble, no markdown fences:
{"faithfulness": 0.0-1.0, "relevance": 0.0-1.0, "reasoning": "one sentence explaining the scores"}"""


@dataclass
class JudgeResult:
    faithfulness: float
    relevance: float
    reasoning: str
    raw_response: str
    skipped: bool = False  # True when judging was skipped (e.g. no cited sources)


def build_judge_prompt(query: str, answer: str, cited_source_texts: list[str]) -> list[dict]:
    sources_block = "\n\n".join(f"[Source {i+1}] {text}" for i, text in enumerate(cited_source_texts))
    user_content = (
        f"Question: {query}\n\n"
        f"Cited sources:\n{sources_block}\n\n"
        f"Answer to evaluate: {answer}"
    )
    return [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _parse_judge_response(raw: str) -> JudgeResult:
    """Falls back to 0.0/0.0 (not a neutral middle value) on parse failure —
    an unparseable judge response shouldn't be silently treated as an
    average-quality answer; it should look bad enough in aggregate results
    to be noticed and investigated, not blended in unnoticed."""
    try:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(cleaned)
        return JudgeResult(
            faithfulness=float(data.get("faithfulness", 0.0)),
            relevance=float(data.get("relevance", 0.0)),
            reasoning=str(data.get("reasoning", "")),
            raw_response=raw,
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        return JudgeResult(
            faithfulness=0.0,
            relevance=0.0,
            reasoning="Judge response could not be parsed.",
            raw_response=raw,
        )


async def judge_faithfulness(
    query: str, answer: str, cited_source_texts: list[str], client: OllamaClient
) -> JudgeResult:
    if not cited_source_texts:
        # Nothing was cited — typically an insufficient-evidence abstention.
        # Trivially faithful (no claims made that could be unsupported),
        # but not meaningfully scorable for relevance without a source to
        # judge against. Skip the LLM call rather than ask it to judge
        # something with no grounding to check.
        return JudgeResult(
            faithfulness=1.0,
            relevance=0.0,
            reasoning="No cited sources — skipped judging (likely an abstention answer).",
            raw_response="",
            skipped=True,
        )

    messages = build_judge_prompt(query, answer, cited_source_texts)
    raw = await client.chat(messages)
    return _parse_judge_response(raw)
