"""
app/routing/query_router.py

Query routing logic for the Adaptive RAG Engine.

Design: two-tier router.
  1. Rule-based fast path — cheap regex/keyword signal extraction, scores the
     query toward "lexical" (BM25) or "semantic" (vector) evidence, and
     decides confidently when the signal is strong. No LLM call, ~microseconds.
  2. LLM fallback — only triggered when the rule-based signal is ambiguous
     (scores close together, or query is short/vague). Uses a small,
     structured-output call to classify strategy AND optionally rewrite the
     query. This keeps latency and cost low for the common case while still
     handling genuinely ambiguous queries well.

Output matches the RetrievalPlan shape from the README:
    {"strategy": "hybrid", "top_k": 10, "rerank": true, "query_rewrite": true}
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from app.core.config import settings


class Strategy(str, Enum):
    VECTOR = "vector"
    BM25 = "bm25"
    HYBRID = "hybrid"


@dataclass
class RetrievalPlan:
    strategy: Strategy
    top_k: int
    rerank: bool
    query_rewrite: bool
    rewritten_query: Optional[str] = None
    # Debug/eval fields — keep these; they're what let you audit routing
    # decisions later when you're building the evaluation dataset.
    lexical_score: float = 0.0
    semantic_score: float = 0.0
    decided_by: str = "rule"  # "rule" | "llm_fallback"

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy.value,
            "top_k": self.top_k,
            "rerank": self.rerank,
            "query_rewrite": self.query_rewrite,
            "rewritten_query": self.rewritten_query,
        }


# ---------------------------------------------------------------------------
# 1. Signal extraction
# ---------------------------------------------------------------------------

# Patterns that strongly suggest the user wants an EXACT match, not a
# conceptual one — these are classic BM25 wins where embeddings blur things
# a keyword index wouldn't.
LEXICAL_PATTERNS = {
    "quoted_phrase": re.compile(r'"[^"]{2,}"|\'[^\']{2,}\''),
    "identifier_like": re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\b"),  # e.g. payment.retry_limit
    "snake_or_camel": re.compile(r"\b([a-z]+_[a-z_]+|[a-z]+[A-Z][a-zA-Z]*)\b"),
    "version_or_code": re.compile(r"\b([A-Z]{2,}-\d+|v?\d+\.\d+(\.\d+)?|0x[0-9a-fA-F]+)\b"),
    "config_key": re.compile(r"\b[A-Z][A-Z0-9_]{3,}\b"),  # e.g. MAX_RETRY_LIMIT
    "file_path": re.compile(r"\b[\w/\\]+\.(py|json|yaml|yml|env|ts|js|md|toml)\b"),
}

# Words that suggest a conceptual/explanatory question — classic vector wins.
SEMANTIC_KEYWORDS = {
    "why", "how", "explain", "compare", "difference between", "overview",
    "summarize", "summarise", "what is the purpose", "rationale", "reason",
    "pros and cons", "trade-off", "tradeoff", "best practice", "recommend",
}

# Signals that the query is too short/vague to route confidently and would
# benefit from rewriting before retrieval.
AMBIGUITY_SIGNALS = {
    "pronoun_only": re.compile(r"^\s*(it|that|this|they|those)\b", re.IGNORECASE),
}


@dataclass
class QueryFeatures:
    lexical_hits: list[str] = field(default_factory=list)
    semantic_hits: list[str] = field(default_factory=list)
    is_short: bool = False
    is_pronoun_led: bool = False

    @property
    def lexical_score(self) -> float:
        # Simple weighted count — tune weights once you have eval data.
        return min(1.0, 0.3 * len(self.lexical_hits))

    @property
    def semantic_score(self) -> float:
        return min(1.0, 0.35 * len(self.semantic_hits))


def extract_features(query: str) -> QueryFeatures:
    lexical_hits = [name for name, pat in LEXICAL_PATTERNS.items() if pat.search(query)]
    lowered = query.lower()
    semantic_hits = [kw for kw in SEMANTIC_KEYWORDS if kw in lowered]
    words = query.strip().split()
    return QueryFeatures(
        lexical_hits=lexical_hits,
        semantic_hits=semantic_hits,
        is_short=len(words) <= 3,
        is_pronoun_led=bool(AMBIGUITY_SIGNALS["pronoun_only"].match(query)),
    )


# ---------------------------------------------------------------------------
# 2. Rule-based router
# ---------------------------------------------------------------------------

# Thresholds below are starting points. Once Phase 5 (evaluation) is up,
# sweep these against your eval set and log (features -> chosen strategy ->
# Recall@5/MRR) so the thresholds are tuned on evidence, not guesswork.
CONFIDENT_MARGIN = 0.25  # min gap between lexical/semantic score to trust the rule path
MIN_CONFIDENCE = 0.3     # below this on both axes, treat as ambiguous


def route_rule_based(query: str) -> tuple[Optional[RetrievalPlan], QueryFeatures]:
    """Returns a RetrievalPlan if the rule path is confident, else None
    (meaning: fall back to the LLM router)."""
    feats = extract_features(query)

    if feats.is_pronoun_led or (feats.is_short and not feats.lexical_hits):
        return None, feats  # too ambiguous to trust heuristics

    lex, sem = feats.lexical_score, feats.semantic_score

    if max(lex, sem) < MIN_CONFIDENCE:
        return None, feats  # neither signal fired meaningfully

    if abs(lex - sem) < CONFIDENT_MARGIN:
        strategy = Strategy.HYBRID
    elif lex > sem:
        strategy = Strategy.BM25
    else:
        strategy = Strategy.VECTOR

    plan = RetrievalPlan(
        strategy=strategy,
        top_k=10 if strategy == Strategy.HYBRID else 8,
        rerank=strategy != Strategy.VECTOR or sem < 0.7,  # rerank unless very confidently semantic
        query_rewrite=False,
        lexical_score=lex,
        semantic_score=sem,
        decided_by="rule",
    )
    return plan, feats


# ---------------------------------------------------------------------------
# 3. LLM fallback router (used only when rule path is unsure)
# ---------------------------------------------------------------------------

LLM_ROUTER_SYSTEM_PROMPT = """You are a retrieval strategy router for a RAG system.
Given a user query, decide:
- strategy: one of "vector", "bm25", "hybrid"
  - "bm25" for queries about exact identifiers, config keys, error codes, file names
  - "vector" for conceptual, explanatory, "why/how" style questions
  - "hybrid" when the query mixes both, or you are unsure
