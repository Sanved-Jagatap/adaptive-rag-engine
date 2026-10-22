"""
app/ingestion/loader.py

Phase 1 scope: parse PDF/Markdown/TXT files into Document objects. No
structure-aware metadata extraction yet (headings, sections) — that's a
Phase 2+ enhancement once the baseline pipeline is proven end-to-end.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.models.schemas import Document, DocumentType

SUPPORTED_EXTENSIONS = {".pdf": DocumentType.PDF, ".md": DocumentType.MARKDOWN, ".txt": DocumentType.TEXT}


def _make_doc_id(content: str) -> str:
    # Hash of the decoded TEXT CONTENT, not the file path. This was
    # previously hashlib.sha256(str(path.resolve())...) — a path-based ID
    # is NOT portable: the same file at a different absolute path (a
    # different machine, a different OS, even just a differently-named
    # parent folder) produces a completely different doc_id. That silently
    # broke experiments/eval_dataset_v1.jsonl's ground-truth chunk_ids the
    # moment the project ran on a machine other than the one it was built
    # on — Recall/Precision/MRR all read exactly 0.000, since every
    # relevant_chunk_id was baked in against paths that no longer existed.
    # Content-based hashing also has a nice side effect: path.read_text()
    # already normalizes line endings (\r\n -> \n) during decode, so this
    # is stable across Windows/Linux checkouts of the identical file too.
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _load_pdf(path: Path) -> str:
    import fitz  # PyMuPDF

    text_parts = []
    with fitz.open(path) as pdf:
        for page in pdf:
            text_parts.append(page.get_text())
    return "\n".join(text_parts)


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_document(path: str | Path) -> Document:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"No such file: {path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}' for {path}. "
            f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    doc_type = SUPPORTED_EXTENSIONS[ext]
    raw_text = _load_pdf(path) if doc_type == DocumentType.PDF else _load_text(path)

    return Document(
        doc_id=_make_doc_id(raw_text),
        source_path=str(path),
        doc_type=doc_type,
        title=path.stem,
        raw_text=raw_text,
        metadata={"file_size_bytes": path.stat().st_size},
    )


def load_directory(dir_path: str | Path) -> list[Document]:
    """Loads every supported file directly under dir_path (non-recursive
    for now — recursion is a one-line change once you actually need nested
    source directories)."""
    dir_path = Path(dir_path)
    documents = []
    for ext in SUPPORTED_EXTENSIONS:
        for file_path in sorted(dir_path.glob(f"*{ext}")):
            documents.append(load_document(file_path))
    return documents