"""JSON report writer."""

from __future__ import annotations

from pathlib import Path


def write_json_report(report, output: str | None) -> None:
    """Write the report as JSON."""
    json_str = report.model_dump_json(indent=2, exclude_none=True)

    if output:
        Path(output).write_text(json_str, encoding="utf-8")
        print(f"Report written to {output}")
    else:
        import json as _json
        parsed = _json.loads(json_str)
        print(_json.dumps(parsed, indent=2, default=str))
