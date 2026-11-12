"""Unit tests for context checks."""

from __future__ import annotations

from datetime import datetime

from ragcheckup.checks.base import CheckContext
from ragcheckup.checks.context import (
    missing_heading,
    dangling_reference,
    starts_mid_sentence,
    ends_mid_sentence,
    size_outlier,
)
from ragcheckup.models import Chunk, CorpusStats
from ragcheckup.textutil import sentence_count


def _make_chunk(**kwargs) -> Chunk:
    defaults = {
        "id": "c1",
        "text": "Sample text here.",
        "metadata": {},
    }
    defaults.update(kwargs)
    return Chunk(**defaults)


def _make_stats(**kwargs) -> CorpusStats:
    return CorpusStats(
        total_chunks=100,
        word_count_mean=100.0,
        word_count_median=90.0,
        word_count_p5=50.0,
        word_count_p95=200.0,
        word_count_min=5,
        word_count_max=500,
    )


def test_missing_heading_with_title() -> None:
    chunk = _make_chunk(title="My Heading")
    ctx = CheckContext(stats=_make_stats())
    findings = missing_heading(chunk, ctx)
    assert len(findings) == 0


def test_missing_heading_no_title() -> None:
    chunk = _make_chunk()
    ctx = CheckContext(stats=_make_stats())
    findings = missing_heading(chunk, ctx)
    assert len(findings) == 1


def test_missing_heading_with_heading_text() -> None:
    chunk = _make_chunk(text="# Introduction\nSome content here.")
    ctx = CheckContext(stats=_make_stats())
    findings = missing_heading(chunk, ctx)
    assert len(findings) == 0


def test_dangling_reference_this() -> None:
    chunk = _make_chunk(text="this policy does not apply to items.")
    ctx = CheckContext(stats=_make_stats())
    findings = dangling_reference(chunk, ctx)
    assert len(findings) == 1


def test_dangling_reference_ok() -> None:
    chunk = _make_chunk(
        text="The return policy applies to all items.",
        title="Return Policy",
    )
    ctx = CheckContext(stats=_make_stats())
    findings = dangling_reference(chunk, ctx)
    assert len(findings) == 0


def test_starts_mid_sentence_lowercase() -> None:
    chunk = _make_chunk(text="and this continues the previous thought.")
    ctx = CheckContext(stats=_make_stats())
    findings = starts_mid_sentence(chunk, ctx)
    assert len(findings) == 1


def test_starts_mid_sentence_allowed_lowercase() -> None:
    chunk = _make_chunk(text="API documentation is available.")
    ctx = CheckContext(stats=_make_stats())
    findings = starts_mid_sentence(chunk, ctx)
    assert len(findings) == 0


def test_starts_mid_sentence_connector() -> None:
    chunk = _make_chunk(text="but this is a different clause.")
    ctx = CheckContext(stats=_make_stats())
    findings = starts_mid_sentence(chunk, ctx)
    assert len(findings) == 1


def test_ends_mid_sentence() -> None:
    chunk = _make_chunk(text="this sentence has no ending")
    ctx = CheckContext(stats=_make_stats())
    findings = ends_mid_sentence(chunk, ctx)
    assert len(findings) == 1


def test_ends_mid_sentence_ok() -> None:
    chunk = _make_chunk(text="this sentence ends properly.")
    ctx = CheckContext(stats=_make_stats())
    findings = ends_mid_sentence(chunk, ctx)
    assert len(findings) == 0


def test_size_outlier_small() -> None:
    chunks = [_make_chunk(text="hello world foo bar")] * 50
    chunks.append(_make_chunk(text="x"))  # tiny outlier (below floor of 8)
    ctx = CheckContext(stats=_make_stats())
    findings = size_outlier(chunks, ctx)
    # Should flag chunks with too few words (below absolute floor of 8)
    tiny_findings = [f for f in findings if "words" in f.message and "below" not in f.message]
    assert len(tiny_findings) >= 1, f"Expected small-outlier finding, got: {[f.message for f in findings[:3]]}"


def test_size_outlier_large() -> None:
    chunks = [_make_chunk(text="hello world foo bar")] * 50
    big_text = " ".join(["word"] * 1600)
    chunks.append(_make_chunk(text=big_text))
    ctx = CheckContext(stats=_make_stats())
    findings = size_outlier(chunks, ctx)
    large_findings = [f for f in findings if "1600 words" in f.message]
    assert len(large_findings) >= 1
