"""
scripts/smoke_test_ingestion.py

Sanity-checks the Phase 1 ingestion path (load -> chunk) against a sample
file, with no external services required (no Qdrant/Postgres/Ollama). Run:

    python scripts/smoke_test_ingestion.py

This is a manual smoke test, not a replacement for tests/ — it's here so
you can eyeball actual chunk output on a real file quickly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ingestion.chunker import chunk_document
from app.ingestion.loader import load_document

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "sample.md"


def main():
    if not SAMPLE_PATH.exists():
        print(f"No sample file at {SAMPLE_PATH} — create one to run this smoke test.")
        return

    doc = load_document(SAMPLE_PATH)
    print(f"Loaded document: {doc.doc_id} ({doc.doc_type.value}, {len(doc.raw_text)} chars)")

    chunks = chunk_document(doc, chunk_size_tokens=100, chunk_overlap_tokens=20)
    print(f"Produced {len(chunks)} chunks\n")

    for chunk in chunks:
        preview = chunk.text[:80].replace("\n", " ")
        print(f"  [{chunk.chunk_index}] {chunk.chunk_id} ({chunk.token_count} words) — {preview}...")


if __name__ == "__main__":
    main()
