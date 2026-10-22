"""
app/api/routes/ingest.py

POST /ingest — runs the load -> chunk -> embed -> index pipeline against
the configured raw data directory, indexing into both the vector store and
the BM25 lexical index. Synchronous/blocking for now; a background task
queue is a reasonable upgrade once ingestion runs against more than a
handful of files.
"""

import logging

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.dependencies import get_bm25_retriever, get_vector_retriever
from app.ingestion.pipeline import ingest_directory
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.vector import VectorRetriever

router = APIRouter()
_log = logging.getLogger(__name__)


@router.post("/ingest")
async def ingest(
    vector_retriever: VectorRetriever = Depends(get_vector_retriever),
    bm25_retriever: BM25Retriever = Depends(get_bm25_retriever),
):
    result = ingest_directory(settings.raw_data_dir, vector_retriever, bm25_retriever)
    _log.info(
        "ingestion completed dir=%s documents=%d chunks=%d",
        settings.raw_data_dir,
        result["documents_ingested"],
        result["chunks_indexed"],
    )
    return result
