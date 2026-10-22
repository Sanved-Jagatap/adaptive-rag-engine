import pytest

from app.ingestion.chunker import chunk_document
from app.models.schemas import Document, DocumentType


def make_doc(text: str) -> Document:
    return Document(
        doc_id="test_doc",
        source_path="test.txt",
        doc_type=DocumentType.TEXT,
        title="test",
        raw_text=text,
    )


def test_empty_document_produces_no_chunks():
    doc = make_doc("")
    assert chunk_document(doc) == []


def test_short_document_produces_single_chunk():
    doc = make_doc("This is a short test document.")
    chunks = chunk_document(doc, chunk_size_tokens=400, chunk_overlap_tokens=60)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].doc_id == "test_doc"


def test_long_document_produces_multiple_overlapping_chunks():
    # Repeat a phrase enough times to exceed a small chunk size.
    doc = make_doc("word " * 500)
    chunks = chunk_document(doc, chunk_size_tokens=50, chunk_overlap_tokens=10)
    assert len(chunks) > 1
    # chunk_index should be sequential starting at 0
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    # every chunk_id should be unique
    assert len({c.chunk_id for c in chunks}) == len(chunks)


def test_overlap_must_be_smaller_than_chunk_size():
    doc = make_doc("some text")
    with pytest.raises(ValueError):
        chunk_document(doc, chunk_size_tokens=50, chunk_overlap_tokens=50)
