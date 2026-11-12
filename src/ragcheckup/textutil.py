"""Chunk-level text-utility helpers."""

from __future__ import annotations

import re
from typing import Iterable


def tokenize(text: str) -> list[str]:
    """Split text into word tokens using a simple whitespace rule."""
    return text.split()


def count_tokens(tokens: Iterable[str]) -> tuple[int, int]:
    """Return (numeric_token_count, total_token_count).

    A *numeric* token is one consisting entirely of digits (optionally
    with commas, periods, or minus signs).  Tokens like '42' or '3.14'
    count as numeric; tokens like 'id' or 'name' do not.
    """
    total = 0
    numeric = 0
    for t in tokens:
        total += 1
        cleaned = t.strip("-,.")
        if cleaned.isdigit() and len(cleaned) > 0:
            numeric += 1
        elif cleaned and cleaned.replace(".", "", 1).isdigit() and cleaned.count(".") <= 1:
            numeric += 1
    return numeric, total


def is_purely_numeric(text: str) -> bool:
    """Return True if the text is (mostly) numeric tokens."""
    tokens = tokenize(text)
    if not tokens:
        return False
    numeric, total = count_tokens(tokens)
    return total > 0 and numeric / total >= 0.6


def label_density(text: str, window: int = 2) -> float:
    """Share of numeric tokens that have an alphabetic neighbour within *window*."""
    tokens = tokenize(text)
    if not tokens:
        return 1.0  # no tokens → no problem

    numeric_positions = [
        i for i, t in enumerate(tokens) if t.strip("-,.").isdigit()
    ]

    if not numeric_positions:
        return 1.0  # no numbers → no problem

    labeled = 0
    for pos in numeric_positions:
        for offset in range(-window, window + 1):
            idx = pos + offset
            if 0 <= idx < len(tokens):
                token = tokens[idx].strip("-,.").lower()
                if token and token.isalpha():
                    labeled += 1
                    break

    return labeled / len(numeric_positions) if numeric_positions else 1.0


def numeric_ratio(text: str) -> float:
    """Share of tokens that are purely numeric."""
    tokens = tokenize(text)
    if not tokens:
        return 0.0
    numeric, total = count_tokens(tokens)
    return numeric / total


def line_break_ratio(text: str) -> float:
    """Share of lines that are blank or contain only whitespace."""
    lines = text.splitlines()
    if not lines:
        return 0.0
    blank = sum(1 for line in lines if not line.strip())
    return blank / len(lines)


def sentence_count(text: str) -> int:
    """Rough sentence count: split on `.`, `!`, `?`."""
    return len([s for s in re.split(r'[.!?]+', text) if s.strip()])


def is_sentence_start(text: str) -> bool:
    """Heuristic: does the text look like a sentence start?"""
    stripped = text.strip()
    if not stripped:
        return False
    return stripped[0].isupper() or stripped[0] in ('"', "'", '(', '[')


def looks_like_heading(text: str) -> bool:
    """Does this line look like a markdown or heading-style line?"""
    stripped = text.strip()
    if not stripped:
        return False
    # Markdown heading
    if stripped.startswith("# "):
        return True
    # ALL-CAPS short line (likely a heading)
    words = stripped.split()
    if len(words) <= 8 and stripped.isupper():
        return True
    # Short line followed by blank line (checked externally)
    return False


# ---------------------------------------------------------------------------
# Dangling-reference word lists
# ---------------------------------------------------------------------------

DANGLING_STARTERS: list[str] = [
    "this", "that", "these", "those",
    "it", "they", "its", "their",
    "the above", "as mentioned", "as noted", "the following",
    "as described", "as shown", "as explained",
]

ALLOWED_LOWERCASE: set[str] = {
    "iphone", "npm", "macos", "ios", "api", "sdk", "ui", "ux",
    "ai", "ml", "devops", "ci", "cd", "css", "html", "js", "ts",
    "qa", "saas", "paas", "iaas", "db", "sql", "http", "https",
    "pdf", "csv", "json", "yaml", "xml", "url", "id", "api",
    "a", "i", "am", "at", "by", "in", "of", "on", "to", "up",
}

CONNECTIVES: set[str] = {
    "and", "but", "or", "nor", "for", "yet", "so",
    "however", "moreover", "furthermore", "nevertheless",
    "therefore", "thus", "hence", "consequently",
    "although", "though", "while", "whereas", "unless",
    "because", "since", "if", "when", "whenever", "before", "after",
}
