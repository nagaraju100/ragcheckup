"""Unit tests for the exact-string (Failure 3) check."""

from __future__ import annotations

from ragcheckup.checks.base import CheckContext
from ragcheckup.checks.exact import run_exact_check, _extract_identifiers
from ragcheckup.models import Chunk


def _make_chunk(**kwargs) -> Chunk:
    defaults = {"id": "c1", "text": "Sample text here."}
    defaults.update(kwargs)
    return Chunk(**defaults)


def _make_stats(total_chunks: int = 100) -> dict:
    return type("CorpusStats", (), {
        "total_chunks": total_chunks,
        "word_count_mean": 100.0,
        "word_count_median": 90.0,
        "word_count_p5": 50.0,
        "word_count_p95": 200.0,
        "word_count_min": 5,
        "word_count_max": 500,
        "avg_numeric_ratio": 0.0,
        "avg_line_break_ratio": 0.0,
    })()


def test_extract_identifiers_found() -> None:
    """Identifiers in chunks are extracted."""
    chunks = [
        _make_chunk(id="a", text="Product SKU: NW-TR-4B and ERR-4012 found"),
        _make_chunk(id="b", text="Contact NW-ST-CS1 for support"),
    ]
    ids = _extract_identifiers(chunks, seed=42, max_ids=300)
    # Should find ERR-4012, NW-TR-4B, NW-ST-CS1 (error codes + SKUs)
    assert len(ids) >= 2


def test_run_exact_no_vector_retriever() -> None:
    """Without a vector retriever, reports BM25 baseline only."""
    chunks = [
        _make_chunk(id="a", text="SKU: NW-TR-4B and ERR-4012 are in this chunk."),
        _make_chunk(id="b", text="NW-ST-CS1 and NW-TR-2A are different products."),
        _make_chunk(id="c", text="ERR-FL-03 and ERR-IGN-01 are error codes."),
        _make_chunk(id="d", text="Product NW-BV-1P is a bivouac tent."),
        _make_chunk(id="e", text="SKU NW-AC-HL1 headlamp costs $39."),
    ]
    ctx = CheckContext(stats=_make_stats(), seed=42)
    findings = run_exact_check(chunks, ctx, bm25_retriever=None, vector_retriever=None, k=5)
    assert len(findings) == 1
    assert "vector retriever" in findings[0].message.lower()
    assert "identifier_count" in findings[0].evidence


def test_run_exact_no_identifiers() -> None:
    """No identifiers → informative message."""
    chunks = [_make_chunk(text="Just regular English text with no codes.")]
    ctx = CheckContext(stats=_make_stats(), seed=42)
    findings = run_exact_check(chunks, ctx, bm25_retriever=None, vector_retriever=None, k=5)
    assert len(findings) == 1
    assert "no identifiable" in findings[0].message.lower()


def test_run_exact_with_bm25_only() -> None:
    """With BM25 retriever, reports keyword miss rate."""
    from ragcheckup.retrieval.bm25 import BM25Retriever

    chunks = [
        _make_chunk(id="a", text="Product SKU: NW-TR-4B and ERR-4012 found"),
        _make_chunk(id="b", text="Contact NW-ST-CS1 for support"),
        _make_chunk(id="c", text="ERR-FL-03 and ERR-IGN-01 are error codes."),
        _make_chunk(id="d", text="Product NW-BV-1P is a bivouac tent."),
        _make_chunk(id="e", text="SKU NW-AC-HL1 headlamp costs $39."),
        _make_chunk(id="f", text="SKU NW-TR-2A is a 2-person tent."),
        _make_chunk(id="g", text="Product NW-TR-4A costs $449."),
        _make_chunk(id="h", text="SKU NW-ST-IS1 is the integrated system."),
    ]
    bm25 = BM25Retriever(
        chunk_ids=[c.id for c in chunks],
        chunk_texts=[c.text for c in chunks],
    )
    ctx = CheckContext(stats=_make_stats(), seed=42)
    findings = run_exact_check(chunks, ctx, bm25_retriever=bm25, vector_retriever=None, k=5)
    assert len(findings) == 1
    assert "keyword_miss_rate" in findings[0].evidence
    assert findings[0].evidence["identifier_count"] > 0


def test_run_exact_severity_high() -> None:
    """When vector misses far more than keyword → high severity."""
    from ragcheckup.retrieval.bm25 import BM25Retriever

    # Create chunks where BM25 does well but a fake "vector" retriever does poorly
    chunks = [
        _make_chunk(id=f"chunk_{i}", text=f"Product SKU: SKU-{i:04d} is a great item about camping gear and equipment and products for sale.")
        for i in range(20)
    ]

    bm25 = BM25Retriever(
        chunk_ids=[c.id for c in chunks],
        chunk_texts=[c.text for c in chunks],
    )

    # Fake vector retriever that never hits
    class BadVectorRetriever:
        def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
            return []

    ctx = CheckContext(stats=_make_stats(), seed=42)
    findings = run_exact_check(chunks, ctx, bm25_retriever=bm25,
                               vector_retriever=BadVectorRetriever(), k=5)
    assert len(findings) == 1
    # When BM25 hits well but vector misses badly, gap >= 30 → high
    assert findings[0].severity.value == "high"
