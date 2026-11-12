"""Retrieval base protocol."""

from __future__ import annotations

from abc import ABC


class Retriever(ABC):
    """Protocol for performing retrieval queries."""

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """Return top-K (chunk_id, score) pairs for a query."""
        ...


class NullRetriever(Retriever):
    """A no-op retriever for when no search backend is available."""

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        return []
