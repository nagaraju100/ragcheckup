"""Unit tests for text utility functions."""

from __future__ import annotations

from ragcheckup.textutil import (
    tokenize,
    count_tokens,
    is_purely_numeric,
    label_density,
    numeric_ratio,
    line_break_ratio,
    sentence_count,
    is_sentence_start,
    looks_like_heading,
    DANGLING_STARTERS,
    ALLOWED_LOWERCASE,
    CONNECTIVES,
)


def test_tokenize() -> None:
    assert tokenize("hello world") == ["hello", "world"]
    assert tokenize("") == []


def test_count_tokens() -> None:
    num, total = count_tokens(["hello", "42", "world", "3.14"])
    assert total == 4
    assert num == 2


def test_is_purely_numeric() -> None:
    assert is_purely_numeric("123 456 789") is True
    assert is_purely_numeric("hello world") is False


def test_label_density() -> None:
    # Pure numbers with no labels
    assert label_density("123 456 789 321") < 0.3
    # Numbers next to words — the colon makes them non-alpha, but
    # we check strip("-,.") so "id" and "count" should match
    assert label_density("id 123 count 456") > 0.3


def test_numeric_ratio() -> None:
    assert numeric_ratio("123 456 789") > 0.8
    assert numeric_ratio("hello world") == 0.0


def test_line_break_ratio() -> None:
    assert line_break_ratio("a\n\nb\n\nc") > 0.3
    assert line_break_ratio("a\nb\nc") < 0.2


def test_sentence_count() -> None:
    assert sentence_count("Hello. World!") == 2
    assert sentence_count("no punctuation here") == 1


def test_is_sentence_start() -> None:
    assert is_sentence_start("Hello") is True
    assert is_sentence_start("hello") is False
    assert is_sentence_start("") is False


def test_looks_like_heading() -> None:
    assert looks_like_heading("# Introduction") is True
    assert looks_like_heading("ALL CAPS TEXT HERE") is True
    assert looks_like_heading("normal sentence") is False
    assert looks_like_heading("") is False


def test_dangling_starters_nonempty() -> None:
    assert len(DANGLING_STARTERS) > 0
    assert "this" in DANGLING_STARTERS


def test_allowed_lowercase_nonempty() -> None:
    assert len(ALLOWED_LOWERCASE) > 0
    assert "api" in ALLOWED_LOWERCASE


def test_connectives_nonempty() -> None:
    assert len(CONNECTIVES) > 0
    assert "and" in CONNECTIVES
    assert "however" in CONNECTIVES
