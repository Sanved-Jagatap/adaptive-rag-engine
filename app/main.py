"""
app/main.py

FastAPI application entrypoint. Run locally with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
or via Docker Compose (see docker-compose.yml).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import evaluation, health, ingest, query, system
from app.core.config import settings
from app.core.logging_config import configure_logging

configure_logging()

app = FastAPI(
    title=settings.app_name,
    description="Adaptive RAG Engine — dynamic retrieval strategy selection, "
    "reranking, and grounded generation.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(ingest.router, tags=["ingestion"])
app.include_router(query.router, tags=["query"])
app.include_router(evaluation.router, tags=["evaluation"])
app.include_router(system.router, tags=["system"])


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "env": settings.app_env,
        "docs": "/docs",
    }
