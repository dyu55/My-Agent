import pytest
from pathlib import Path
from py_replace.core import ReplaceEngine

def test_replace_in_content():
    """Test the string replacement logic without file I/O."""
    engine = ReplaceEngine("foo", "bar")
    content = "the foo jumps over the foo"
    new_content, count = engine.replace_in_content(content)
    
    assert count == 2
    assert new_content == "the bar jumps over the bar"

def test_replace_in_content_no_match():
    """Test scenario where no matches are found."""
    engine = ReplaceEngine("baz", "bar")
    content = "the foo jumps over the foo"
    new_content, count = engine.replace_in_content(content)
    
    assert count == 0
    assert new_content == content

def test_process_file(tmp_path: Path):
    """Test actual file processing using a pytest temporary directory."""
    # Setup: Create a temporary file
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world\nhello python", encoding="utf-8")
    
    engine = ReplaceEngine("hello", "hi")
    
    # Test actual replacement
    count = engine.process_file(test_file, dry_run=False)
    assert count == 2
    assert test_file.read_text(encoding="utf-8") == "hi world\nhi python"

def test_process_file_dry_run(tmp_path: Path):
    """Test that dry_run does not modify the file."""
    test_file = tmp_path / "test_dry.txt"
    original_text = "keep me as I am"
    test_file.write_text(original_text, encoding="utf-8")
    
    engine = ReplaceEngine("keep", "change")
    count = engine.process_file(test_file, dry_run=True)
    
    assert count == 1
    assert test_file.read_text(encoding="utf-8") == original_text

def test_process_file_not_found():
    """Test that FileNotFoundError is raised for missing files."""
    engine = ReplaceEngine("a", "b")
    with pytest.raises(FileNotFoundError):
        engine.process_file(Path("non_existent_file_12345.txt"))