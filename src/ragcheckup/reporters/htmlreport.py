"""HTML report generator — single self-contained file, no external assets."""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader


def write_html_report(report, output: str | None) -> None:
    """Generate a self-contained HTML report and write to file or stdout."""
    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent)),
        autoescape=True,
    )

    template = env.get_template("template.html.j2")

    # Flatten findings for the template
    all_findings: list[tuple[str, object]] = []
    for r in report.results:
        for f in r.findings:
            all_findings.append((r.failure_mode.value, f))

    # Severity ordering for sorting
    severity_order = {"high": 0, "medium": 1, "low": 2}
    all_findings.sort(
        key=lambda x: (severity_order.get(x[1].severity.value, 2), x[0])
    )

    html = template.render(
        title="ragcheckup Report",
        origin=report.origin,
        tool_version=report.tool_version,
        chunk_count=report.chunk_count,
        duration_ms=report.duration_ms,
        started_at=report.started_at.isoformat() if hasattr(report.started_at, 'isoformat') else str(report.started_at),
        score_by_failure_mode=report.score_by_failure_mode,
        results_json=json.dumps([
            {
                "check_id": r.check_id,
                "failure_mode": r.failure_mode.value,
                "status": r.status.value,
                "skipped_reason": r.skipped_reason,
                "findings_count": len(r.findings),
                "summary": r.summary,
            }
            for r in report.results
        ], default=str),
        findings_json=json.dumps([
            {
                "check_id": f.check_id,
                "severity": f.severity.value,
                "chunk_ids": f.chunk_ids,
                "message": f.message,
                "evidence": f.evidence,
                "fix_url": f.fix_url,
            }
            for _, f in all_findings
        ], default=str),
    )

    if output:
        Path(output).write_text(html, encoding="utf-8")
        print(f"Report written to {output}")
    else:
        print(html)
