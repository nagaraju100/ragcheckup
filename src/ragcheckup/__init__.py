"""ragcheckup — Inspect RAG indices for structural problems.

Eval tools tell you your score dropped. ragcheckup tells you which chunks
are broken and why.
"""

from __future__ import annotations

__version__ = "0.1.0a0"

from ragcheckup.engine import Engine
from ragcheckup.models import (
    CheckResult,
    Chunk,
    ChunkSet,
    CorpusStats,
    Finding,
    Report,
)

__all__ = [
    "Chunk",
    "ChunkSet",
    "CheckResult",
    "CorpusStats",
    "Engine",
    "Finding",
    "Report",
]
