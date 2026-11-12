"""Version conflict checks (Failure 4) — near-duplicates, same title multiple dates."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from ragcheckup.checks.base import CheckContext, register, _default_severity
from ragcheckup.models import Chunk, ChunkSet, Finding


def _stem_with_version(source: str | None) -> str:
    """Normalize a source filename by stripping version/date tokens.

    E.g. 'leave-policy-2023.pdf' and 'leave_policy_2025.pdf' -> 'leave-policy'.
    """
    if not source:
        return ""

    # Strip common version/date suffixes (before file extension)
    import re
    stem = re.sub(r'[_-]?\d{4}(\.[a-zA-Z]+)?$', '', source.lower())
    stem = re.sub(r'[_-]v\d+(\.[a-zA-Z]+)?$', '', stem)
    stem = re.sub(r'[^a-z0-9/_\-.]', '-', stem)
    return stem.strip("-")


def _extract_date(chunk: Chunk) -> datetime | str | None:
    """Extract a date string from chunk's updated or version metadata."""
    if chunk.updated:
        return chunk.updated

    raw = chunk.metadata.get("_raw", {})
    for key in ("date", "version_date", "effective_date", "last_modified"):
        val = raw.get(key) or chunk.metadata.get(key)
        if val and isinstance(val, str) and val.strip():
            return val.strip()

    # Try to extract from version
    version = chunk.metadata.get("version") or chunk.metadata.get("revision")
    if version:
        return str(version)

    return None


# ---------------------------------------------------------------------------
# Corpus-scope checks
# ---------------------------------------------------------------------------

@register(
    id="version.near_duplicate",
    failure_mode="versions",
    default_severity="medium",
    scope="corpus",
)
def near_duplicate(chunks: list[Chunk], ctx: CheckContext) -> list[Finding]:
    """Flag near-identical chunks from different sources or different dates."""
    # Group chunks by source stem (without version)
    stem_groups: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        stem = _stem_with_version(chunk.source)
        if stem:
            stem_groups[stem].append(chunk)

    findings: list[Finding] = []
    for stem, group in stem_groups.items():
        if len(group) < 2:
            continue

        # Check for chunks with different sources or different dates
        sources = set()
        dates = set()
        for chunk in group:
            if chunk.source:
                sources.add(chunk.source)
            d = _extract_date(chunk)
            if d:
                dates.add(str(d))

        # Only report if chunks have different sources or different dates
        if len(sources) > 1 or len(dates) > 1:
            affected_ids = [c.id for c in group[:10]]
            findings.append(
                Finding(
                    check_id="version.near_duplicate",
                    severity=_default_severity("medium"),
                    chunk_ids=affected_ids,
                    message=(
                        f"{len(group)} chunks from '{stem}' have similar content "
                        f"from {len(sources)} source(s) and {len(dates)} date(s). "
                        f"Users may retrieve outdated content."
                    ),
                    evidence={
                        "stem": stem,
                        "chunk_count": len(group),
                        "sources": list(sources),
                        "dates": list(dates),
                    },
                    fix_url=f"/checks/version.near_duplicate.html",
                )
            )

    return findings


@register(
    id="version.same_title_multiple_dates",
    failure_mode="versions",
    default_severity="medium",
    scope="corpus",
)
def same_title_multiple_dates(chunks: list[Chunk], ctx: CheckContext) -> list[Finding]:
    """Flag groups of chunks with the same title but different version/date metadata."""
    title_groups: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunks:
        title = chunk.title or chunk.source or ""
        title_groups[title].append(chunk)

    findings: list[Finding] = []
    for title, group in title_groups.items():
        dates = set()
        for chunk in group:
            d = _extract_date(chunk)
            if d:
                dates.add(str(d))

        if len(dates) > 1:
            chunk_ids = [c.id for c in group[:10]]
            findings.append(
                Finding(
                    check_id="version.same_title_multiple_dates",
                    severity=_default_severity("medium"),
                    chunk_ids=chunk_ids,
                    message=(
                        f"Multiple chunks share title '{title[:80]}' but have "
                        f"{len(dates)} different dates ({', '.join(sorted(dates)[:5])}). "
                        f"Users may not know which version is current."
                    ),
                    evidence={
                        "title": title[:100],
                        "chunk_count": len(group),
                        "dates": sorted(dates),
                    },
                    fix_url=f"/checks/version.same_title_multiple_dates.html",
                )
            )

    return findings


@register(
    id="version.missing_freshness_metadata",
    failure_mode="versions",
    default_severity="low",
    scope="corpus",
)
def missing_freshness_metadata(chunks: list[Chunk], ctx: CheckContext) -> list[Finding]:
    """Report the share of chunks with no version, last-updated, or date metadata."""
    total = len(chunks)
    if total == 0:
        return []

    missing = sum(
        1 for c in chunks
        if not _extract_date(c)
    )

    share = missing / total

    if share > 0.1:  # More than 10% missing → flag
        return [
            Finding(
                check_id="version.missing_freshness_metadata",
                severity=_default_severity("low"),
                chunk_ids=[],
                message=(
                    f"{share:.0%} of chunks ({missing}/{total}) have no date or "
                    f"version metadata. Without freshness info, the system cannot "
                    f"serve the most recent content."
                ),
                evidence={
                    "total_chunks": total,
                    "missing_count": missing,
                    "share": round(share, 3),
                },
                fix_url=f"/checks/version.missing_freshness_metadata.html",
            )
        ]

    return []
