"""
app/ingestion/pipeline.py

Orchestrates the full ingestion path: load -> chunk -> embed -> index into
both the vector store and the BM25 lexical index, so either retrieval
strategy is usable immediately after ingestion completes.
"""

from __future__ import annotations

from app.ingestion.chunker import chunk_document
from app.ingestion.loader import load_directory
from app.models.schemas import Chunk, Document
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.vector import VectorRetriever


def ingest_directory(
    dir_path: str,
    vector_retriever: VectorRetriever,
    bm25_retriever: BM25Retriever,
) -> dict:
    documents: list[Document] = load_directory(dir_path)

    all_chunks: list[Chunk] = []
    for doc in documents:
        all_chunks.extend(chunk_document(doc))

    vector_retriever.index_chunks(all_chunks)
    bm25_retriever.index_chunks(all_chunks)

    return {
        "documents_ingested": len(documents),
        "chunks_indexed": len(all_chunks),
        "doc_ids": [d.doc_id for d in documents],
    }
