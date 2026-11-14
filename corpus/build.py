#!/usr/bin/env python
"""Build the test corpus into JSONL exports and Chroma collections.

Usage:
    python build.py [--naive] [--good] [--all] [--help]

Options:
    --naive   Build the "naive" chunked index (plants failures).
    --good    Build the "good" chunked index (mostly clean).
    --all     Build both (default).

Output:
    corpus/chunks_naive.jsonl  — JSONL chunks from naive splitter
    corpus/chunks_good.jsonl   — JSONL chunks from good splitter
    corpus/chroma_naive/       — Chroma collection (if chromadb installed)
    corpus/chroma_good/        — Chroma collection (if chromadb installed)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE = Path(__file__).resolve().parent
DOCS_DIR = BASE / "docs"
OUTPUT_DIR = BASE


def list_documents() -> list[Path]:
    """Return all .md files under DOCS_DIR, sorted."""
    docs = sorted(DOCS_DIR.glob("*.md"))
    return [d for d in docs if d.is_file()]


# ---------------------------------------------------------------------------
# Chunking strategies
# ---------------------------------------------------------------------------

def naive_chunk(text: str, max_tokens: int = 300) -> list[str]:
    """Split raw text into chunks by fixed token window.

    This is the "naive" splitter that plants failures realistically:
    it doesn't respect headings, so chunks can split mid-sentence,
    orphan headings, and lose context.
    """
    paragraphs = [p.strip() for p in text.splitlines() if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
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


def good_chunk(text: str, max_tokens: int = 300) -> list[str]:
    """Split text respecting markdown headings and table blocks.

    This is the "good" splitter that avoids planting failures:
    it keeps headings with their content, doesn't split tables,
    and tries to keep sentences intact.
    """
    lines = text.splitlines()
    chunks: list[tuple[str, list[str]]] = []  # (heading_or_None, [lines])
    current_heading: str | None = None
    current_lines: list[str] = []
    current_tokens = 0

    for line in lines:
        stripped = line.strip()

        # Detect heading
        heading_match = re.match(r"^(#{1,3})\s+(.+)$", stripped)
        is_heading = heading_match is not None

        # Detect table row
        is_table_row = stripped.startswith("|")

        if is_heading:
            # Flush previous chunk
            if current_lines:
                chunks.append((current_heading, current_lines))
            current_heading = heading_match.group(2).strip()
            current_lines = [line]
            current_tokens = len(stripped.split())
        elif current_lines and current_heading and not current_lines[-1].strip().startswith("#"):
            # Check if adding this line would break a table
            if is_table_row:
                # Keep table together — just add it
                current_lines.append(line)
                current_tokens += len(stripped.split())
            elif current_tokens > max_tokens and not stripped:
                # Blank line after content → start new chunk
                chunks.append((current_heading, current_lines))
                current_heading = None
                current_lines = []
                current_tokens = 0
            else:
                current_lines.append(line)
                current_tokens += len(stripped.split())
        else:
            current_lines.append(line)
            current_tokens += len(stripped.split())

    if current_lines:
        chunks.append((current_heading, current_lines))

    # Flatten chunks to text
    result: list[str] = []
    for heading, lines in chunks:
        if heading:
            result.append(f"# {heading}\n" + "\n".join(lines))
        else:
            result.append("\n".join(lines))

    return result


# ---------------------------------------------------------------------------
# Chunk export
# ---------------------------------------------------------------------------

def build_chunks(
    doc_path: Path,
    chunks: list[str],
    splitter_name: str,
) -> list[dict[str, Any]]:
    """Convert a list of chunk texts to chunk export dicts."""
    source_name = doc_path.name
    title = doc_path.stem

    # Extract version/date from filename
    version_match = re.search(r"(\d{4})", source_name)
    version_date = version_match.group(1) if version_match else None

    chunks_list: list[dict[str, Any]] = []
    for idx, chunk_text in enumerate(chunks):
        chunk: dict[str, Any] = {
            "id": f"{source_name}_chunk{idx}_{splitter_name}",
            "text": chunk_text,
            "metadata": {
                "source": source_name,
                "title": title,
                "position": idx,
            },
        }
        if version_date:
            chunk["metadata"]["date"] = f"{version_date}-01-01"

        chunks_list.append(chunk)

    return chunks_list


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_splitter(splitter_name: str = "naive") -> list[list[str]]:
    """Build chunks for all documents using the specified splitter."""
    splitter = naive_chunk if splitter_name == "naive" else good_chunk
    all_chunks: list[dict[str, Any]] = []

    for doc_path in list_documents():
        text = doc_path.read_text(encoding="utf-8")
        chunks = splitter(text)
        chunk_dicts = build_chunks(doc_path, chunks, splitter_name)
        all_chunks.extend(chunk_dicts)

    return all_chunks


def write_jsonl(chunks: list[dict[str, Any]], filename: str) -> Path:
    """Write chunks to a JSONL file."""
    output_path = OUTPUT_DIR / filename
    with output_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"  Wrote {len(chunks)} chunks to {output_path}")
    return output_path


def build_chroma(chunks: list[dict[str, Any]], collection_name: str) -> Path:
    """Build a Chroma collection from chunks (if chromadb is installed)."""
    try:
        import chromadb
    except ImportError:
        print("  chromadb not installed. Skipping Chroma collection.")
        return Path()

    persist_dir = OUTPUT_DIR / f"chroma_{collection_name}"
    persist_dir.mkdir(exist_ok=True)

    client = chromadb.PersistentClient(path=str(persist_dir))

    # Use the same embedding model as specified in corpus/README.md
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")

        class EmbeddingFn:
            def __call__(self, input):
                return model.encode(input, normalize_embeddings=True).tolist()

        collection = client.create_collection(
            name=collection_name,
            embedding_function=EmbeddingFn(),
        )
    except ImportError:
        # No embedding model — use default (none)
        collection = client.create_collection(name=collection_name)

    ids = [c["id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    collection.add(ids=ids, documents=documents, metadatas=metadatas)

    count = collection.count()
    print(f"  Created Chroma collection '{collection_name}' with {count} chunks at {persist_dir}")

    return persist_dir


def main():
    args = sys.argv[1:]

    # Parse arguments
    build_naive = "--naive" in args or "--all" in args or len(args) == 0
    build_good = "--good" in args or "--all" in args

    if not build_naive and not build_good:
        print("Usage: python build.py [--naive] [--good] [--all]")
        sys.exit(1)

    print(f"Building corpus from {DOCS_DIR}...")
    print(f"  Documents found: {len(list_documents())}")
    print()

    if build_naive:
        print("Building naive index...")
        chunks = build_splitter("naive")
        write_jsonl(chunks, "chunks_naive.jsonl")
        build_chroma(chunks, "naive")
        print()

    if build_good:
        print("Building good index...")
        chunks = build_splitter("good")
        write_jsonl(chunks, "chunks_good.jsonl")
        build_chroma(chunks, "good")
        print()

    print("Done!")
    print()
    print("Output files:")
    print(f"  corpus/labels.yaml          — ground truth labels")
    if build_naive:
        print(f"  corpus/chunks_naive.jsonl   — naive chunk export")
    if build_good:
        print(f"  corpus/chunks_good.jsonl    — good chunk export")


if __name__ == "__main__":
    main()
