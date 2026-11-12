#!/usr/bin/env python3
"""
Simple RAG CLI — ask questions, get answers grounded in retrieved documents.

Usage:
    python rag_cli.py                    # interactive mode
    python rag_cli.py "What is RAG?"     # one-shot query
    python rag_cli.py --help

No API keys or external services needed.

Dependencies:
    pip install sentence-transformers faiss-cpu
"""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

from rag_pipeline import get_indexer, SimpleRetriever


EXAMPLES_DIR = Path(__file__).parent / "documents"


def format_result(result) -> str:
    """Pretty-print a RAGResult."""
    lines = [
        "=" * 64,
        f"QUERY: {result.query}",
        "=" * 64,
        "",
        "RETRIEVED CONTEXT:",
        "-" * 40,
    ]

    for i, chunk in enumerate(result.retrieved_chunks, 1):
        lines.append(f"  [{i}] Source: {Path(chunk.source).name}")
        lines.append(f"  [{i}] Text:")
        for line in chunk.text.splitlines()[:15]:  # cap display
            lines.append(f"        {line}")
        if len(chunk.text.splitlines()) > 15:
            lines.append("        ...")
        lines.append("")

    lines.extend([
        "-" * 40,
        "TIP: To get a final generated answer, connect an LLM",
        "     (e.g. local Ollama) and append the context.",
        "=" * 64,
    ])

    return "\n".join(lines)


def run_query(query: str, docs_dir: Path) -> None:
    """Build index (if needed) and answer one query."""
    indexer = get_indexer(docs_dir)
    retriever = SimpleRetriever(indexer, k=3)
    result = retriever.search(query)
    print(format_result(result))


def interactive_mode(docs_dir: Path) -> None:
    """Repeatedly ask the user for questions."""
    print("Simple RAG — Interactive Mode")
    print("  Type your question, or 'quit' / 'exit' to leave.\n")

    while True:
        try:
            query = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        run_query(query, docs_dir)
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple RAG example — no API keys needed.")
    parser.add_argument("query", nargs="?", default=None, help="One-shot question, or run interactive mode.")
    parser.add_argument("query_v2", nargs="?", default=None, help="One-shot question 2, or run interactive mode.")
    parser.add_argument(
        "--documents",
        type=Path,
        default=EXAMPLES_DIR,
        help=f"Path to documents directory (default: {EXAMPLES_DIR})",
    )
    args = parser.parse_args()

    if not args.documents.is_dir():
        print(f"Error: documents directory not found: {args.documents}")
        sys.exit(1)

    if args.query is not None:
        run_query(args.query, args.documents)
    else:
        interactive_mode(args.documents)


if __name__ == "__main__":
    main()
