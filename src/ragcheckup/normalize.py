"""Metadata key normalization for ragcheckup."""

from __future__ import annotations

from datetime import datetime
from typing import Any


# Default key-mapping lists, in lookup priority order.
# Users can extend these via config.

DEFAULT_KEY_MAPPINGS: dict[str, list[str]] = {
    "id": ["id", "chunk_id", "doc_id", "_id", "node_id"],
    "source": ["source", "file_path", "file_name", "url", "document_id", "doc_id"],
    "title": [
        "title", "heading", "section", "header",
        "heading_path", "document_title", "h1", "h2", "h3",
    ],
    "position": ["position", "chunk_index", "seq_num"],
    "updated": [
        "updated_at", "last_modified", "modified", "date",
        "version_date", "effective_date",
    ],
    "version": ["version", "revision"],
}


def normalize_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    """Map known metadata keys to ragcheckup's canonical names.

    Parameters
    ----------
    raw :
        The raw metadata dict from a connector (Chroma, JSONL, etc.).

    Returns
    -------
    dict
        A dict with canonical keys: ``id``, ``source``, ``title``,
        ``position``, ``updated``, ``version``.  Unknown keys are left
        untouched under ``_raw`` so users can still access them.
    """

    result: dict[str, Any] = {}

    for canonical, keys in DEFAULT_KEY_MAPPINGS.items():
        for key in keys:
            if key in raw:
                value = raw[key]
                # Parse dates if they look like ISO strings
                if canonical == "updated" and isinstance(value, str):
                    value = _parse_date(value)
                result[canonical] = value
                break

    # Always preserve a raw copy for debugging
    result["_raw"] = {k: v for k, v in raw.items() if k not in DEFAULT_KEY_MAPPINGS}

    return result


def _parse_date(value: str) -> datetime | None:
    """Try to parse an ISO-date string; return None on failure."""
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%b %d, %Y",
    ):
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None
