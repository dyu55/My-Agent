from __future__ import annotations

import pathlib
import pytest
from core.text_stats import count_text, TextStats


@pytest.fixture
def sample_file(tmp_path: pathlib.Path) -> pathlib.Path:
    file = tmp_path / "test.txt"
    file.write_text("Hello World\nThis is a test.\n", encoding="utf-8")
    return file


def test_count_text_normal(sample_file: pathlib.Path) -> None:
    stats = count_text(sample_file)
    assert isinstance(stats, TextStats)
    assert stats.lines == 2
    assert stats.words == 6
    assert stats.characters == 27
    assert stats.byte_size == 27


def test_count_text_empty(tmp_path: pathlib.Path) -> None:
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")
    stats = count_text(empty_file)
    assert stats.lines == 0
    assert stats.words == 0
    assert stats.characters == 0
    assert stats.byte_size == 0


def test_count_text_unicode(tmp_path: pathlib.Path) -> None:
    uni_file = tmp_path / "unicode.txt"
    content = "你好\n世界\n"
    uni_file.write_text(content, encoding="utf-8")
    stats = count_text(uni_file)
    assert stats.lines == 2
    assert stats.words == 2
    assert stats.characters == len(content)
    assert stats.byte_size == len(content.encode("utf-8"))


def test_count_text_returns_frozen_dataclass(tmp_path: pathlib.Path) -> None:
    file = tmp_path / "data.txt"
    file.write_text("test", encoding="utf-8")
    stats = count_text(file)
    assert hasattr(stats, "__dataclass_fields__")
    with pytest.raises(Exception):
        stats.lines = 0