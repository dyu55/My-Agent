import os
from pathlib import Path

DB_PATH = Path(os.getenv("SNIPPET_DB_PATH", Path.home() / ".snippets.db"))