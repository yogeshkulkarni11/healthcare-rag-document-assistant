from pathlib import Path

from src.rag import load_documents, rewrite_query


def test_documents_are_loaded():
    chunks = load_documents(Path("data/documents"))
    assert len(chunks) >= 6
    assert all(c.source.endswith(".md") for c in chunks)


def test_query_rewriting_expands_terms():
    rewritten = rewrite_query("What is pre auth for a claim?")
    assert "preauthorization" in rewritten
    assert "reimbursement" in rewritten or "claim" in rewritten


def test_chunk_metadata_is_present():
    chunk = load_documents(Path("data/documents"))[0]
    assert chunk.chunk_id
    assert chunk.topic
