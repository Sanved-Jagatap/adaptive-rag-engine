from app.core.qdrant_store import QdrantStore
from app.ingestion.chunker import chunk_document
from app.models.schemas import Document, DocumentType
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import HybridRetriever, reciprocal_rank_fusion
from app.retrieval.types import RetrievedChunk
from app.retrieval.vector import VectorRetriever
from tests.stub_embedder import StubEmbedder


def make_hybrid_retriever(collection_name: str) -> HybridRetriever:
    embedder = StubEmbedder()
    store = QdrantStore(collection_name=collection_name, vector_size=embedder.dimension, in_memory=True)
    vector_retriever = VectorRetriever(embedder=embedder, store=store)
    bm25_retriever = BM25Retriever()
    return HybridRetriever(vector_retriever=vector_retriever, bm25_retriever=bm25_retriever)


def make_chunks():
    doc = Document(
        doc_id="doc1",
        source_path="doc1.txt",
        doc_type=DocumentType.TEXT,
        raw_text=(
            "The payment service retries failed requests. MAX_RETRY_LIMIT "
            "controls the maximum number of attempts before giving up. "
            "Unrelated sentence about the cafeteria menu changing every "
            "Tuesday and Wednesday for lunch and dinner options."
        ),
    )
    return chunk_document(doc, chunk_size_tokens=15, chunk_overlap_tokens=3)


def test_reciprocal_rank_fusion_rewards_chunks_ranked_in_both_lists():
    # Build two RetrievedChunk lists sharing one chunk_id in common.
    from app.models.schemas import Chunk

    shared = Chunk(chunk_id="c1", doc_id="d", text="shared", chunk_index=0, token_count=1)
    only_vec = Chunk(chunk_id="c2", doc_id="d", text="vec only", chunk_index=1, token_count=1)
    only_bm25 = Chunk(chunk_id="c3", doc_id="d", text="bm25 only", chunk_index=2, token_count=1)

    vector_results = [RetrievedChunk(chunk=shared, score=0.9), RetrievedChunk(chunk=only_vec, score=0.5)]
    bm25_results = [RetrievedChunk(chunk=shared, score=5.0), RetrievedChunk(chunk=only_bm25, score=2.0)]

    fused = reciprocal_rank_fusion([vector_results, bm25_results])

    # The chunk ranked #1 in both lists should come out on top of the fusion.
    assert fused[0].chunk.chunk_id == "c1"
    assert {r.chunk.chunk_id for r in fused} == {"c1", "c2", "c3"}


def test_hybrid_retriever_indexes_and_searches_both_legs():
    retriever = make_hybrid_retriever("test_hybrid_search")
    chunks = make_chunks()

    retriever.vector_retriever.index_chunks(chunks)
    retriever.bm25_retriever.index_chunks(chunks)

    results = retriever.search("What controls MAX_RETRY_LIMIT?", top_k=3)

    assert len(results) > 0
    assert len(results) <= 3
    # Every result should be a chunk actually from the indexed set.
    indexed_ids = {c.chunk_id for c in chunks}
    assert all(r.chunk.chunk_id in indexed_ids for r in results)


def test_hybrid_retriever_handles_empty_index_gracefully():
    retriever = make_hybrid_retriever("test_hybrid_empty")
    retriever.vector_retriever.store.ensure_collection()
    results = retriever.search("anything", top_k=3)
    assert results == []
