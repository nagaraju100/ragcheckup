"""CLI interface for ragcheckup.

Usage:
    ragcheckup scan SOURCE [--format terminal|json] [--output PATH]
                         [--fail-on high|medium|low|never] [--verbose]
    ragcheckup checks                  # list all checks
    ragcheckup version
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(
    name="ragcheckup",
    help="Inspect RAG indices for structural problems that make retrieval fail.",
    add_completion=False,
)

console = Console()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command()
def scan(
    source: str = typer.Argument(..., help="Source to scan: path to JSON/JSONL, or chroma URI."),
    format: str = typer.Option("terminal", "--format", help="Output format: terminal, json."),
    output: str | None = typer.Option(None, "--output", "-o", help="Write report to file."),
    fail_on: str = typer.Option("never", "--fail-on", help="Exit with code 1 if findings at or above this severity."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show all findings, not just top 10."),
    k: int = typer.Option(5, "--k", help="Number of top results for retrieval checks."),
    seed: int = typer.Option(42, "--seed", help="Random seed for reproducible sampling."),
    embed_model: str | None = typer.Option(None, "--embed-model", help="Embedding model name (for exact-string check)."),
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
):
    """Scan a chunk source (JSONL file or Chroma collection) for structural problems."""
    from ragcheckup import __version__
    from ragcheckup.engine import Engine

    if version:
        console.print(f"ragcheckup {__version__}")
        return

    try:
        engine = Engine(
            source=source,
            embed_model=embed_model,
            k=k,
            seed=seed,
            fail_on=fail_on,
        )
        report = engine.run()
    except FileNotFoundError:
        console.print(f"[red]Error: Source not found: {source}[/red]")
        sys.exit(3)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(2)

    if format == "json":
        _write_json_report(report, output)
    else:
        _print_terminal_report(report, verbose)

    # Determine exit code
    if fail_on != "never":
        severity_order = {"low": 0, "medium": 1, "high": 2}
        threshold = severity_order.get(fail_on, 0)
        for result in report.results:
            for finding in result.findings:
                if severity_order.get(finding.severity.value, 0) >= threshold:
                    sys.exit(1)

    sys.exit(0)


@app.command()
def checks():
    """List all registered checks with IDs, failure modes, and severity."""
    from ragcheckup.engine import Engine

    check_info = Engine.list_checks()
    table = Table(title="Registered Checks")
    table.add_column("Check ID", style="cyan")
    table.add_column("Failure Mode", style="magenta")
    table.add_column("Severity", style="yellow")
    table.add_column("Scope", style="green")
    table.add_column("Description", style="white")

    for info in check_info:
        table.add_row(
            info["id"],
            info["failure_mode"],
            info["default_severity"],
            info["scope"],
            info["description"],
        )

    console.print(table)


@app.command()
def version():
    """Show version."""
    from ragcheckup import __version__
    console.print(f"ragcheckup {__version__}")


# ---------------------------------------------------------------------------
# Report formatters
# ---------------------------------------------------------------------------

def _print_terminal_report(report, verbose: bool = False) -> None:
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


def _write_json_report(report, output: str | None) -> None:
    """Write the report as JSON."""
    json_str = report.model_dump_json(indent=2)

    if output:
        Path(output).write_text(json_str, encoding="utf-8")
        console.print(f"[green]Report written to {output}[/green]")
    else:
        console.print(json_str)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
