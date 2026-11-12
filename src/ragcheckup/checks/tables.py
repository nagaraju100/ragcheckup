"""Table checks (Failure 1) — shredded tables, broken markdown, orphan headers."""

from __future__ import annotations

import re
from typing import Iterable

from ragcheckup.checks.base import CheckContext, register, _default_severity
from ragcheckup.models import Chunk, ChunkSet, Finding
from ragcheckup.textutil import count_tokens, label_density, numeric_ratio


# ---------------------------------------------------------------------------
# Chunk-scope checks
# ---------------------------------------------------------------------------

@register(
    id="table.flattened_numeric",
    failure_mode="tables",
    default_severity="high",
    scope="chunk",
)
def flattened_numeric(chunk: Chunk, ctx: CheckContext) -> list[Finding]:
    """Flag chunks dominated by numeric tokens with few labels — typical of flattened PDF tables."""
    text = chunk.text.strip()
    if not text:
        return []

    # Skip chunks that are explicitly marked as serialized tables
    if chunk.metadata.get("table_serialized") or chunk.metadata.get("serialized_table"):
        return []

    num_count, total_count = count_tokens(text)
    if total_count < 1:
        return []

    ratio = num_count / total_count
    labels = label_density(text, window=2)

    # Flag when numeric_ratio >= 0.4 AND label_density < 0.3 AND at least 12 numeric tokens
    if ratio >= 0.4 and labels < 0.3 and num_count >= 12:
        return [
            Finding(
                check_id="table.flattened_numeric",
                severity=_default_severity("high"),
                chunk_ids=[chunk.id],
                message=(
                    f"Chunk {chunk.id} appears to be a flattened table: "
                    f"{num_count} numeric tokens ({ratio:.0%} of all tokens), "
                    f"with only {labels:.0%} having nearby labels. "
                    f"No column headers to help users find these values."
                ),
                evidence={
                    "numeric_ratio": round(ratio, 3),
                    "label_density": round(labels, 3),
                    "numeric_count": num_count,
                    "total_tokens": total_count,
                },
                fix_url=f"/checks/table.flattened_numeric.html",
            )
        ]

    return []


# Regex for pipe-table rows
_PIPE_TABLE = re.compile(r"^\|(.+)\|$", re.MULTILINE)


@register(
    id="table.markdown_broken",
    failure_mode="tables",
    default_severity="high",
    scope="chunk",
)
def markdown_broken(chunk: Chunk, ctx: CheckContext) -> list[Finding]:
    """Flag Markdown tables with inconsistent columns, missing separators, or headers with no rows."""
    text = chunk.text.strip()
    if not text:
        return []

    rows = _PIPE_TABLE.findall(text)
    if len(rows) < 3:
        return []  # Need at least header, separator, data row

    col_counts = [len(row.split("|")) - 2 for row in rows]

    findings: list[Finding] = []
    issues = []

    # Check for separator row (all dashes)
    has_separator = any(
        all(c.strip() == "-" or c.strip() == ":" for c in row.split("|")[1:-1])
        for row in rows
    )

    if not has_separator:
        issues.append("missing separator row (---|)")

    # Inconsistent column counts
    unique_counts = set(col_counts)
    if len(unique_counts) > 1:
        issues.append(f"inconsistent columns (row counts: {sorted(unique_counts)})")

    # Header with no data rows
    header_row = rows[0] if rows else ""
    data_rows = rows[2:]  # skip header and separator
    if len(data_rows) == 0 and not has_separator:
        issues.append("header with no data rows")

    if issues:
        findings.append(
            Finding(
                check_id="table.markdown_broken",
                severity=_default_severity("high"),
                chunk_ids=[chunk.id],
                message=(
                    f"Chunk {chunk.id} contains a broken Markdown table: "
                    f"{'; '.join(issues)}."
                ),
                evidence={
                    "issues": issues,
                    "row_count": len(rows),
                    "column_counts": list(unique_counts),
                },
                fix_url=f"/checks/table.markdown_broken.html",
            )
        )

    return findings


@register(
    id="table.header_orphan",
    failure_mode="tables",
    default_severity="medium",
    scope="chunk",
)
def header_orphan(chunk: Chunk, ctx: CheckContext) -> list[Finding]:
    """Flag header-like lines at the end of a chunk with no data following in the same chunk."""
    text = chunk.text.strip()
    if not text:
        return []

    lines = text.splitlines()
    if len(lines) < 3:
        return []

    findings: list[Finding] = []

    # Look for header-like patterns: short, mostly title-cased or all-caps lines
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        words = stripped.split()
        if len(words) < 3 or len(words) > 10:
            continue

        # Title-cased or all-cased
        title_cased = all(w[0].isupper() for w in words if w)
        all_upper = all(w.isupper() for w in words if w)

        if not (title_cased or all_upper):
            continue

        # Check if this is near the end of the chunk
        if i < len(lines) - 3:
            continue  # Not near the end

        # Check if subsequent lines contain data
        subsequent = lines[i + 1 :]
        has_data = any(
            s.strip() and not (s.strip().split() and all(w[0].isupper() for w in s.strip().split() if w))
            for s in subsequent
        )

        if not has_data and subsequent:
            findings.append(
                Finding(
                    check_id="table.header_orphan",
                    severity=_default_severity("medium"),
                    chunk_ids=[chunk.id],
                    message=(
                        f"Chunk {chunk.id} has a header-like line "
                        f"('{stripped[:50]}...') with no data following in the same chunk. "
                        f"The table body was likely cut off into the next chunk."
                    ),
                    evidence={
                        "header": stripped[:80],
                        "subsequent_lines": len(subsequent),
                    },
                    fix_url=f"/checks/table.header_orphan.html",
                )
            )

    return findings

