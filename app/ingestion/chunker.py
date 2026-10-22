"""
app/ingestion/chunker.py

Phase 1 scope: fixed-size chunking with overlap. This is intentionally the
simplest strategy that works — structure-aware chunking (splitting on
headings/sections, respecting sentence boundaries) is a Phase 2+ upgrade
once you have a baseline to compare it against. Don't build the fancier
chunker before you can measure whether it actually improves Recall@K over
this one.

Deliberately NOT using tiktoken here: it requires a network fetch of the
encoding file on first use (breaks in offline/firewalled Docker builds),
and cl100k_base approximates OpenAI's tokenizer specifically — not
whatever model you actually run through Ollama, so the "token count" would
already be an approximation dressed up as precision. Instead this uses a
whitespace-based word count, which is honest about being an approximation
and has zero external dependencies. Swap in the real tokenizer for
whichever model you standardize on if you need exact context-window
accounting later.
"""

from __future__ import annotations

import re

from app.core.config import settings
from app.models.schemas import Chunk, Document

_WORD_PATTERN = re.compile(r"\S+")


def _tokenize(text: str) -> list[str]:
    """Whitespace-delimited word split. Approximate token count — see
    module docstring for why this is preferred over a real tokenizer here."""
    return _WORD_PATTERN.findall(text)


def _detokenize(words: list[str]) -> str:
    return " ".join(words)


def chunk_document(
    document: Document,
    chunk_size_tokens: int | None = None,
    chunk_overlap_tokens: int | None = None,
) -> list[Chunk]:
    chunk_size = chunk_size_tokens or settings.chunk_size_tokens
    overlap = chunk_overlap_tokens or settings.chunk_overlap_tokens

    if overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap_tokens ({overlap}) must be smaller than "
            f"chunk_size_tokens ({chunk_size})"
        )

    words = _tokenize(document.raw_text)
    if not words:
        return []

    chunks: list[Chunk] = []
    start = 0
    index = 0
    stride = chunk_size - overlap

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text = _detokenize(chunk_words)

        chunks.append(
            Chunk(
                chunk_id=f"{document.doc_id}_chunk_{index:03d}",
                doc_id=document.doc_id,
                text=chunk_text,
                chunk_index=index,
                token_count=len(chunk_words),
                metadata={"source_path": document.source_path},
            )
        )

        index += 1
        start += stride
        if end == len(words):
            break

    return chunks
