"""
app/api/routes/system.py

System status and runtime configuration endpoints used by the
production-style System pages in the frontend.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from fastapi import APIRouter

from app.core.config import settings
from app.core.ollama_client import ollama_client
from app.core.qdrant_store import QdrantStore

router = APIRouter()


async def _check_ollama() -> tuple[str, list[str]]:
    """Check Ollama availability and return installed model names."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_host.rstrip('/')}/api/tags")

        if response.status_code != 200:
            return "unreachable", []

        data = response.json()
        models = [
            model.get("name", "")
            for model in data.get("models", [])
            if model.get("name")
        ]

        return "ok", models

    except (httpx.HTTPError, ValueError):
        return "unreachable", []


async def _check_qdrant() -> tuple[str, dict]:
    """Check Qdrant and collect collection statistics."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"http://{settings.qdrant_host}:{settings.qdrant_port}/healthz"
            )

        if response.status_code != 200:
            return "unreachable", {}

        store = QdrantStore()

        collection = settings.qdrant_collection
        collections = [
            item.name
            for item in store.client.get_collections().collections
        ]

        if collection not in collections:
            return "ok", {
                "collection": collection,
                "exists": False,
                "points": 0,
                "segments": 0,
                "indexed_vectors": 0,
                "optimizer_status": "unknown",
            }

        info = store.client.get_collection(collection)

        return "ok", {
            "collection": collection,
            "exists": True,
            "points": info.points_count or 0,
            "segments": info.segments_count or 0,
            "indexed_vectors": info.indexed_vectors_count or 0,
            "optimizer_status": str(info.optimizer_status),
            "vectors": {
                "size": info.config.params.vectors.size,
                "distance": str(info.config.params.vectors.distance),
            },
        }

    except Exception:
        return "unreachable", {}


def _check_bm25() -> dict:
    """Inspect the persisted BM25 corpus without rebuilding the index."""
    path = Path(settings.bm25_persist_path)

    if not path.exists():
        return {
            "status": "missing",
            "path": str(path),
            "chunks": 0,
        }

    try:
        with path.open("r", encoding="utf-8") as file:
            chunk_count = sum(1 for line in file if line.strip())

        return {
            "status": "ok",
            "path": str(path),
            "chunks": chunk_count,
        }

    except OSError:
        return {
            "status": "error",
            "path": str(path),
            "chunks": 0,
        }


def _check_postgres() -> str:
    """
    Check PostgreSQL connectivity.

    psycopg2 is already part of the project's PostgreSQL stack.
    The connection is intentionally short-lived because this endpoint
    is a diagnostic endpoint rather than a database workload.
    """
    try:
        import psycopg2

        connection = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password,
            connect_timeout=3,
        )

        connection.close()
        return "ok"

    except Exception:
        return "unreachable"


@router.get("/system/status")
async def system_status():
    """Return runtime configuration and dependency health."""

    ollama_status, installed_models = await _check_ollama()
    qdrant_status, qdrant_info = await _check_qdrant()

    postgres_status = _check_postgres()
    bm25_info = _check_bm25()

    reranker_model = settings.reranker_model

    return {
        "service": {
            "name": settings.app_name,
            "environment": settings.app_env,
            "version": "0.1.0",
            "log_level": settings.log_level,
        },
        "dependencies": {
            "api": "ok",
            "ollama": ollama_status,
            "qdrant": qdrant_status,
            "postgres": postgres_status,
        },
        "models": {
            "ollama": settings.ollama_model,
            "ollama_host": settings.ollama_host,
            "installed_ollama_models": installed_models,
            "embedding": settings.embedding_model,
            "reranker": reranker_model,
            "reranker_status": "configured",
        },
        "retrieval": {
            "strategies": [
                "vector",
                "bm25",
                "hybrid",
            ],
            "default_top_k": 5,
            "chunk_size": settings.chunk_size_tokens,
            "chunk_overlap": settings.chunk_overlap_tokens,
            "vector_dimension": 384,
            "distance": "COSINE",
            "rrf_k": 60,
        },
        "qdrant": qdrant_info,
        "bm25": bm25_info,
        "paths": {
            "raw_data": settings.raw_data_dir,
            "processed_data": settings.processed_data_dir,
            "bm25_corpus": settings.bm25_persist_path,
            "routing_log": settings.routing_log_path,
        },
    }