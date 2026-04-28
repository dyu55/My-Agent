import pytest
from pathlib import Path
from disk_analyzer.core import DiskAnalyzer

@pytest.fixture
def analyzer():
    return DiskAnalyzer()

@pytest.fixture
def sample_dir(tmp_path):
    """Creates a temporary directory structure for testing."""
    # Create a file 1KB
    file1 = tmp_path / "file1.bin"
    file1.write_bytes(b"\x00" * 1024)
    
    # Create a subdirectory with a file 2KB
    sub = tmp_path / "sub"
    sub.mkdir()
    file2 = sub / "file2.bin"
    file2.write_bytes(b"\x00" * 2048)
    
    # Create another file 500B
    file3 = tmp_path / "file3.bin"
    file3.write_bytes(b"\x00" * 500)
    
    return tmp_path

def test_format_size(analyzer):
    assert analyzer.format_size(0) == "0B"
    assert analyzer.format_size(1024) == "1.00 KB"
    assert analyzer.format_size(1024 * 1024) == "1.00 MB"
    assert analyzer.format_size(1024**3 * 1.5) == "1.50 GB"

def test_get_size(analyzer, sample_dir):
    # 1024 + 2048 + 500 = 3572
    expected_size = 1024 + 2048 + 500
    assert analyzer.get_size(sample_dir) == expected_size

def test_list_top_items(analyzer, sample_dir):
    # The 'sub' directory should be the largest (2048 bytes)
    # Then 'file1.bin' (1024 bytes)
    # Then 'file3.bin' (500 bytes)
    top_items = list(analyzer.list_top_items(sample_dir, limit=2))
    
    assert len(top_items) == 2
    assert top_items[0][0].name == "sub"
    assert top_items[0][1] == 2048
    assert top_items[1][0].name == "file1.bin"
    assert top_items[1][1] == 1024

def test_get_size_file(analyzer, sample_dir):
    file_path = sample_dir / "file1.bin"
    assert analyzer.get_size(file_path) == 1024