import pytest
from pathlib import Path
from src.processor import replace_text_in_file, replace_text_in_dir

def test_replace_text_in_file(tmp_path: Path):
    # Setup
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello World! Hello Python!", encoding="utf-8")
    
    # Execution
    count = replace_text_in_file(test_file, "Hello", "Hi")
    
    # Verification
    assert count == 2
    assert test_file.read_text(encoding="utf-8") == "Hi World! Hi Python!"

def test_replace_text_in_dir_recursive(tmp_path: Path):
    # Setup directory structure
    dir_a = tmp_path / "dir_a"
    dir_a.mkdir()
    file1 = dir_a / "f1.txt"
    file1.write_text("apple orange", encoding="utf-8")
    
    dir_b = tmp_path / "dir_b"
    dir_b.mkdir()
    file2 = dir_b / "f2.txt"
    file2.write_text("apple banana", encoding="utf-8")
    
    file3 = tmp_path / "f3.log"
    file3.write_text("apple grape", encoding="utf-8")

    # Execution: Replace apple -> pear only in .txt files
    result = replace_text_in_dir(
        root_dir=tmp_path,
        search_str="apple",
        replace_str="pear",
        extensions=[".txt"]
    )

    # Verification
    assert result.files_modified == 2
    assert result.total_replacements == 2
    assert file1.read_text() == "pear orange"
    assert file2.read_text() == "pear banana"
    assert file3.read_text() == "apple grape"  # Should remain unchanged (.log)

def test_no_match(tmp_path: Path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("nothing here", encoding="utf-8")
    
    result = replace_text_in_dir(tmp_path, "missing", "found")
    assert result.files_modified == 0
    assert result.total_replacements == 0