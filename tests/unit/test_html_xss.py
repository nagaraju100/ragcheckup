"""HTML report must not let chunk content inject markup or script."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ragcheckup.cli import app

PAYLOAD = "</script><img src=x onerror=alert(1)>"


def test_html_report_escapes_untrusted_content(tmp_path: Path) -> None:
    src = tmp_path / "chunks.jsonl"
    rows = [
        {"id": f"c{i}<b>", "text": f"{PAYLOAD} | a | b |\n|---|\n| 1 | 2 | 3 |", "source": "x.md"}
        for i in range(3)
    ]
    src.write_text("\n".join(json.dumps(r) for r in rows))
    out = tmp_path / "r.html"
    result = CliRunner().invoke(app, ["scan", str(src), "--format", "html", "--output", str(out)])
    assert result.exit_code == 0, result.output
    html = out.read_text(encoding="utf-8")
    assert PAYLOAD not in html
    assert "</script><img" not in html
    assert html.count("</script>") == 1  # only the template's own closing tag
