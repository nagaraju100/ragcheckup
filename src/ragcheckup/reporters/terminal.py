"""Terminal output reporter."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def print_terminal_report(report, verbose: bool = False) -> None:
    """Print a human-readable terminal report."""
    from ragcheckup.models import Severity

    # Summary header
    console.print()
    console.print(Panel(
        f"[bold]Source:[/bold] {report.origin}  |  "
        f"[bold]{report.chunk_count}[/bold] chunks  |  "
        f"[bold]{report.duration_ms}ms[/bold]",
        subtitle=f"ragcheckup {report.tool_version}",
    ))
    console.print()

    # Score table
    score_table = Table(title="Failure Mode Scores (0-100, higher = better)")
    score_table.add_column("Mode", style="cyan")
    score_table.add_column("Score", justify="right", style="green")
    score_table.add_column("Findings", justify="right")

    for mode in ["tables", "context", "exact", "versions", "hygiene"]:
        score = report.score_by_failure_mode.get(mode, 0)
        finding_count = 0
        for r in report.results:
            if r.failure_mode.value == mode:
                finding_count = len(r.findings)
        score_table.add_row(mode, str(score), str(finding_count))

    console.print(score_table)
    console.print()

    # Findings
    if verbose:
        all_findings = _all_findings_with_mode(report)
    else:
        all_findings = _top_findings(report, n=10)

    if not all_findings:
        console.print("[green]No findings. Your index looks clean.[/green]")
        return

    # Group by failure mode
    findings_by_mode: dict[str, list] = {}
    for mode, findings in sorted(report.score_by_failure_mode.items()):
        for r in report.results:
            if r.failure_mode.value == mode:
                findings_by_mode.setdefault(mode, []).extend(r.findings)

    for mode in ["tables", "context", "exact", "versions", "hygiene"]:
        findings = findings_by_mode.get(mode, [])
        if not findings:
            continue

        console.print(f"\n[bold cyan]{mode.upper()}[/bold cyan]")
        for f in findings:
            severity_label = f.severity.value.upper()
            color = {"high": "red", "medium": "yellow", "low": "blue"}.get(
                f.severity.value, "white"
            )
            console.print(
                f"  [{severity_label}] {f.message}"
            )
            if f.chunk_ids:
                console.print(f"    Chunks: {', '.join(f.chunk_ids[:5])}"
                              f"{'...' if len(f.chunk_ids) > 5 else ''}")
        console.print()


def _all_findings_with_mode(report) -> list:
    """Flatten all findings, tagged with their failure mode."""
    all_f = []
    for r in report.results:
        for f in r.findings:
            all_f.append((r.failure_mode.value, f))
    return all_f


def _top_findings(report, n: int = 10) -> list:
    """Return top-N findings across all modes, ordered by severity."""
    from ragcheckup.models import Severity

    all_f = []
    for r in report.results:
        for f in r.findings:
            all_f.append((r.failure_mode.value, f))

    severity_order = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}
    all_f.sort(key=lambda x: (severity_order.get(x[1].severity, 2), x[0]))

    return all_f[:n]
