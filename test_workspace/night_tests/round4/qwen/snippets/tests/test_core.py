"""Unit tests for number_analyzer.core module."""

import pytest
import json
from number_analyzer.core import calculate_stats, format_result


def test_calculate_stats_valid() -> None:
    """Test statistics calculation with valid input."""
    numbers = [1.0, 2.0, 3.0, 4.0, 5.0]
    stats = calculate_stats(numbers)
    assert stats["sum"] == 15.0
    assert stats["mean"] == 3.0
    assert stats["min"] == 1.0
    assert stats["max"] == 5.0
    assert stats["count"] == 5


def test_calculate_stats_empty() -> None:
    """Test that empty list raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        calculate_stats([])


def test_format_result_text() -> None:
    """Test text formatting output."""
    stats = {"sum": 10.0, "mean": 2.0}
    result = format_result(stats, "text")
    assert "sum: 10.00" in result
    assert "mean: 2.00" in result


def test_format_result_json() -> None:
    """Test JSON formatting output."""
    stats = {"sum": 10.0, "count": 5}
    result = format_result(stats, "json")
    parsed = json.loads(result)
    assert parsed["sum"] == 10.0
    assert parsed["count"] == 5


def test_format_result_csv() -> None:
    """Test CSV formatting output."""
    stats = {"sum": 10.0, "mean": 2.0}
    result = format_result(stats, "csv")
    assert result.startswith("sum,mean")
    assert "10.0,2.0" in result