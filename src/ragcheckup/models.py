"""Data models for ragcheckup core types."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Severity levels for findings."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FailureMode(str, Enum):
    """The five failure modes (evalset is a separate command)."""

    TABLES = "tables"
    CONTEXT = "context"
    EXACT = "exact"
    VERSIONS = "versions"
    HYGIENE = "hygiene"


class CheckScope(str, Enum):
    """Scope of a check: per-chunk, corpus-wide, or retrieval."""

    CHUNK = "chunk"
    CORPUS = "corpus"
    RETRIEVAL = "retrieval"


class CheckStatus(str, Enum):
    """Whether a check ran, was skipped, or errored."""

    RAN = "ran"
    SKIPPED = "skipped"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------

class Chunk(BaseModel):
    """A single chunk with normalized metadata fields."""

    id: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None
    title: str | None = None
    position: int | None = None
    updated: datetime | None = None
    vector: list[float] | None = None

    @property
    def word_count(self) -> int:
        """Number of whitespace-separated tokens in text."""
        return len(self.text.split())


class CorpusStats(BaseModel):
    """Aggregate statistics computed once for the whole corpus."""

    total_chunks: int = 0
    total_documents: int = 0
    word_count_mean: float = 0.0
    word_count_median: float = 0.0
    word_count_p5: float = 0.0
    word_count_p95: float = 0.0
    word_count_min: int = 0
    word_count_max: int = 0
    avg_numeric_ratio: float = 0.0
    avg_line_break_ratio: float = 0.0


class Finding(BaseModel):
    """A single finding about a chunk or the corpus."""

    check_id: str
    severity: Severity
    chunk_ids: list[str] = Field(default_factory=list)
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    fix_url: str = ""


class CheckResult(BaseModel):
    """Result of running one check against the corpus."""

    check_id: str
    failure_mode: FailureMode
    status: CheckStatus = CheckStatus.RAN
    skipped_reason: str | None = None
    findings: list[Finding] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class ChunkSet(BaseModel):
    """Collection of chunks from a single source."""

    chunks: list[Chunk]
    origin: str

    @property
    def by_source(self) -> dict[str, list[Chunk]]:
        """Group chunks by source, sorted by position."""
        groups: dict[str, list[Chunk]] = {}
        for chunk in sorted(self.chunks, key=lambda c: (c.position or 0, c.id)):
            key = chunk.source or "unknown"
            groups.setdefault(key, []).append(chunk)
        return groups


class Report(BaseModel):
    """Full scan report, JSON-serialisable."""

    tool_version: str
    schema_version: int = 1
    origin: str
    chunk_count: int
    started_at: datetime
    duration_ms: int
    results: list[CheckResult] = Field(default_factory=list)
    score_by_failure_mode: dict[str, int] = Field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        """Determine exit code from findings and configured threshold."""
        # This is a simplification; the CLI handles the threshold.
        has_high = any(f.severity == Severity.HIGH for r in self.results for f in r.findings)
        return 1 if has_high else 0
