"""Pytest configuration for MyAgent tests."""
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path so imports work
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def tmp_workspace(tmp_path):
    """Provide a temporary workspace directory."""
    return tmp_path


@pytest.fixture
def sample_python_file(tmp_path):
    """Create a sample Python file for testing."""
    file_path = tmp_path / "sample.py"
    file_path.write_text('def hello():\n    return "Hello, World!"\n')
    return file_path


@pytest.fixture
def sample_project(tmp_path):
    """Create a sample project structure for testing."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").touch()
    (tmp_path / "src" / "main.py").write_text('print("Hello")\n')
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text('def test_main(): pass\n')
    (tmp_path / "requirements.txt").write_text("requests>=2.0\n")
    return tmp_path
