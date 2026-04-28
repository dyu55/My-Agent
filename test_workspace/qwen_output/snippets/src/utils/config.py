from pathlib import Path
 DEFAULT_DB_PATH = Path.home() / ".snippet_manager" / "snippets.db"
 def get_db_path() -> str:
    return str(DEFAULT_DB_PATH)