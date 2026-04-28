import sqlite3
import json
from datetime import datetime
from typing import List, Optional
from src.models import Snippet
from src.utils.config import DB_PATH

class Database:
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snippets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    language TEXT NOT NULL,
                    content TEXT NOT NULL,
                    description TEXT,
                    tags TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def add_snippet(self, s: Snippet) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO snippets (name, language, content, description, tags) VALUES (?, ?, ?, ?, ?)",
                (s.name, s.language, s.content, s.description, json.dumps(s.tags))
            )
            return cursor.lastrowid

    def get_snippet(self, snippet_id: int) -> Optional[Snippet]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM snippets WHERE id = ?", (snippet_id,))
            row = cursor.fetchone()
            if row:
                return Snippet(
                    id=row[0], name=row[1], language=row[2], content=row[3],
                    description=row[4], tags=json.loads(row[5]), 
                    created_at=row[6], updated_at=row[7]
                )
            return None

    def list_snippets(self) -> List[Snippet]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT id, name, language, tags FROM snippets")
            return [Snippet(id=row[0], name=row[1], language=row[2], tags=json.loads(row[3]), 
                            content="", description="") for row in cursor.fetchall()]

    def update_snippet(self, snippet_id: int, updates: dict) -> bool:
        if not updates: return False
        fields = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values())
        values.append(snippet_id)
        
        if 'tags' in updates and isinstance(updates['tags'], list):
            # Handle JSON conversion for tags in updates
            idx = values.index(updates['tags'])
            values[idx] = json.dumps(updates['tags'])

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE snippets SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                values
            )
            return cursor.rowcount > 0

    def delete_snippet(self, snippet_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))
            return cursor.rowcount > 0

    def search_snippets(self, query: str) -> List[Snippet]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM snippets WHERE name LIKE ? OR description LIKE ? OR tags LIKE ?",
                (f"%{query}%", f"%{query}%", f"%{query}%")
            )
            return [Snippet(
                id=row[0], name=row[1], language=row[2], content=row[3],
                description=row[4], tags=json.loads(row[5]), 
                created_at=row[6], updated_at=row[7]
            ) for row in cursor.fetchall()]