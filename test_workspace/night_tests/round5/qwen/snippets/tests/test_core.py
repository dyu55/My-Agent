from __future__ import annotations
import pytest
from word_counter.core import TextStats, count_text


def test_empty_input() -> None:
    result = count_text("")
    assert result == TextStats(lines=0, words=0, chars=0)


def test_whitespace_only() -> None:
    result = count_text("   \t  ")
    assert result.lines == 1
    assert result.words == 0
    assert result.chars == 7


def test_single_line_no_newline() -> None:
    result = count_text("Hello world")
    assert result == TextStats(lines=1, words=2, chars=11)


def test_multiple_lines() -> None:
    text = "Line one\nLine two\nLine three"
    result = count_text(text)
    assert result == TextStats(lines=3, words=6, chars=28)


def test_trailing_newline() -> None:
    text = "Single line\n"
    result = count_text(text)
    assert result == TextStats(lines=1, words=1, chars=11)


def test_multiple_trailing_newlines() -> None:
    text = "End\n\n\n"
    result = count_text(text)
    assert result == TextStats(lines=3, words=1, chars=6)


def test_mixed_spaces_and_tabs() -> None:
    text = "  word1 \t word2\t\tword3  "
    result = count_text(text)
    assert result == TextStats(lines=1, words=3, chars=21)