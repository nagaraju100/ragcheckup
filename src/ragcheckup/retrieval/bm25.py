"""BM25 keyword retrieval baseline (pure Python, no server)."""

from __future__ import annotations

import math
from typing import Any

from rank_bm25 import BM25Okapi


class BM25Retriever:
    """BM25 keyword search over chunk texts.

    Built from a list of chunk texts; provides top-K query.
    """

    def __init__(self, chunk_ids: list[str], chunk_texts: list[str]) -> None:
        self.chunk_ids = chunk_ids
        self.tokenized_texts = [text.split() for text in chunk_texts]
        self.bm25 = BM25Okapi(self.tokenized_texts)

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """Return top-K (chunk_id, score) for a query string."""
        query_tokens = query.split()
        scores = self.bm25.get_scores(query_tokens)

        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        results: list[tuple[str, float]] = []
        for idx, score in indexed_scores[:top_k]:
            results.append((self.chunk_ids[idx], score))

        return results
