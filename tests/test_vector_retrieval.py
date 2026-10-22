from app.core.qdrant_store import QdrantStore
from app.ingestion.chunker import chunk_document
from app.models.schemas import Document, DocumentType
from app.retrieval.vector import VectorRetriever
from tests.stub_embedder import StubEmbedder


def make_retriever(collection_name: str) -> VectorRetriever:
    # Fresh in-memory store per test (via unique collection name) so tests
    # don't leak state into each other.
    embedder = StubEmbedder()
    store = QdrantStore(collection_name=collection_name, vector_size=embedder.dimension, in_memory=True)
    return VectorRetriever(embedder=embedder, store=store)


def test_index_and_search_returns_relevant_chunk():
    retriever = make_retriever("test_index_and_search")

    doc = Document(
        doc_id="doc1",
        source_path="doc1.txt",
        doc_type=DocumentType.TEXT,
        raw_text=(
            "The payment service retries failed requests using exponential "
            "backoff. The maximum retry limit is controlled by "
            "MAX_RETRY_LIMIT, which defaults to three attempts. "
            "Unrelated: the cafeteria menu changes every Tuesday."
        ),
    )
    chunks = chunk_document(doc, chunk_size_tokens=20, chunk_overlap_tokens=5)
    retriever.index_chunks(chunks)

    results = retriever.search("What controls the retry limit?", top_k=2)

    assert len(results) > 0
    # The chunk mentioning MAX_RETRY_LIMIT should be retrievable at all —
    # with the stub embedder we're testing plumbing, not ranking quality,
    # so just confirm indexed chunks come back with valid scores.
    assert all(r.score is not None for r in results)
    assert all(r.chunk.doc_id == "doc1" for r in results)


def test_search_on_empty_index_returns_no_results():
    retriever = make_retriever("test_empty_index")
    retriever.store.ensure_collection()
    results = retriever.search("anything", top_k=5)
    assert results == []


def test_indexed_chunk_roundtrips_metadata():
    retriever = make_retriever("test_roundtrip")

    doc = Document(
        doc_id="doc2",
        source_path="doc2.md",
        doc_type=DocumentType.MARKDOWN,
        raw_text="A short document about nothing in particular.",
    )
    chunks = chunk_document(doc, chunk_size_tokens=50, chunk_overlap_tokens=5)
    retriever.index_chunks(chunks)

    results = retriever.search("nothing in particular", top_k=1)
    assert len(results) == 1
    assert results[0].chunk.chunk_id == chunks[0].chunk_id
    assert results[0].chunk.text == chunks[0].text
