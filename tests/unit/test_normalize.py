"""Unit tests for normalize module."""

from __future__ import annotations

from datetime import datetime

from ragcheckup.normalize import normalize_metadata, _parse_date


def test_normalize_basic() -> None:
    raw = {"id": "c1", "source": "doc.md", "title": "My Title"}
    result = normalize_metadata(raw)
    assert result["id"] == "c1"
    assert result["source"] == "doc.md"
    assert result["title"] == "My Title"


def test_normalize_with_alt_keys() -> None:
    raw = {"chunk_id": "c2", "file_path": "/path/to/file.txt", "heading": "H1"}
    result = normalize_metadata(raw)
    assert result["id"] == "c2"
    assert result["source"] == "/path/to/file.txt"
    assert result["title"] == "H1"


def test_normalize_preserves_raw() -> None:
    raw = {"id": "c1", "custom_field": "value"}
    result = normalize_metadata(raw)
    assert "_raw" in result
    assert result["_raw"]["custom_field"] == "value"


def test_parse_date_iso() -> None:
    result = _parse_date("2025-01-15")
    assert result == datetime(2025, 1, 15)


def test_parse_date_invalid() -> None:
    result = _parse_date("not a date")
    assert result is None


def test_normalize_empty() -> None:
    result = normalize_metadata({})
    assert result == {"_raw": {}}
