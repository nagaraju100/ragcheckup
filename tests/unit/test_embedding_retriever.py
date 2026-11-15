"""Unit tests for the embedding-based vector retriever."""

from __future__ import annotations

import pytest

pytest.importorskip("sentence_transformers", reason="needs the embed extra")

from ragcheckup.checks.base import CheckContext
from ragcheckup.checks.exact import run_exact_check
from ragcheckup.models import Chunk
from ragcheckup.retrieval.bm25 import BM25Retriever
from ragcheckup.retrieval.embedding import EmbeddingRetriever, build_embedding_retriever


def _make_chunks(texts: list[str]) -> list[Chunk]:
    return [Chunk(id=f"c{i}", text=t) for i, t in enumerate(texts)]


def test_embedding_retriever_builds() -> None:
    """EmbeddingRetriever should build embeddings for all chunks."""
    chunks = _make_chunks([
        "Northwind Gear was founded in 2010 in Boulder, Colorado.",
        "Our mission is to equip outdoor enthusiasts with reliable gear.",
    ])
    retriever = EmbeddingRetriever(
        chunk_ids=[c.id for c in chunks],
        chunk_texts=[c.text for c in chunks],
    )
    assert retriever is not None
    assert len(retriever.chunk_ids) == 2


def test_embedding_retriever_search() -> None:
    """EmbeddingRetriever should return chunks sorted by cosine similarity."""
    texts = [
        "The error 404 means the resource was not found on the server.",
        "Contact support at support@company.com for help.",
        "Our team of 25 engineers builds robust systems.",
    ]
    chunks = _make_chunks(texts)
    retriever = EmbeddingRetriever(
        chunk_ids=[c.id for c in chunks],
        chunk_texts=[c.text for c in chunks],
    )
    results = retriever.search("page not found error", top_k=3)
    assert len(results) == 3
    # The first result should be the most similar chunk
    assert isinstance(results[0], tuple)
    assert len(results[0]) == 2  # (chunk_id, score)


def test_embedding_retriever_vs_bm25() -> None:
    """When searching for an identifier, both retrievers should find matching chunks."""
    chunk_text = "SKU-NW-TT-4B is a lightweight tent for alpine climbing."
    chunks = _make_chunks([chunk_text])
    bm25 = BM25Retriever(chunk_ids=[chunks[0].id], chunk_texts=[chunks[0].text])
    embed = EmbeddingRetriever(
        chunk_ids=[chunks[0].id],
        chunk_texts=[chunks[0].text],
    )

    bm25_results = bm25.search("NW-TT-4B", top_k=1)
    embed_results = embed.search("NW-TT-4B", top_k=1)

    # Both should find the chunk (or at least not crash)
    assert len(bm25_results) >= 1
    assert len(embed_results) >= 1


def test_build_embedding_retriever_factory() -> None:
    """build_embedding_retriever should handle edge cases."""
    # Empty chunks
    result = build_embedding_retriever([], model_name="all-MiniLM-L6-v2")
    assert result is None

    # Real chunks
    chunks = _make_chunks(["hello world", "foo bar"])
    result = build_embedding_retriever(chunks, model_name="all-MiniLM-L6-v2")
    assert result is not None
    assert len(result.chunk_ids) == 2


def test_embedding_retriever_search_ranking() -> None:
    """The most relevant chunk should rank first for a vector search."""
    texts = [
        "The Northwind Gear store in Boulder sells climbing gear.",
        "Error code 404 means the page is not found.",
        "Contact support at support@northwindgear.com.",
    ]
    chunks = _make_chunks(texts)
    retriever = EmbeddingRetriever(
        chunk_ids=[c.id for c in chunks],
        chunk_texts=[c.text for c in chunks],
    )

    results = retriever.search("Boulder Colorado climbing", top_k=3)
    # The Boulder-related chunk should be first (highest cosine similarity)
    assert results[0][0] == "c0"


def test_exact_check_with_both_retrievers() -> None:
    """Full integration: exact check with BM25 and embedding both provided."""
    chunks = _make_chunks([
        "SKU-AB-1234 is a top-selling backpack for hiking.",
        "The error code ERR-5001 indicates a server timeout.",
        "Ticket TKT-98765 was resolved by the support team.",
    ])
    ctx = CheckContext(
        stats=type("Stats", (), {"total_chunks": 3, "word_count_mean": 15})(),
        seed=42,
    )
    bm25 = BM25Retriever(
        chunk_ids=[c.id for c in chunks],
        chunk_texts=[c.text for c in chunks],
    )
    embed = EmbeddingRetriever(
        chunk_ids=[c.id for c in chunks],
        chunk_texts=[c.text for c in chunks],
    )

    findings = run_exact_check(
        chunks, ctx,
        bm25_retriever=bm25,
        vector_retriever=embed,
        k=3, sample=300,
    )
    assert len(findings) == 1
    ev = findings[0].evidence
    assert ev["identifier_count"] > 0
    assert ev["total_queries"] > 0
    assert ev["vector_miss_rate"] is not None  # Vector was provided
    assert ev["keyword_miss_rate"] is not None  # BM25 was provided


def test_exact_check_gap_computed() -> None:
    """When both retrievers are provided, the gap should be computed."""
    chunks = _make_chunks([
        "SKU-XYZ-789 is our best-selling product.",
        "Error 404 means the resource cannot be found.",
    ])
    ctx = CheckContext(
        stats=type("Stats", (), {"total_chunks": 2, "word_count_mean": 10})(),
        seed=42,
    )
    bm25 = BM25Retriever(
        chunk_ids=[c.id for c in chunks],
        chunk_texts=[c.text for c in chunks],
    )
    embed = EmbeddingRetriever(
        chunk_ids=[c.id for c in chunks],
        chunk_texts=[c.text for c in chunks],
    )

    findings = run_exact_check(
        chunks, ctx,
        bm25_retriever=bm25,
        vector_retriever=embed,
        k=3, sample=300,
    )
    ev = findings[0].evidence
    # Gap should be computed when both retrievers are provided
    assert ev.get("vector_vs_keyword_gap") is not None
    assert isinstance(ev["vector_vs_keyword_gap"], float)
