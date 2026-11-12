"""Unit tests for the core models."""

from __future__ import annotations

from datetime import datetime

from ragcheckup.models import (
    Chunk,
    ChunkSet,
    CorpusStats,
    Finding,
    CheckResult,
    Report,
    Severity,
    FailureMode,
    CheckScope,
    CheckStatus,
)


def test_chunk_word_count() -> None:
    chunk = Chunk(id="test", text="hello world foo bar")
    assert chunk.word_count == 4


def test_chunk_no_source() -> None:
    chunk = Chunk(id="test", text="some text")
    assert chunk.source is None
    assert chunk.title is None


def test_chunk_with_all_fields() -> None:
    chunk = Chunk(
        id="c1",
        text="hello",
        metadata={"source": "doc.md", "title": "Title"},
        source="doc.md",
        title="Title",
        position=0,
        updated=datetime(2025, 1, 1),
        vector=[0.1, 0.2, 0.3],
    )
    assert chunk.id == "c1"
    assert chunk.source == "doc.md"
    assert chunk.title == "Title"
    assert chunk.position == 0
    assert chunk.vector == [0.1, 0.2, 0.3]


def test_chunkset_by_source() -> None:
    chunks = [
        Chunk(id="a", text="text1", source="doc.md", position=0),
        Chunk(id="b", text="text2", source="doc.md", position=1),
        Chunk(id="c", text="text3", source="other.md", position=0),
    ]
    cs = ChunkSet(chunks=chunks, origin="test")
    by_src = cs.by_source
    assert len(by_src) == 2
    assert len(by_src["doc.md"]) == 2
    assert by_src["doc.md"][0].id == "a"


def test_corpus_stats() -> None:
    stats = CorpusStats(
        total_chunks=10,
        total_documents=3,
        word_count_mean=100.0,
        word_count_median=90.0,
        word_count_p5=50.0,
        word_count_p95=200.0,
        word_count_min=5,
        word_count_max=500,
    )
    assert stats.total_chunks == 10


def test_finding() -> None:
    f = Finding(
        check_id="test.check",
        severity=Severity.HIGH,
        chunk_ids=["c1", "c2"],
        message="Test finding",
        evidence={"key": "value"},
        fix_url="/checks/test.html",
    )
    assert f.check_id == "test.check"
    assert f.severity == Severity.HIGH
    assert len(f.chunk_ids) == 2


def test_check_result() -> None:
    r = CheckResult(
        check_id="test.check",
        failure_mode=FailureMode.CONTEXT,
        findings=[],
        summary={"affected_share": 0.1},
    )
    assert r.status.value == "ran"


def test_report_json_serialization() -> None:
    report = Report(
        tool_version="0.1.0",
        origin="test",
        chunk_count=10,
        started_at=datetime(2025, 1, 1),
        duration_ms=100,
        results=[],
        score_by_failure_mode={"context": 80},
    )
    json_str = report.model_dump_json()
    assert "0.1.0" in json_str
    assert json_str  # not empty


def test_severity_enum() -> None:
    assert Severity.HIGH.value == "high"
    assert Severity.MEDIUM.value == "medium"
    assert Severity.LOW.value == "low"
