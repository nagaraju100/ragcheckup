"""Integration tests — CLI end-to-end, JSONL scan, and report format verification."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from ragcheckup.engine import Engine


def _corpus_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "corpus"


def test_scan_jsonl_produces_findings() -> None:
    """Scanning the naive corpus should produce findings from multiple check types."""
    engine = Engine(source=_corpus_path() / "chunks_naive.jsonl")
    report = engine.run()

    assert report.chunk_count > 0
    assert len(report.results) > 0

    # Should have findings from at least tables, context, versions, hygiene
    finding_count_by_mode: dict[str, int] = {}
    for r in report.results:
        mode = r.failure_mode.value
        finding_count_by_mode[mode] = sum(len(fr.findings) for fr in report.results if fr.failure_mode.value == mode)

    assert finding_count_by_mode.get("tables", 0) > 0, "Should find table problems"
    assert finding_count_by_mode.get("context", 0) > 0, "Should find context problems"
    assert finding_count_by_mode.get("versions", 0) > 0, "Should find version conflicts"


def test_scan_empty_corpus() -> None:
    """Scanning an empty corpus should produce results with 0 findings."""
    tmp = Path("/tmp/empty_chunks.json")
    tmp.write_text("[]")
    engine = Engine(source=tmp)
    report = engine.run()
    assert report.chunk_count == 0
    assert all(r.status.value != "error" for r in report.results)


def test_report_has_score_by_failure_mode() -> None:
    """Report should contain a score for each failure mode."""
    engine = Engine(source=_corpus_path() / "chunks_naive.jsonl")
    report = engine.run()

    for mode in ["tables", "context", "exact", "versions", "hygiene"]:
        assert mode in report.score_by_failure_mode, f"Missing score for {mode}"


def test_json_report_serialization() -> None:
    """Full JSON report should be valid and contain expected fields."""
    engine = Engine(source=_corpus_path() / "chunks_naive.jsonl")
    report = engine.run()

    json_str = report.model_dump_json(indent=2, exclude_none=True)
    parsed = json.loads(json_str)

    assert parsed["tool_version"].startswith("ragcheckup")
    assert parsed["chunk_count"] > 0
    assert isinstance(parsed["results"], list)
    assert len(parsed["results"]) > 0
    assert isinstance(parsed["score_by_failure_mode"], dict)


def test_check_listing() -> None:
    """Engine.list_checks() should return all registered checks including exact."""
    checks = Engine.list_checks()
    ids = [c["id"] for c in checks]

    expected_checks = [
        "context.dangling_reference",
        "context.ends_mid_sentence",
        "context.missing_heading",
        "context.size_outlier",
        "context.starts_mid_sentence",
        "exact.vector_miss_rate",
        "hygiene.empty_or_noise",
        "hygiene.exact_duplicate",
        "hygiene.missing_id_or_source",
        "table.flattened_numeric",
        "table.header_orphan",
        "table.markdown_broken",
        "version.missing_freshness_metadata",
        "version.near_duplicate",
        "version.same_title_multiple_dates",
    ]
    for expected in expected_checks:
        assert expected in ids, f"Missing check: {expected}"


def test_labels_yaml_exists_and_valid() -> None:
    """labels.yaml should exist and contain valid labels."""
    labels_path = _corpus_path() / "labels.yaml"
    assert labels_path.exists(), "labels.yaml should exist"

    labels = yaml.safe_load(labels_path.read_text(encoding="utf-8"))
    assert isinstance(labels, list)
    assert len(labels) > 0

    for label in labels:
        assert "id" in label
        assert "doc" in label
        assert "check" in label
        assert "applies_to" in label


def test_build_output_exists() -> None:
    """Built JSONL files should exist."""
    naive_path = _corpus_path() / "chunks_naive.jsonl"
    good_path = _corpus_path() / "chunks_good.jsonl"
    assert naive_path.exists(), "chunks_naive.jsonl should exist"
    assert good_path.exists(), "chunks_good.jsonl should exist"

    naive_lines = naive_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(naive_lines) > 0

    # Each line should parse as valid JSON
    for line in naive_lines[:5]:  # Sample first 5
        obj = json.loads(line)
        assert "id" in obj
        assert "text" in obj
        assert "metadata" in obj


def test_html_report_generated() -> None:
    """HTML report should be generated and contain expected content."""
    html_path = _corpus_path() / "report.html"
    assert html_path.exists(), "report.html should exist"

    content = html_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "ragcheckup" in content.lower()
    assert "Failure Mode Scores" in content


def test_config_loads() -> None:
    """Config module should load and parse YAML config."""
    from ragcheckup.config import load_config, Config

    config = load_config()  # No file → defaults
    assert config.fail_on == "never"
    assert config.disable == []

    # Test with a config file
    tmp = Path("/tmp/test_config.yaml")
    tmp.write_text(
        "version: 1\nfail_on: medium\ndisable:\n  - context.size_outlier\nchecks:\n  table.flattened_numeric:\n    numeric_ratio: 0.45\n"
    )
    config = load_config(tmp)
    assert config.fail_on == "medium"
    assert "context.size_outlier" in config.disable
    assert "table.flattened_numeric" in config.checks
