"""
Simple RAG Pipeline — Pure Python, zero API keys.

Builds a vector index from text documents and answers questions
by retrieving the most similar chunks, then returns the raw
retrieved context (since no generative LLM is required for this
standalone example).

Dependencies:  pip install sentence-transformers faiss-cpu
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
@dataclass
class DocumentChunk:
    """A single piece of text with its metadata."""

    source: str       # file path the chunk came from
    text: str         # the chunk text itself
    chunk_index: int  # position within source file
    embedding: np.ndarray = field(repr=False, default_factory=lambda: np.empty(0))


@dataclass
class RAGResult:
    """Answer returned by the retrieval step."""

    query: str
    retrieved_chunks: List[DocumentChunk]
    combined_context: str


# ---------------------------------------------------------------------------
# Indexer
# ---------------------------------------------------------------------------
class SimpleIndexer:
    """Chunk documents and build a FAISS index."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def _chunk_text(self, text: str, max_tokens: int = 300) -> List[str]:
        """Split raw text on paragraph boundaries, merging until *max_tokens*."""
        paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        for para in paragraphs:
            token_est = len(para.split())
            if current_len + token_est > max_tokens and current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            current.append(para)
            current_len += token_est

        if current:
            chunks.append("\n".join(current))

        return chunks

    def build_index(
        self,
        documents_dir: str | Path,
        glob_pattern: str = "**/*.txt",
    ) -> List[DocumentChunk]:
        """Read every .txt file under *documents_dir* and return chunks with embeddings."""
        doc_dir = Path(documents_dir)
        files = sorted(doc_dir.glob(glob_pattern))

        all_chunks: List[DocumentChunk] = []

        for fpath in files:
            raw = fpath.read_text(encoding="utf-8")
            text_chunks = self._chunk_text(raw)
            for idx, chunk_text in enumerate(text_chunks):
                chunk = DocumentChunk(
                    source=str(fpath),
                    text=chunk_text,
                    chunk_index=idx,
                )
                all_chunks.append(chunk)

        # Embed all chunks at once
        if all_chunks:
            texts = [c.text for c in all_chunks]
            embeddings = self.model.encode(texts, normalize_embeddings=True)
            for chunk, emb in zip(all_chunks, embeddings):
                chunk.embedding = emb

        return all_chunks

    def _make_faiss_index(self, chunks: List[DocumentChunk]) -> faiss.IndexFlatIP:
        """Inner-product index (works with L2-normalized vectors → cosine)."""
        if not chunks:
            return faiss.IndexFlatIP(0)

        matrix = np.stack([c.embedding for c in chunks]).astype("float32")
        dim = matrix.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(matrix)
        return index


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------
class SimpleRetriever:
    """Retrieve top-K chunks for a query."""

    def __init__(self, indexer: SimpleIndexer, k: int = 3):
        self.indexer = indexer
        self.k = k

    def search(self, query: str) -> RAGResult:
        """Retrieve and return the top-K chunks."""
        chunks = self.indexer._cached_chunks  # type: ignore[attr-defined]

        if not chunks:
            raise RuntimeError("Index is empty. Call build_index() first.")

        index = self.indexer._make_faiss_index(chunks)

        # Embed the query
        q_emb = self.indexer.model.encode([query], normalize_embeddings=True)

        # Retrieve top-K (inner-product = cosine here)
        scores, indices = index.search(q_emb, min(self.k, len(chunks)))

        retrieved = [chunks[i] for i in indices[0] if i < len(chunks)]
        combined = "\n---\n".join(c.text for c in retrieved)

        return RAGResult(
            query=query,
            retrieved_chunks=retrieved,
            combined_context=combined,
        )


# ---------------------------------------------------------------------------
# Module-level cache (lazy singleton)
# ---------------------------------------------------------------------------
_INDEXER: SimpleIndexer | None = None


def reset_index() -> None:
    """Clear the cached index (useful for re-indexing)."""
    global _INDEXER
    _INDEXER = None


def get_indexer(documents_dir: str | Path) -> SimpleIndexer:
    """Lazy-initialise a global indexer for the given docs directory."""
    global _INDEXER
    if _INDEXER is None:
        _INDEXER = SimpleIndexer()
        _INDEXER._cached_chunks = _INDEXER.build_index(documents_dir)  # type: ignore[attr-defined]
    return _INDEXER
