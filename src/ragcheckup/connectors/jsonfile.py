"""JSON / JSONL file connector."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ragcheckup.models import Chunk, ChunkSet
from ragcheckup.normalize import normalize_metadata
from ragcheckup.connectors.base import Connector


class JsonFileConnector(Connector):
    """Load chunks from a JSON list or JSONL file."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> ChunkSet:
        text = self.path.read_text(encoding="utf-8")
        chunks = self._parse(text)
        return ChunkSet(
            chunks=chunks,
            origin=str(self.path),
        )

    def _parse(self, text: str) -> list[Chunk]:
        text = text.strip()
        if not text:
            return []

        # Try JSON list first
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return [self._to_chunk(item) for item in data]
            if isinstance(data, dict):
                return [self._to_chunk(data)]
        except json.JSONDecodeError:
            pass

        # Fall back to JSONL (one object per line)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return [self._to_chunk(json.loads(line)) for line in lines]

    def _to_chunk(self, item: dict[str, Any]) -> Chunk:
        """Convert a dict from a chunk export to a normalized Chunk."""
        metadata = item.get("metadata", {})
        if isinstance(metadata, dict) and "_raw" not in metadata:
            metadata = normalize_metadata(metadata)
        else:
            metadata = normalize_metadata(item.get("metadata", {}))

        # Handle alternative text keys
        text = item.get("text") or item.get("page_content") or item.get("content") or ""

        # Check for id at top-level first, then in metadata
        chunk_id = item.get("id") or metadata.get("id") or f"row-{id(item)}"
        source = item.get("source") or metadata.get("source")
        title = item.get("title") or metadata.get("title")
        position = item.get("position") or metadata.get("position")

        # Synthesize ID if missing
        if not chunk_id or chunk_id == "":
            chunk_id = f"row-{id(item)}"

        return Chunk(
            id=str(chunk_id),
            text=text,
            metadata=metadata,
            source=source,
            title=title,
            position=position,
        )

    def _chunk_to_chunk(self, item: dict[str, Any]) -> Chunk:
        """Convert a corpus-built JSONL chunk (source in metadata) to a Chunk."""
        metadata = item.get("metadata", {})
        metadata = normalize_metadata(metadata)

        text = item.get("text") or item.get("page_content") or item.get("content") or ""

        chunk_id = item.get("id") or metadata.get("id") or f"row-{id(item)}"
        source = item.get("source") or metadata.get("source")
        title = item.get("title") or metadata.get("title")
        position = item.get("position") or metadata.get("position")

        if not chunk_id or chunk_id == "":
            chunk_id = f"row-{id(item)}"

        return Chunk(
            id=str(chunk_id),
            text=text,
            metadata=metadata,
            source=source,
            title=title,
            position=position,
        )
