import pytest

from app.ingestion.loader import load_document, load_directory
from app.models.schemas import DocumentType


def test_load_text_file(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("hello world")
    doc = load_document(f)
    assert doc.doc_type == DocumentType.TEXT
    assert doc.raw_text == "hello world"
    assert doc.title == "note"


def test_load_markdown_file(tmp_path):
    f = tmp_path / "readme.md"
    f.write_text("# Heading\n\nBody text.")
    doc = load_document(f)
    assert doc.doc_type == DocumentType.MARKDOWN
    assert "Heading" in doc.raw_text


def test_unsupported_extension_raises(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("a,b,c")
    with pytest.raises(ValueError):
        load_document(f)


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_document("/no/such/file.txt")


def test_doc_id_is_stable_for_same_path(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("hello world")
    doc1 = load_document(f)
    doc2 = load_document(f)
    assert doc1.doc_id == doc2.doc_id


def test_load_directory_finds_supported_files(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.md").write_text("b")
    (tmp_path / "c.csv").write_text("c")  # unsupported, should be skipped
    docs = load_directory(tmp_path)
    assert len(docs) == 2
