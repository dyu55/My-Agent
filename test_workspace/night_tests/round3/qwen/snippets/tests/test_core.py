import pytest
from pathlib import Path
from core import count_text, TextMetrics


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    """Create a temporary file with deterministic content."""
    content = "Hello world\nThis is a test file.\nThird line."
    target = tmp_path / "sample.txt"
    target.write_text(content, encoding="utf-8")
    return target


def test_count_valid_file(sample_file: Path) -> None:
    """Verify correct counting metrics on a valid file."""
    result = count_text(sample_file)
    assert isinstance(result, TextMetrics)

    content = sample_file.read_text(encoding="utf-8")
    assert result.lines == len(content.splitlines())
    assert result.words == len(content.split())
    assert result.characters == len(content)


def test_count_missing_file(tmp_path: Path) -> None:
    """Ensure FileNotFoundError is raised for non-existent paths."""
    with pytest.raises(FileNotFoundError, match="File not found"):
        count_text(tmp_path / "nonexistent.txt")


def test_count_empty_file(tmp_path: Path) -> None:
    """Verify metrics for an empty file."""
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    result = count_text(empty)
    assert result == TextMetrics(lines=0, words=0, characters=0)