"""ragcheckup — Inspect RAG indices for structural problems.

Eval tools tell you your score dropped. ragcheckup tells you which chunks
are broken and why.
"""

from __future__ import annotations

__version__ = "0.1.0a0"

from ragcheckup.models import (
    Chunk,
    ChunkSet,
    CheckResult,
    CorpusStats,
    Finding,
    Report,
)
from ragcheckup.engine import Engine

__all__ = [
    "Chunk",
    "ChunkSet",
    "CheckResult",
    "CorpusStats",
    "Engine",
    "Finding",
    "Report",
]
