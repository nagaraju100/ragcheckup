"""Unit tests for the engine."""

from __future__ import annotations

from pathlib import Path

from ragcheckup.engine import Engine


def test_scan_jsonl_file(tmp_path: Path) -> None:
    chunk_file = tmp_path / "chunks.json"
    chunk_file.write_text(
        '[{"id": "c1", "text": "hello world.", "metadata": {"source": "doc.md"}}, '
        '{"id": "c2", "text": "goodbye world.", "metadata": {"source": "doc.md"}}]'
    )
    engine = Engine(source=chunk_file)
    report = engine.run()
    assert report.chunk_count == 2
    assert len(report.results) > 0  # Should have some checks run


def test_scan_nonexistent_file() -> None:
    engine = Engine(source="/nonexistent/path/chunks.json")
    try:
        engine.run()
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_scan_empty_file(tmp_path: Path) -> None:
    chunk_file = tmp_path / "empty.json"
    chunk_file.write_text("[]")
    engine = Engine(source=chunk_file)
    report = engine.run()
    assert report.chunk_count == 0
    assert len(report.results) > 0  # Checks should still run (even with 0 chunks)


def test_list_checks() -> None:
    checks = Engine.list_checks()
    assert len(checks) > 0
    ids = [c["id"] for c in checks]
    assert "context.dangling_reference" in ids
    assert "hygiene.exact_duplicate" in ids
    assert "table.flattened_numeric" in ids
