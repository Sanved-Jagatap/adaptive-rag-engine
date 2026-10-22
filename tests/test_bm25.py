import json

from app.ingestion.chunker import chunk_document
from app.models.schemas import Document, DocumentType
from app.retrieval.bm25 import BM25Retriever


def make_chunks():
    doc = Document(
        doc_id="doc1",
        source_path="doc1.txt",
        doc_type=DocumentType.TEXT,
        raw_text=(
            "The payment service retries failed requests. MAX_RETRY_LIMIT "
            "controls the maximum number of attempts. Unrelated sentence "
            "about the cafeteria menu changing every Tuesday."
        ),
    )
    return chunk_document(doc, chunk_size_tokens=15, chunk_overlap_tokens=3)


def test_exact_term_match_ranks_above_unrelated_chunk():
    retriever = BM25Retriever()
    chunks = make_chunks()
    retriever.index_chunks(chunks)

    results = retriever.search("MAX_RETRY_LIMIT", top_k=5)

    assert len(results) >= 1
    # The chunk containing the literal term should score highest — this is
    # exactly the case BM25 should win at that a pure vector search might
    # blur.
    assert "MAX_RETRY_LIMIT" in results[0].chunk.text


def test_search_on_empty_index_returns_no_results():
    retriever = BM25Retriever()
    assert retriever.search("anything", top_k=5) == []


def test_zero_score_results_are_excluded():
    retriever = BM25Retriever()
    retriever.index_chunks(make_chunks())
    # A query with no term overlap at all against the corpus.
    results = retriever.search("xylophone quantum nebula", top_k=5)
    assert results == []


def test_persistence_roundtrip(tmp_path):
    persist_path = tmp_path / "bm25_corpus.jsonl"

    retriever1 = BM25Retriever(persist_path=persist_path)
    retriever1.index_chunks(make_chunks())
    assert persist_path.exists()

    # New retriever instance, same persist path — should reload the corpus
    # without needing index_chunks() called again.
    retriever2 = BM25Retriever(persist_path=persist_path)
    results = retriever2.search("MAX_RETRY_LIMIT", top_k=5)
    assert len(results) >= 1


def test_persisted_file_is_valid_jsonl(tmp_path):
    persist_path = tmp_path / "bm25_corpus.jsonl"
    retriever = BM25Retriever(persist_path=persist_path)
    chunks = make_chunks()
    retriever.index_chunks(chunks)

    lines = persist_path.read_text().strip().split("\n")
    assert len(lines) == len(chunks)
    for line in lines:
        data = json.loads(line)  # should not raise
        assert "chunk_id" in data
