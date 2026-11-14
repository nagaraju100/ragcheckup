"""Exact-string blind spot check (Failure 3).

Extracts identifiers (SKUs, error codes, ticket IDs, version strings,
proper names) from the corpus itself, then queries the index with each
identifier to measure how often vector search misses the chunk containing
the identifier — compared with a BM25 keyword baseline.
"""

from __future__ import annotations

import math
import re
import random
from collections import defaultdict
from typing import Any

from ragcheckup.checks.base import CheckContext, register, _default_severity
from ragcheckup.models import Chunk, Finding


# Pattern definitions for identifier families
# Order matters: more specific patterns first
_PATTERN_RULES: list[tuple[str, re.Pattern]] = [
    # Error/status codes: ERR-4012, E1043, ERR-FL-01, ERR-IGN-01
    ("error_code", re.compile(r'\b[A-Z]{2,6}-?\d{2,6}\b')),
    # HTTP-style codes (only when preceded by error/status)
    ("http_code", re.compile(r'(?:error|status)\s*[=:]\s*\b[45]\d{2}\b', re.IGNORECASE)),
    # SKUs: uppercase-letter-digits-with-numeric requirement, e.g. NW-TR-4B, NW-ST-CS1
    # Must contain a dash and a digit to avoid matching words like "Product", "SKU"
    ("sku", re.compile(r'\b[A-Z]+-[A-Z0-9]+-[0-9][A-Za-z0-9_-]*\b')),
    # Ticket IDs: Jira-style ABC-1234, or #123
    ("ticket", re.compile(r'\b[A-Z]{1,4}[0-9]+-[0-9]+\b|#\d{3,}\b')),
    # Version strings: v1.2.3 or 1.2
    ("version", re.compile(r'\bv?\d+\.\d+(\.\d+)?\b')),
]


def _extract_identifiers(chunks: list[Chunk], seed: int = 42, max_ids: int = 300) -> list[str]:
    """Extract identifiers from the corpus, keeping those that appear in 1–5 chunks.

    Returns a deduplicated, seeded sample of identifiers.
    """
    # Collect all token matches with their chunk context
    id_chunks: dict[str, set[str]] = defaultdict(set)

    for chunk in chunks:
        text = chunk.text
        for family, pattern in _PATTERN_RULES:
            for match in pattern.finditer(text):
                identifier = match.group(0).strip()
                # Normalize: uppercase for consistency
                identifier = identifier.upper()
                if len(identifier) >= 3:  # Minimum length
                    id_chunks[identifier].add(chunk.id)

    # Keep only identifiers that appear in 1–5 chunks (specific enough)
    candidate_ids = [
        ident for ident, chunk_set in id_chunks.items()
        if 1 <= len(chunk_set) <= 5
    ]

    # Deduplicate and sample with fixed seed
    candidate_ids = sorted(set(candidate_ids))
    rng = random.Random(seed)

    # Sample up to max_ids
    if len(candidate_ids) > max_ids:
        sampled = rng.sample(candidate_ids, min(max_ids, len(candidate_ids)))
    else:
        sampled = candidate_ids

    return sampled


def _build_query_templates(identifier: str) -> list[str]:
    """Build a query string and templated question for each identifier."""
    return [identifier, f"What is {identifier}?", f"Find {identifier}"]


