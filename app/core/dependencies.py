"""
app/core/dependencies.py

Singletons for FastAPI dependency injection. Production endpoints get the
real SentenceTransformerEmbedder + real QdrantStore (server mode) + real
BM25Retriever (with disk persistence) + real CrossEncoderReranker — tests
inject their own stub embedder + in-memory QdrantStore directly instead of
using these.
"""

from functools import lru_cache

from app.core.config import settings
from app.core.qdrant_store import QdrantStore
from app.ingestion.embedder import SentenceTransformerEmbedder
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.vector import VectorRetriever
from app.routing.query_router import RoutingLogger


@lru_cache
def get_vector_retriever() -> VectorRetriever:
    embedder = SentenceTransformerEmbedder()
    store = QdrantStore(vector_size=embedder.dimension)
    return VectorRetriever(embedder=embedder, store=store)


@lru_cache
def get_bm25_retriever() -> BM25Retriever:
    return BM25Retriever(persist_path=settings.bm25_persist_path)


@lru_cache
def get_hybrid_retriever() -> HybridRetriever:
    return HybridRetriever(
        vector_retriever=get_vector_retriever(),
        bm25_retriever=get_bm25_retriever(),
    )


@lru_cache
def get_reranker() -> CrossEncoderReranker:
    return CrossEncoderReranker(model_name=settings.reranker_model)


@lru_cache
def get_routing_logger() -> RoutingLogger:
    return RoutingLogger(log_path=settings.routing_log_path)