- rewrite: a clearer, retrieval-friendly rephrasing of the query if the
  original is ambiguous, pronoun-led, or underspecified. If no rewrite is
  needed, set rewrite to null.

When recent conversation context is provided, use it to resolve
contextual references — words like "it", "that", "this", "those", "the
setting", "the value", "the limit", and similar wording that only make
sense given what was just discussed:
- If the query depends on the previous turn, make the referenced entity
  explicit in the rewrite (e.g. "that setting" -> the actual config name
  from context).
- Preserve the user's actual intent — do not add unrelated facts from
  context that the query didn't ask about.
- Do not answer the question inside the rewrite; the rewrite is a
  clearer question, not an answer.
- If the query is already specific and unambiguous, rewrite=null.
- If the provided context is insufficient to confidently resolve an
  ambiguous reference, rewrite=null rather than guessing at an entity —
  a wrong guess is worse than leaving the query as-is.

Example:
Context:
User: What does ACCESS_TOKEN_TTL_SECONDS default to?
Assistant: The default access token lifetime is 15 minutes.
Query: What's the default for that setting?
Rewrite: What is the default value of ACCESS_TOKEN_TTL_SECONDS?

Respond ONLY with JSON, no preamble, no markdown fences:
{"strategy": "...", "rewrite": "..." | null, "rerank": true|false}
"""


def build_llm_router_messages(query: str, recent_context: str = "") -> list[dict]:
    """Caller wires this into whatever LLM client the app uses (Ollama, etc).
    recent_context is optional — e.g. last user/assistant turn, useful for
    resolving pronoun-led queries like 'What controls that?'"""
    user_content = query if not recent_context else (
        f"Recent conversation context:\n{recent_context}\n\nQuery: {query}"
    )
    return [
        {"role": "system", "content": LLM_ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def parse_llm_router_response(raw: str, feats: QueryFeatures) -> RetrievalPlan:
    """Parse the LLM's JSON response into a RetrievalPlan. Falls back to
    hybrid + rerank on any parse failure — never let a malformed LLM
    response crash retrieval."""
    try:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(cleaned)
        strategy = Strategy(data.get("strategy", "hybrid"))
        rewrite = data.get("rewrite")
        rerank = bool(data.get("rerank", True))
    except (json.JSONDecodeError, ValueError):
        strategy, rewrite, rerank = Strategy.HYBRID, None, True

    return RetrievalPlan(
        strategy=strategy,
        top_k=10,
        rerank=rerank,
        query_rewrite=rewrite is not None,
        rewritten_query=rewrite,
        lexical_score=feats.lexical_score,
        semantic_score=feats.semantic_score,
        decided_by="llm_fallback",
    )


# ---------------------------------------------------------------------------
# 4. Ollama client (default llm_call_fn implementation)
# ---------------------------------------------------------------------------

class OllamaRouterClient:
    """Thin wrapper around Ollama's /api/chat endpoint, shaped to match the
    llm_call_fn signature route_query expects: callable(messages) -> str.
    temperature=0 because routing decisions should be deterministic given
    the same query — you don't want strategy selection to be a source of
    noise in your Recall@K comparisons.
    """

    def __init__(
        self,
        model: str | None = None,
        host: str | None = None,
        timeout: float | None = None,
    ):
        # Defaults come from app settings, not hardcoded values — this was
        # a real bug: a hardcoded "llama3.1"/localhost silently diverged
        # from whatever model/host the rest of the app was actually
        # configured to use (e.g. a different model name, or Ollama
        # reachable via host.docker.internal rather than localhost).
        self.model = model or settings.ollama_model
        self.host = (host or settings.ollama_host).rstrip("/")
        self.timeout = timeout or settings.ollama_timeout_seconds

    def __call__(self, messages: list[dict]) -> str:
        import requests  # local import: keeps the module importable without

        resp = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


# ---------------------------------------------------------------------------
# 5. Routing logger — feeds the Phase 5 evaluation pipeline
# ---------------------------------------------------------------------------

class RoutingLogger:
    """Appends every routing decision to a JSONL file. Schema is flat so it
    loads straight into pandas and joins cleanly against Recall@K results
    keyed by query.

    The point of logging EVERY decision (not just rewrites) is to get a
    control group for free: once the eval dataset exists, group by
    `was_rewritten` and compare Recall@5/MRR between the raw-query rows and
    the rewritten-query rows. That's the actual answer to "does query
    rewriting help," rather than assuming it does.
    """

    def __init__(self, log_path: str = "experiments/routing_log.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, original_query: str, plan: RetrievalPlan) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "original_query": original_query,
            "used_query": plan.rewritten_query or original_query,
            "was_rewritten": plan.query_rewrite,
            "strategy": plan.strategy.value,
            "decided_by": plan.decided_by,
            "lexical_score": plan.lexical_score,
            "semantic_score": plan.semantic_score,
        }
        with self.log_path.open("a") as f:
            f.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# 6. Entry point
# ---------------------------------------------------------------------------

def route_query(
    query: str,
    llm_call_fn=None,
    recent_context: str = "",
    logger: Optional[RoutingLogger] = None,
) -> RetrievalPlan:
    """
    llm_call_fn: callable(messages: list[dict]) -> str. Defaults to
    OllamaRouterClient() if not provided, so the fallback works out of the
    box as long as Ollama is running locally with the default model pulled.
    Pass llm_call_fn=None explicitly (via a no-op lambda) if you want to
    disable the LLM fallback entirely, e.g. in unit tests.

    logger: if provided, every decision (rule-based AND LLM-fallback) is
    recorded — this is what makes the rewrite-vs-raw comparison possible
    later.
    """
    plan, feats = route_rule_based(query)

    if plan is None:
        caller = llm_call_fn if llm_call_fn is not None else OllamaRouterClient()
        messages = build_llm_router_messages(query, recent_context)
        try:
            raw_response = caller(messages)
            plan = parse_llm_router_response(raw_response, feats)
        except Exception:
            # Ollama unreachable, model not pulled, network error, etc. —
            # degrade to a safe default instead of taking down retrieval.
            plan = RetrievalPlan(
                strategy=Strategy.HYBRID,
                top_k=10,
                rerank=True,
                query_rewrite=False,
                lexical_score=feats.lexical_score,
                semantic_score=feats.semantic_score,
                decided_by="llm_fallback_error_default",
            )

    if logger is not None:
        logger.log(query, plan)

    return plan


if __name__ == "__main__":
    # Quick manual smoke tests — replace with real pytest cases in tests/
    # Note: "What controls that?" will try OllamaRouterClient and, if Ollama
    # isn't running locally, gracefully degrade to llm_fallback_error_default
    # rather than crash — that's intentional, see route_query's except clause.
    test_logger = RoutingLogger(log_path="experiments/routing_log_smoketest.jsonl")
    examples = [
        "Why does the payment service retry failed requests?",
        "What controls MAX_RETRY_LIMIT in payment.retry_config?",
        "config/payment_service.yaml retry settings",
        "What controls that?",
        "compare hybrid vs vector search trade-offs",
    ]
    for q in examples:
        plan = route_query(q, logger=test_logger)
        print(f"{q!r}\n  -> {plan.to_dict()} (lex={plan.lexical_score:.2f}, sem={plan.semantic_score:.2f}, by={plan.decided_by})\n")
    print(f"Logged decisions to {test_logger.log_path}")
