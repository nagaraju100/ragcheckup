"""Main engine: loads chunks, runs checks, produces reports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ragcheckup.connectors.base import Connector, parse_uri
from ragcheckup.connectors.jsonfile import JsonFileConnector
from ragcheckup.models import (
    Chunk,
    ChunkSet,
    CheckResult,
    CorpusStats,
    FailureMode,
    Finding,
    Report,
    Severity,
)
from ragcheckup.checks.base import CheckContext, get_checks, list_check_info

# Import all check modules to register them with the registry.
from ragcheckup import checks  # noqa: F401
from ragcheckup.checks import context  # noqa: F401
from ragcheckup.checks import hygiene  # noqa: F401
from ragcheckup.checks import tables  # noqa: F401
from ragcheckup.checks import versions  # noqa: F401
from ragcheckup.checks import exact  # noqa: F401
from ragcheckup.retrieval.bm25 import BM25Retriever
from ragcheckup.retrieval.base import NullRetriever
from ragcheckup.normalize import normalize_metadata


# Mapping from check module import path -> function name
_CHECK_MODULES: dict[str, str] = {}


def register_module(module_path: str, fn_name: str) -> None:
    """Register a check function by module path and name (for engine dispatch)."""
    _CHECK_MODULES[fn_name] = module_path


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class Engine:
    """Orchestrates loading, checking, and reporting."""

    def __init__(
        self,
        source: str | Path,
        embed_model: str | None = None,
        k: int = 5,
        sample: int = 300,
        seed: int = 42,
        fail_on: str = "never",
    ) -> None:
        self.source = str(source)
        self.embed_model = embed_model
        self.k = k
        self.sample = sample
        self.seed = seed
        self.fail_on = fail_on
        self._connector: Connector | None = None
        self._chunks: list[Chunk] = []
        self._stats: CorpusStats | None = None
        self._bm25: BM25Retriever | None = None

    def load(self) -> ChunkSet:
        """Load chunks from the source using the appropriate connector."""
        self._connector = self._create_connector(self.source)
        if self._connector is None:
            raise FileNotFoundError(
                f"Could not create a connector for '{self.source}'. "
                f"Supported formats: JSON/JSONL files, Chroma collections."
            )
        chunk_set = self._connector.load()
        self._chunks = chunk_set.chunks
        self._stats = self._compute_stats(self._chunks)

        # Build BM25 index for keyword baseline (used by exact-string check)
        # Only build if we have chunks (empty corpus → skip)
        if self._chunks:
            self._bm25 = BM25Retriever(
                chunk_ids=[c.id for c in self._chunks],
                chunk_texts=[c.text for c in self._chunks],
            )
        else:
            self._bm25 = None

        return chunk_set

    def _create_connector(self, source: str) -> Connector | None:
        """Parse URI and return the appropriate connector."""
        scheme, path, _ = parse_uri(source)

        if scheme == "file":
            p = Path(source)
            if not p.exists():
                return None
            return JsonFileConnector(p)

        if scheme in ("chroma", "chroma+http"):
            try:
                from ragcheckup.connectors.chroma import ChromaConnector
                # Parse path: could be "persist_dir/collection" or just "collection"
                if "/" in path:
                    parts = path.split("/", 1)
                    return ChromaConnector(
                        persist_dir=parts[0] if scheme == "chroma" else None,
                        collection_name=parts[1],
                        http_url=source if scheme == "chroma+http" else None,
                    )
                else:
                    return ChromaConnector(
                        collection_name=path,
                        http_url=source if scheme == "chroma+http" else None,
                    )
            except ImportError:
                print("Warning: chromadb not installed. Install with: pip install 'ragcheckup[chroma]'")
                return None

        return None

    def _compute_stats(self, chunks: list[Chunk]) -> CorpusStats:
        """Compute corpus-wide statistics in a single pass."""
        word_counts = [c.word_count for c in chunks]
        if not word_counts:
            return CorpusStats()

        word_counts_sorted = sorted(word_counts)
        n = len(word_counts_sorted)

        def percentile(data: list[int], p: float) -> float:
            if not data:
                return 0.0
            k = (len(data) - 1) * (p / 100)
            f = int(k)
            c = f + 1
            if c >= len(data):
                return float(data[f])
            return data[f] + (k - f) * (data[c] - data[f])

        # Unique sources (rough document count)
        sources = set()
        for c in chunks:
            if c.source:
                sources.add(c.source)

        return CorpusStats(
            total_chunks=n,
            total_documents=len(sources),
            word_count_mean=sum(word_counts) / n,
            word_count_median=percentile(word_counts_sorted, 50),
            word_count_p5=percentile(word_counts_sorted, 5),
            word_count_p95=percentile(word_counts_sorted, 95),
            word_count_min=min(word_counts),
            word_count_max=max(word_counts),
        )

    def run_checks(self) -> list[CheckResult]:
        """Run all checks and return results."""
        if not self._chunks:
            self.load()

        checks = get_checks()
        ctx = CheckContext(
            stats=self._stats,
            seed=self.seed,
        )

        results: list[CheckResult] = []
        for check_id, (fn, meta) in sorted(checks.items()):
            scope = meta["scope"]
            failure_mode = FailureMode(meta["failure_mode"])

            try:
                if scope == "chunk":
                    # Run per-chunk, aggregate findings
                    all_findings: list[Finding] = []
                    for chunk in self._chunks:
                        findings = fn(chunk, ctx)
                        all_findings.extend(findings)
                    result = CheckResult(
                        check_id=check_id,
                        failure_mode=failure_mode,
                        findings=all_findings,
                    )

                elif scope == "corpus":
                    # Check if this is the exact-string check that needs BM25
                    if check_id == "exact.vector_miss_rate":
                        from ragcheckup.checks.exact import run_exact_check
                        findings = run_exact_check(
                            self._chunks, ctx,
                            bm25_retriever=self._bm25,
                            k=self.k, sample=self.sample,
                        )
                    else:
                        findings = fn(self._chunks, ctx)
                    result = CheckResult(
                        check_id=check_id,
                        failure_mode=failure_mode,
                        findings=findings,
                    )

                else:  # retrieval scope — skip for now (requires embeddings)
                    result = CheckResult(
                        check_id=check_id,
                        failure_mode=failure_mode,
                        status="skipped",
                        skipped_reason="Retrieval checks require embedding model (not implemented in v0.1)",
                    )

            except Exception as e:
                result = CheckResult(
                    check_id=check_id,
                    failure_mode=failure_mode,
                    status="error",
                    findings=[],
                    summary={"error": str(e)},
                )

            results.append(result)

        return results

    def build_report(
        self,
        results: list[CheckResult],
    ) -> Report:
        """Build and return a final Report object."""
        started_at = datetime.now()
        import time
        start = time.time()

        # Compute scores by failure mode
        score_by_mode: dict[str, int] = {}
        mode_findings: dict[str, list[Finding]] = {
            "tables": [],
            "context": [],
            "exact": [],
            "versions": [],
            "hygiene": [],
        }

        for result in results:
            mode_str = result.failure_mode.value
            mode_findings[mode_str].extend(result.findings)

        for mode_str, findings in mode_findings.items():
            if not findings:
                score_by_mode[mode_str] = 0  # 0 if no findings
                continue

            # Weighted affected share: high=1.0, medium=0.5, low=0.1
            weighted = 0.0
            total = 0
            seen_chunks: set[str] = set()

            for f in findings:
                for cid in f.chunk_ids:
                    if cid not in seen_chunks:
                        seen_chunks.add(cid)
                        total += 1
                        if f.severity == Severity.HIGH:
                            weighted += 1.0
                        elif f.severity == Severity.MEDIUM:
                            weighted += 0.5
                        else:
                            weighted += 0.1

            total_chunks = self._stats.total_chunks if self._stats else 1
            affected_share = len(seen_chunks) / max(total_chunks, 1)
            score = max(0, round(100 * (1 - weighted / max(total, 1)), 0))
            score_by_mode[mode_str] = score

        elapsed_ms = int((time.time() - start) * 1000)

        return Report(
            tool_version="ragcheckup " + __import__("ragcheckup").__version__,
            origin=self.source,
            chunk_count=self._stats.total_chunks if self._stats else 0,
            started_at=started_at,
            duration_ms=elapsed_ms,
            results=results,
            score_by_failure_mode=score_by_mode,
        )

    def run(self) -> Report:
        """Execute a full scan: load, check, report."""
        self.load()
        results = self.run_checks()
        return self.build_report(results)

    @staticmethod
    def list_checks() -> list[dict[str, Any]]:
        """List all registered checks with their metadata."""
        return list_check_info()