def run_exact_check(chunks: list[Chunk], ctx: CheckContext,
                    bm25_retriever: Any | None = None,
                    vector_retriever: Any | None = None,
                    k: int = 5, sample: int = 300) -> list[Finding]:
    """Run the exact-string blind spot check.

    Parameters
    ----------
    chunks :
        All chunks in the corpus.
    ctx :
        Check context (contains seed, stats).
    bm25_retriever :
        BM25 keyword retriever (required for baseline).
    vector_retriever :
        Vector retriever (optional). If None, the check reports that
        vector search cannot be evaluated.
    k :
        Number of top results to check (hit@k).
    sample :
        Maximum identifiers to test.

    Returns
    -------
    findings :
        A single finding with miss rates.
    """
    if not chunks:
        return []

    # Step 1: Extract identifiers
    seed = ctx.seed
    identifiers = _extract_identifiers(chunks, seed=seed, max_ids=sample)

    if not identifiers:
        return [Finding(
            check_id="exact.vector_miss_rate",
            severity=_default_severity("low"),
            chunk_ids=[],
            message="No identifiable exact-strings found in the corpus. "
                    "The exact-string check requires identifiable codes, SKUs, "
                    "ticket IDs, or version strings.",
            evidence={"identifier_count": 0},
            fix_url="/checks/exact.vector_miss_rate.html",
        )]

    # Build the reverse map: identifier -> set of chunk IDs it appears in
    id_to_chunks: dict[str, set[str]] = defaultdict(set)
    for chunk in chunks:
        text = chunk.text.upper()
        for ident in identifiers:
            if ident in text:
                id_to_chunks[ident].add(chunk.id)

    # Step 2: Query both retrievers for each identifier
    vector_hits = 0
    keyword_hits = 0
    vector_missed: list[str] = []
    keyword_missed: list[str] = []
    total_queries = 0

    for identifier in identifiers:
        queries = _build_query_templates(identifier)
        target_chunks = id_to_chunks[identifier]

        for query in queries:
            total_queries += 1

            # BM25 (keyword) query
            if bm25_retriever:
                bm25_results = bm25_retriever.search(query, top_k=k)
                bm25_hit_ids = {cid for cid, _ in bm25_results}
                if bm25_hit_ids & target_chunks:
                    keyword_hits += 1
                else:
                    keyword_missed.append(identifier)

            # Vector query (if available)
            if vector_retriever:
                vector_results = vector_retriever.search(query, top_k=k)
                vector_hit_ids = {cid for cid, _ in vector_results}
                if vector_hit_ids & target_chunks:
                    vector_hits += 1
                else:
                    vector_missed.append(identifier)

    # Step 3: Compute miss rates
    total_queries = max(total_queries, 1)
    vector_miss_rate = (len(vector_missed) / total_queries) * 100 if vector_retriever else None
    keyword_miss_rate = (len(keyword_missed) / total_queries) * 100

    # If no vector retriever, report the keyword baseline
    if not vector_retriever:
        return [Finding(
            check_id="exact.vector_miss_rate",
            severity=_default_severity("low"),
            chunk_ids=[],
            message=(
                f"Exact-string check needs a vector retriever to compare miss rates. "
                f"Keyword (BM25) missed {keyword_miss_rate:.0f}% of {total_queries} queries. "
                f"Pass --embed-model and a live index to compare vector vs keyword."
            ),
            evidence={
                "identifier_count": len(identifiers),
                "total_queries": total_queries,
                "keyword_miss_rate": round(keyword_miss_rate, 1),
                "vector_miss_rate": None,
                "vector_vs_keyword_gap": None,
            },
            fix_url="/checks/exact.vector_miss_rate.html",
        )]

    # Step 4: Compute severity based on the gap
    gap = (vector_miss_rate - keyword_miss_rate) if vector_miss_rate is not None else 0

    if gap >= 30:
        severity = _default_severity("high")
    elif gap >= 15:
        severity = _default_severity("medium")
    else:
        severity = _default_severity("low")

    return [Finding(
        check_id="exact.vector_miss_rate",
        severity=severity,
        chunk_ids=[],
        message=(
            f"Vector search missed {vector_miss_rate:.0f}% of {total_queries} "
            f"exact-identifier lookups (keyword search missed "
            f"{keyword_miss_rate:.0f}%). Your users' code and SKU searches will fail. "
            f"Enable hybrid search."
        ),
        evidence={
            "identifier_count": len(identifiers),
            "total_queries": total_queries,
            "vector_miss_rate": round(vector_miss_rate, 1),
            "keyword_miss_rate": round(keyword_miss_rate, 1),
            "vector_vs_keyword_gap": round(gap, 1),
            "vector_missed": vector_missed[:20],  # top 20 missed identifiers
        },
        fix_url="/checks/exact.vector_miss_rate.html",
    )]


@register(
    id="exact.vector_miss_rate",
    failure_mode="exact",
    default_severity="high",
    scope="corpus",
)
def vector_miss_rate(chunks: list[Chunk], ctx: CheckContext) -> list[Finding]:
    """Flag when vector search misses exact-string identifiers that BM25 finds."""
    # This is a corpus-level check; the engine wires up BM25/vector retrievers
    return run_exact_check(chunks, ctx)
