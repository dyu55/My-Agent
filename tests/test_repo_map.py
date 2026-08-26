"""Tests for AST-based RepoMap."""

import tempfile
from pathlib import Path
from agent.tools.repo_map import RepoMap


def test_repo_map_extraction():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        sample_file = tmp_path / "module_a.py"
        sample_file.write_text("""\"\"\"Sample module docstring.\"\"\"

class UserService:
    \"\"\"Handles user lifecycle.\"\"\"
    def __init__(self, db_conn):
        self.db = db_conn

    def create_user(self, name: str, email: str) -> bool:
        \"\"\"Create a new user.\"\"\"
        return True

def standalone_helper(x: int) -> str:
    \"\"\"Helper function.\"\"\"
    return str(x)
""", encoding="utf-8")

        repo_map = RepoMap(tmp_path, max_chars=2000)
        output = repo_map.generate_map()

        assert "UserService" in output
        assert "create_user" in output
        assert "standalone_helper" in output
        assert "module_a.py" in output
