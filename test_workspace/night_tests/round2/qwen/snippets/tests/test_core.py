import json
import pytest
from pathlib import Path
from text_stats.core import analyze_file, TextStats
from text_stats.cli import main

def test_analyze_file_basic(tmp_path: Path) -> None:
    """测试常规文件统计。"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello world\nThis is a test.")
    stats: TextStats = analyze_file(test_file)
    assert stats.lines == 2
    assert stats.words == 6
    assert stats.characters == 28

def test_analyze_file_empty(tmp_path: Path) -> None:
    """测试空文件统计。"""
    test_file = tmp_path / "empty.txt"
    test_file.write_text("")
    stats: TextStats = analyze_file(test_file)
    assert stats.lines == 0
    assert stats.words == 0
    assert stats.characters == 0

def test_analyze_file_not_found(tmp_path: Path) -> None:
    """测试文件不存在时的异常处理。"""
    missing_file = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError, match="File not found"):
        analyze_file(missing_file)

def test_cli_json_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """测试 CLI JSON 输出格式。"""
    test_file = tmp_path / "cli_test.txt"
    test_file.write_text("A B C\n")
    exit_code: int = main([str(test_file), "--format", "json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    output: dict[str, int] = json.loads(captured.out.strip())
    assert output == {"lines": 1, "words": 3, "characters": 6}

def test_cli_text_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """测试 CLI 默认文本输出格式。"""
    test_file = tmp_path / "cli_test2.txt"
    test_file.write_text("Line 1\nLine 2")
    exit_code: int = main([str(test_file)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Lines: 2" in captured.out
    assert "Words: 4" in captured.out
    assert "Characters: 13" in captured.out