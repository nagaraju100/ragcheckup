"""Configuration file support for ragcheckup.

Loads a ``ragcheckup.yaml`` (or ``--config PATH``) and merges it with
CLI defaults.

Example ``ragcheckup.yaml``::

    version: 1
    fail_on: high
    metadata_keys:
      title: [title, heading, section]
      updated: [updated_at, effective_date]
    checks:
      context.dangling_reference:
        severity: low
      table.flattened_numeric:
        numeric_ratio: 0.45
    exact.vector_miss_rate:
      k: 5
      sample: 300
    disable:
      - context.size_outlier
    ignore:
      chunk_ids: [faq-001]
      sources: ["legacy/*"]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = "ragcheckup.yaml"


class Config:
    """Parsed configuration from a YAML file."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = data or {}

    @property
    def version(self) -> int:
        return self.data.get("version", 1)

    @property
    def fail_on(self) -> str:
        return self.data.get("fail_on", "never")

    @property
    def metadata_keys(self) -> dict[str, list[str]]:
        return self.data.get("metadata_keys", {})

    @property
    def checks(self) -> dict[str, dict[str, Any]]:
        """Per-check overrides: {check_id: {severity, numeric_ratio, ...}}."""
        return self.data.get("checks", {})

    @property
    def disable(self) -> list[str]:
        """Checks to disable (by ID)."""
        return self.data.get("disable", [])

    @property
    def ignore(self) -> dict[str, list[str]]:
        """Chunk IDs or sources to ignore."""
        return self.data.get("ignore", {})

    def is_check_disabled(self, check_id: str) -> bool:
        return check_id in self.disable

    def get_check_overrides(self, check_id: str) -> dict[str, Any]:
        return self.checks.get(check_id, {})

    def should_ignore_chunk(self, chunk_id: str, source: str | None) -> bool:
        ignore_ids = self.ignore.get("chunk_ids", [])
        if chunk_id in ignore_ids:
            return True
        ignore_sources = self.ignore.get("sources", [])
        if source:
            import fnmatch
            for pattern in ignore_sources:
                if fnmatch.fnmatch(source, pattern):
                    return True
        return False


def load_config(path: str | Path | None = None) -> Config:
    """Load configuration from a YAML file.

    If *path* is ``None``, looks for ``ragcheckup.yaml`` in the
    current working directory.  Returns a :class:`Config` with sensible
    defaults when no file is found.
    """
    if path is None:
        candidate = Path(DEFAULT_CONFIG_PATH)
        if not candidate.exists():
            return Config()
        path = candidate

    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    return Config(data)


def merge_cli_config(cli_fail_on: str, cli_checks: str | None, cli_skip: str | None,
                     config: Config) -> tuple[str, list[str] | None, list[str] | None]:
    """Merge CLI arguments with config file overrides.

    CLI flags take priority; the config file fills in defaults.
    """
    # fail_on: CLI overrides config
    fail_on = cli_fail_on if cli_fail_on != "never" else config.fail_on

    # --checks: CLI overrides config completely
    checked_ids: list[str] | None = None
    if cli_checks:
        checked_ids = [c.strip() for c in cli_checks.split(",")]

    # --skip: merge with config's disable list
    skipped_ids: list[str] | None = None
    skip_set: set[str] = set(config.disable)
    if cli_skip:
        skip_set.update(c.strip() for c in cli_skip.split(","))
    if skip_set:
        skipped_ids = sorted(skip_set)

    return fail_on, checked_ids, skipped_ids
