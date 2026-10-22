"""
app/core/ollama_client.py

Thin async wrapper around Ollama's REST API, for use inside the FastAPI app
(the routing module's OllamaRouterClient is a separate, sync, standalone
wrapper — this one is for endpoints that are already inside an async
request handler).
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import settings


@dataclass
class ChatResult:
    content: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_duration_ns: int | None
    load_duration_ns: int | None
    eval_duration_ns: int | None


class OllamaClient:
    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ):
        self.host = (host or settings.ollama_host).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout_seconds

    async def is_reachable(self) -> bool:
        """Used by the /health endpoint — cheap ping, no generation."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.host}/api/tags")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def chat_with_usage(self, messages: list[dict], temperature: float = 0.0) -> ChatResult:
        """Like chat(), but keeps Ollama's own token/timing metadata instead
        of discarding it. Ollama's /api/chat response already includes
        prompt_eval_count/eval_count (token counts) and total_duration/
        load_duration/eval_duration (nanoseconds) — reconstructing these
        ourselves (e.g. re-tokenizing the prompt) would be redundant and
        less accurate than what the server already computed."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": temperature},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return ChatResult(
                content=data["message"]["content"],
                prompt_tokens=data.get("prompt_eval_count"),
                completion_tokens=data.get("eval_count"),
                total_duration_ns=data.get("total_duration"),
                load_duration_ns=data.get("load_duration"),
                eval_duration_ns=data.get("eval_duration"),
            )

    async def chat(self, messages: list[dict], temperature: float = 0.0) -> str:
        """Plain-string convenience wrapper over chat_with_usage(), kept as
        the default for callers (generator.py, faithfulness.py, /query) that
        only need the answer text, not usage metadata."""
        result = await self.chat_with_usage(messages, temperature=temperature)
        return result.content


ollama_client = OllamaClient()
