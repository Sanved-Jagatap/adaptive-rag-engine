"""
app/models/schemas.py

Core data shapes shared across ingestion, retrieval, and generation.
Kept as plain Pydantic models (not DB models) for Phase 1 — SQLAlchemy
table definitions come in Phase 2 once Postgres is actually wired up for
metadata storage.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"


class Document(BaseModel):
    doc_id: str
    source_path: str
    doc_type: DocumentType
    title: str | None = None
    raw_text: str
    metadata: dict = Field(default_factory=dict)


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    chunk_index: int  # position within the parent document
    token_count: int
    metadata: dict = Field(default_factory=dict)
