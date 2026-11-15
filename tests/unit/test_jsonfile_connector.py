"""Unit tests for JSON file connector."""

from __future__ import annotations

from pathlib import Path

from ragcheckup.connectors.jsonfile import JsonFileConnector


def test_load_json_list(tmp_path: Path) -> None:
    chunk_file = tmp_path / "chunks.json"
    chunk_file.write_text(
        '[{"id": "c1", "text": "hello", "metadata": {"source": "doc.md"}}, '
        '{"id": "c2", "text": "world", "metadata": {"source": "doc.md"}}]'
    )
    connector = JsonFileConnector(chunk_file)
    chunk_set = connector.load()
    assert len(chunk_set.chunks) == 2
    # The ID is extracted from metadata's "id" key
    assert any(c.id == "c1" for c in chunk_set.chunks)
    assert chunk_set.origin == str(chunk_file)


def test_load_jsonl(tmp_path: Path) -> None:
    chunk_file = tmp_path / "chunks.jsonl"
    chunk_file.write_text(
        '{"id": "c1", "text": "hello", "metadata": {"source": "doc.md"}}\n'
        '{"id": "c2", "text": "world", "metadata": {"source": "other.md"}}\n'
    )
    connector = JsonFileConnector(chunk_file)
    chunk_set = connector.load()
    assert len(chunk_set.chunks) == 2


def test_load_empty(tmp_path: Path) -> None:
    chunk_file = tmp_path / "empty.json"
    chunk_file.write_text("[]")
    connector = JsonFileConnector(chunk_file)
    chunk_set = connector.load()
    assert len(chunk_set.chunks) == 0


def test_load_alternative_text_keys(tmp_path: Path) -> None:
    chunk_file = tmp_path / "chunks.json"
    chunk_file.write_text(
        '[{"id": "c1", "page_content": "hello"}, '
        '{"id": "c2", "content": "world"}]'
    )
    connector = JsonFileConnector(chunk_file)
    chunk_set = connector.load()
    assert chunk_set.chunks[0].text == "hello"
    assert chunk_set.chunks[1].text == "world"
