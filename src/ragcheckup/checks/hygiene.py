"""Hygiene checks — exact duplicates, missing IDs, empty/noise chunks."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from typing import Any

from ragcheckup.checks.base import CheckContext, register, _default_severity
from ragcheckup.models import Chunk, ChunkSet, Finding
from ragcheckup.textutil import line_break_ratio


# ---------------------------------------------------------------------------
# Corpus-scope checks
# ---------------------------------------------------------------------------

@register(
    id="hygiene.exact_duplicate",
    failure_mode="hygiene",
    default_severity="medium",
    scope="corpus",
)
def exact_duplicate(chunks: list[Chunk], ctx: CheckContext) -> list[Finding]:
    """Flag byte-identical chunk text appearing more than once."""
    # Hash normalized text (lowercased, whitespace collapsed)
    hash_map: dict[str, list[str]] = defaultdict(list)

    for chunk in chunks:
        normalized = chunk.text.lower()
        # Collapse multiple whitespace to single space
        normalized = " ".join(normalized.split())
        h = hashlib.md5(normalized.encode("utf-8")).hexdigest()[:12]
        hash_map[h].append(chunk.id)

    findings: list[Finding] = []
    for h, ids in hash_map.items():
        if len(ids) >= 2:
            findings.append(
                Finding(
                    check_id="hygiene.exact_duplicate",
                    severity=_default_severity("medium"),
                    chunk_ids=ids,
                    message=(
                        f"{len(ids)} chunks ({', '.join(ids[:5])}"
                        f"{'...' if len(ids) > 5 else ''}) have identical text. "
                        f"This wastes index space and may confuse retrieval."
                    ),
                    evidence={"duplicate_count": len(ids), "chunk_ids": ids[:10]},
                    fix_url=f"/checks/hygiene.exact_duplicate.html",
                )
            )

    return findings


@register(
    id="hygiene.missing_id_or_source",
    failure_mode="hygiene",
    default_severity="medium",
    scope="corpus",
)
def missing_id_or_source(chunks: list[Chunk], ctx: CheckContext) -> list[Finding]:
    """Flag chunks with no stable ID or no source reference."""
    findings: list[Finding] = []

    for chunk in chunks:
        has_id = bool(chunk.id) and chunk.id != f"row-{id(chunk)}"
        has_source = bool(chunk.source)

        if not has_id or not has_source:
            issues = []
            if not has_id:
                issues.append("no stable ID")
            if not has_source:
                issues.append("no source reference")

            findings.append(
                Finding(
                    check_id="hygiene.missing_id_or_source",
                    severity=_default_severity("medium"),
                    chunk_ids=[chunk.id],
                    message=(
                        f"Chunk {chunk.id} has {', '.join(issues)}. "
                        f"Without an ID or source, chunks cannot be traced back "
                        f"to their document or tracked for updates."
                    ),
                    evidence={
                        "has_id": has_id,
                        "has_source": has_source,
                        "source": chunk.source,
                    },
                    fix_url=f"/checks/hygiene.missing_id_or_source.html",
                )
            )

    return findings


@register(
    id="hygiene.empty_or_noise",
    failure_mode="hygiene",
    default_severity="high",
    scope="corpus",
)
def empty_or_noise(chunks: list[Chunk], ctx: CheckContext) -> list[Finding]:
    """Flag empty chunks and chunks with excessive noise (headers/footers, line breaks)."""
    findings: list[Finding] = []

    for chunk in chunks:
        text = chunk.text.strip()

        # Empty chunks
        if not text:
            findings.append(
                Finding(
                    check_id="hygiene.empty_or_noise",
                    severity=_default_severity("high"),
                    chunk_ids=[chunk.id],
                    message=(
                        f"Chunk {chunk.id} is empty. Empty chunks waste index space "
                        f"and can confuse retrieval systems."
                    ),
                    evidence={"text_length": 0},
                    fix_url=f"/checks/hygiene.empty_or_noise.html",
                )
            )
            continue

        # Noise: excessive line-break ratio (page headers/footers)
        lbr = line_break_ratio(chunk.text)
        if lbr > 0.35:
            findings.append(
                Finding(
                    check_id="hygiene.empty_or_noise",
                    severity=_default_severity("low"),
                    chunk_ids=[chunk.id],
                    message=(
                        f"Chunk {chunk.id} has a high line-break ratio ({lbr:.0%}). "
                        f"This may indicate repeated page headers, footers, or "
                        f"formatting noise from PDF extraction."
                    ),
                    evidence={
                        "line_break_ratio": lbr,
                        "truncated_text": text[:200],
                    },
                    fix_url=f"/checks/hygiene.empty_or_noise.html",
                )
            )

    return findings

