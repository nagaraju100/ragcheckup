"""Chroma vector database connector (read-only)."""

from __future__ import annotations

from typing import Any

from ragcheckup.connectors.base import Connector
from ragcheckup.models import Chunk, ChunkSet
from ragcheckup.normalize import normalize_metadata


class ChromaConnector(Connector):
    """Read-only connector for a Chroma persistent or HTTP collection.

    Supports URIs like:
    - ``chroma:///path/to/persist/dir/collection_name`` (local)
    - ``chroma+http://host:port/collection_name`` (HTTP)
    """

    def __init__(self, persist_dir: str | None = None, collection_name: str | None = None,
                 http_url: str | None = None) -> None:
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.http_url = http_url
        self._client: Any = None
        self._collection: Any = None

    def load(self) -> ChunkSet:
        import chromadb

        if self.http_url:
            self._client = chromadb.HttpClient(
                host=self.http_url.split("://")[-1].split("/")[0] if "://" in self.http_url else self.http_url,
                path="/" + self.http_url.split("://")[-1].split("/", 2)[-1] if "://" in self.http_url else "/default",
            )
        else:
            self._client = chromadb.PersistentClient(path=self.persist_dir)

        self._collection = self._client.get_collection(self.collection_name)

        chunks: list[Chunk] = []
        offset = 0
        limit = 1000  # page size

        while True:
            result = self._collection.get(
                offset=offset,
                limit=limit,
                include=["documents", "metadatas", "embeddings"],
            )

            ids = result.get("ids", [])
            if not ids:
                break

            docs = result.get("documents") or []
            metadatas = result.get("metadatas") or []
            embeddings = result.get("embeddings") or []

            for i, chunk_id in enumerate(ids):
                metadata = metadatas[i] if i < len(metadatas) else {}
                normalized = normalize_metadata(metadata)
                text = docs[i] if i < len(docs) else ""

                vector = None
                if embeddings and i < len(embeddings):
                    vector = embeddings[i]

                chunk = Chunk(
                    id=str(chunk_id),
                    text=text,
                    metadata=normalized,
                    source=normalized.get("source"),
                    title=normalized.get("title"),
                    position=normalized.get("position"),
                    vector=vector,
                )
                chunks.append(chunk)

            offset += len(ids)
            if len(ids) < limit:
                break

        return ChunkSet(
            chunks=chunks,
            origin=f"chroma://{self.collection_name}",
        )

    def native_retriever(self) -> Any | None:
        """Return the Chroma collection for native vector queries."""
        return self._collection

    def stored_embedder(self) -> Any | None:
        """Attempt to discover the stored embedding function.

        Newer Chroma versions persist the embedding function config on
        the collection.  We return it if discoverable.
        """
        if self._collection is None:
            return None
        try:
            return self._collection.metadata.get("embedding_function")
        except Exception:
            return None
