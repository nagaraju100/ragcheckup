"""Connectors base protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ragcheckup.models import ChunkSet


class Connector(ABC):
    """Base protocol for loading chunks from a source.

    Connectors are **read-only** — they must never write to the source.
    """

    @abstractmethod
    def load(self) -> ChunkSet:
        """Load and return all chunks from the source."""

    def native_retriever(self) -> Any | None:
        """Return a native retrieval object if the connector supports it.

        Returns ``None`` by default.  Override in connectors that support
        vector queries (Chroma, Qdrant, etc.).
        """
        return None

    def stored_embedder(self) -> Any | None:
        """Return the embedding model used to build the index, if discoverable.

        Returns ``None`` by default.  Override in connectors that can
        introspect the stored embedding function.
        """
        return None


def parse_uri(uri: str) -> tuple[str, str, dict[str, Any]]:
    """Parse a source URI into (scheme, path, params).

    Supported schemes:
    - ``file:`` / no scheme (local file path)
    - ``chroma:`` (local persistent)
    - ``chroma+http:`` (Chroma over HTTP)
    """
    if "://" not in uri:
        return ("file", uri, {})

    scheme_prefix, rest = uri.split("://", 1)
    params: dict[str, Any] = {}

    if scheme_prefix == "file":
        return ("file", rest, params)

    if scheme_prefix == "chroma":
        parts = rest.split("/", 1)
        path = parts[1] if len(parts) > 1 else parts[0]
        return ("chroma", path, params)

    if scheme_prefix == "chroma+http":
        parts = rest.split("/", 1)
        path = parts[1] if len(parts) > 1 else parts[0]
        return ("chroma+http", path, params)

    raise ValueError(f"Unsupported URI scheme: {scheme_prefix}")
