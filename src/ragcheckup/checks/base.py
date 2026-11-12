"""Checks base protocol and registry."""

from __future__ import annotations

from typing import Any, Callable, Iterable

from ragcheckup.models import Chunk, ChunkSet, CheckResult, CheckScope, FailureMode, Finding, Severity


class CheckContext:
    """Context passed to every check: config, stats, helpers."""

    def __init__(
        self,
        stats: Any,  # CorpusStats
        config: dict[str, Any] | None = None,
        seed: int = 42,
    ) -> None:
        self.stats = stats
        self.config = config or {}
        self.seed = seed


# Registry: check_id -> (function, metadata)
_checks: dict[str, tuple[Callable, dict[str, Any]]] = {}


def register(
    id: str,
    failure_mode: str,
    default_severity: str = "medium",
    scope: str = "chunk",
) -> Callable:
    """Decorator to register a check function."""

    def decorator(fn):
        _checks[id] = (
            fn,
            {
                "id": id,
                "failure_mode": failure_mode,
                "default_severity": default_severity,
                "scope": scope,
            },
        )
        return fn

    return decorator


def get_checks() -> dict[str, tuple[Callable, dict[str, Any]]]:
    """Return the full registry."""
    return dict(_checks)


def list_check_info() -> list[dict[str, Any]]:
    """Return human-readable info for all registered checks."""
    result = []
    for check_id, (fn, meta) in sorted(_checks.items()):
        result.append({
            "id": meta["id"],
            "failure_mode": meta["failure_mode"],
            "default_severity": meta["default_severity"],
            "scope": meta["scope"],
            "description": (fn.__doc__ or "").strip().split("\n")[0],
        })
    return result


def _default_severity(severity: str) -> Severity:
    return Severity(severity)
