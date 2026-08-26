"""Tests for Fuzzy Search-and-Replace in FileTools."""

from agent.tools.file_tools import FileTools


def test_fuzzy_replace_exact():
    content = "def hello():\n    return 'world'\n"
    old = "return 'world'"
    new = "return 'universe'"
    result = FileTools._fuzzy_replace(content, old, new)
    assert result == "def hello():\n    return 'universe'\n"


def test_fuzzy_replace_line_endings():
    content = "line1\r\nline2\r\nline3\r\n"
    old = "line2\n"
    new = "new_line2\n"
    result = FileTools._fuzzy_replace(content, old, new)
    assert "new_line2" in result


def test_fuzzy_replace_whitespace_drift():
    content = """class App:
    def run(self):
        print("Starting")
        self.init_db()
        print("Ready")
"""
    # Model returns slightly different indentation / whitespace
    old = """  def run(self):
      print("Starting")
      self.init_db()"""

    new = """    def run(self):
        print("Booting v2")
        self.init_db()"""

    result = FileTools._fuzzy_replace(content, old, new)
    assert result is not None
    assert 'print("Booting v2")' in result
    assert 'print("Ready")' in result


def test_fuzzy_replace_difflib_similarity():
    content = """def process_data(items):
    for item in items:
        if item.is_valid():
            save_to_db(item)
    return True
"""
    # Slightly altered comments or small drift
    old = """for item in items:
    if item.is_valid():
        save_to_db(item)"""

    new = """for item in items:
    if item.is_valid() and not item.is_deleted():
        save_to_db(item)"""

    result = FileTools._fuzzy_replace(content, old, new)
    assert result is not None
    assert "not item.is_deleted()" in result
