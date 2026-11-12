"""Unit tests for hygiene checks."""

from __future__ import annotations

from ragcheckup.checks.base import CheckContext
from ragcheckup.checks.hygiene import (
    exact_duplicate,
    missing_id_or_source,
    empty_or_noise,
)
from ragcheckup.models import Chunk, CorpusStats


def _make_chunk(**kwargs) -> Chunk:
    defaults = {
        "id": "c1",
        "text": "Sample text here.",
        "metadata": {},
    }
    defaults.update(kwargs)
    return Chunk(**defaults)


def _make_stats() -> CorpusStats:
    return CorpusStats(total_chunks=10, word_count_p5=30.0, word_count_p95=200.0)


def test_exact_duplicate() -> None:
    chunks = [
        _make_chunk(id="a", text="identical text here."),
        _make_chunk(id="b", text="identical text here."),
        _make_chunk(id="c", text="different content."),
    ]
    ctx = CheckContext(stats=_make_stats())
    findings = exact_duplicate(chunks, ctx)
    assert len(findings) == 1
    assert "2 chunks" in findings[0].message


def test_no_duplicates() -> None:
    chunks = [
        _make_chunk(id="a", text="text one"),
        _make_chunk(id="b", text="text two"),
    ]
    ctx = CheckContext(stats=_make_stats())
    findings = exact_duplicate(chunks, ctx)
    assert len(findings) == 0


def test_missing_id() -> None:
    chunks = [_make_chunk(id="", text="no id")]
    ctx = CheckContext(stats=_make_stats())
    findings = missing_id_or_source(chunks, ctx)
    assert len(findings) == 1


def test_missing_source() -> None:
    chunks = [_make_chunk(source="", text="no source")]
    ctx = CheckContext(stats=_make_stats())
    findings = missing_id_or_source(chunks, ctx)
    assert len(findings) == 1


def test_empty_chunk() -> None:
    chunks = [_make_chunk(text="")]
    ctx = CheckContext(stats=_make_stats())
    findings = empty_or_noise(chunks, ctx)
    assert len(findings) == 1
    assert findings[0].severity.value == "high"


def test_noise_chunk(tmp_path: Path) -> None:
    # Text with high ratio of blank/whitespace lines (page header/footer noise)
    lines = ["header line", "", "   ", "content line", "", "   ", "more content"]
    chunks = [_make_chunk(text="\n".join(lines))]
    ctx = CheckContext(stats=_make_stats())
    findings = empty_or_noise(chunks, ctx)
    # Should detect high line-break ratio (3 blank out of 7 lines ≈ 43%)
    noise_findings = [f for f in findings if "line-break" in f.message]
    assert len(noise_findings) >= 1, f"Expected noise finding, got: {[f.message for f in findings]}"
