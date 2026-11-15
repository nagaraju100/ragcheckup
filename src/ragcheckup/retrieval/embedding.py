"""Embedding-based vector retriever (local, no server).

Builds dense embeddings from chunk texts using sentence-transformers,
then performs nearest-neighbor search using cosine similarity.
"""

from __future__ import annotations

from typing import Any

from ragcheckup.retrieval.base import Retriever


class EmbeddingRetriever(Retriever):
    """Embedding-based vector search over chunk texts.

    Built from chunk texts using a sentence-transformers model;
    provides top-K cosine-similarity queries.
    """

    def __init__(
        self,
        chunk_ids: list[str],
        chunk_texts: list[str],
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.chunk_ids = chunk_ids
        self.model_name = model_name

        # Load the embedding model (cached)
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)

        # Pre-compute embeddings for all chunks
        self._embeddings = self._model.encode(
            chunk_texts, normalize_embeddings=True, show_progress_bar=False
        ).tolist()

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        """Return top-K (chunk_id, cosine_score) for a query string."""
        query_emb = self._model.encode([query], normalize_embeddings=True)[0]
        scores = [
            sum(a * b for a, b in zip(query_emb, emb))  # cosine sim (already normalized)
            for emb in self._embeddings
        ]

        # Sort by score descending
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        return [
            (self.chunk_ids[idx], float(score))
            for idx, score in indexed_scores[:top_k]
        ]


def build_embedding_retriever(
    chunks: list[Any],
    model_name: str | None = None,
) -> EmbeddingRetriever | None:
    """Build an EmbeddingRetriever from a list of Chunk objects.

    Returns None if the model cannot be loaded or chunks are empty.
    """
    if not chunks:
        return None

    model_name = model_name or "all-MiniLM-L6-v2"
    try:
        return EmbeddingRetriever(
            chunk_ids=[c.id for c in chunks],
            chunk_texts=[c.text for c in chunks],
            model_name=model_name,
        )
    except Exception as e:
        print(f"Warning: Could not build embedding retriever: {e}")
        return None
