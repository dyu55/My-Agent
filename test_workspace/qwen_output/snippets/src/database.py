import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from src.models import Snippet
from src.utils.config import get_db_path
 class SnippetDB:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or get_db_path()
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()
 def _init_db(self) -> None:
        cursor = self.conn.cursor()
        cursor.execute(""" CREATE TABLE IF NOT EXISTS snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
                language TEXT NOT NULL, content TEXT NOT NULL,
                description TEXT DEFAULT '', tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            )
        """) self.conn.commit()
 def _row_to_snippet(self, row: tuple) -> Snippet:
        return Snippet( id=row[0],
            name=row[1], language=row[2],
            content=row[3], description=row[4],
            tags=json.loads(row[5]), created_at=datetime.fromisoformat(row[6]),
            updated_at=datetime.fromisoformat(row[7])
        )
 def add(self, snippet: Snippet) -> Snippet:
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(""" INSERT INTO snippets (name, language, content, description, tag
tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (snippet.name, snippet.language, snippet.content, snippet.desc snippet.description,
              json.dumps(snippet.tags), now, now))
        self.conn.commit()
        snippet.id = cursor.lastrowid
        snippet.created_at = datetime.fromisoformat(now)
        snippet.updated_at = datetime.fromisoformat(now)
        return snippet
 def list_all(self) -> List[Snippet]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM snippets ORDER BY updated_at DESC")
        return [self._row_to_snippet(row) for row in cursor.fetchall()]
 def get(self, snippet_id: int) -> Optional[Snippet]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM snippets WHERE id = ?", (snippet_id,)
(snippet_id,))
        row = cursor.fetchone()
        return self._row_to_snippet(row) if row else None
 def update(self, snippet: Snippet) -> Optional[Snippet]:
        cursor = self.conn.cursor()
        cursor.execute(""" UPDATE snippets SET name=?, language=?, content=?, description=
description=?, tags=?, updated_at=?
            WHERE id=?
        """, (snippet.name, snippet.language, snippet.content, snippet.desc snippet.description,
              json.dumps(snippet.tags), datetime.now().isoformat(), snippet
snippet.id))
        self.conn.commit()
        return self.get(snippet.id)
 def delete(self, snippet_id: int) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))
        self.conn.commit()
        return cursor.rowcount > 0
 def search(self, query: str) -> List[Snippet]:
        cursor = self.conn.cursor()
        like_pattern = f"%{query}%"
        cursor.execute(""" SELECT * FROM snippets
            WHERE name LIKE ? OR language LIKE ? OR content LIKE ? OR descr
description LIKE ?
            ORDER BY updated_at DESC
        """, (like_pattern, like_pattern, like_pattern, like_pattern)) return [self._row_to_snippet(row) for row in cursor.fetchall()]
 def close(self) -> None:
        self.conn.close()