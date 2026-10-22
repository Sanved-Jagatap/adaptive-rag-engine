"""
app/api/routes/health.py

/health returns 200 as long as the API process itself is up, but the body
reports per-dependency status (Ollama, Qdrant) so you can tell "API is up
but Ollama isn't running" apart from "everything's fine" without digging
through logs. Postgres check is left as a stub for Phase 2, once
SQLAlchemy models exist to check against.
"""

import httpx
from fastapi import APIRouter

from app.core.config import settings
from app.core.ollama_client import ollama_client

router = APIRouter()


async def _check_qdrant() -> bool:
    url = f"http://{settings.qdrant_host}:{settings.qdrant_port}/healthz"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            return resp.status_code == 200
    except httpx.HTTPError:
        return False


@router.get("/health")
async def health():
    ollama_ok = await ollama_client.is_reachable()
    qdrant_ok = await _check_qdrant()

    return {
        "status": "ok",  # the API process responding at all
        "dependencies": {
            "ollama": "ok" if ollama_ok else "unreachable",
            "qdrant": "ok" if qdrant_ok else "unreachable",
            "postgres": "not_checked",  # Phase 2: wire up once models exist
        },
    }
