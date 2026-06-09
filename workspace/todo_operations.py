import sqlite3
from datetime import datetime
from models import TodoItem

class TodoOperations:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def add(self, title, description=''):
        if not title:
            raise ValueError("Title cannot be empty")
        self.cursor.execute('''
            INSERT INTO todos (title, description, completed, created_at)
            VALUES (?, ?, 0, ?)
        ''', (title, description, datetime.now()))
        self.conn.commit()
        return self.cursor.lastrowid

    def list(self):
        self.cursor.execute('SELECT * FROM todos ORDER BY created_at DESC')
        return [dict(zip([desc[0] for desc in self.cursor.description], row)) for row in self.cursor.fetchall()]

    def complete(self, todo_id):
        self.cursor.execute('''
            UPDATE todos SET completed = 1 WHERE id = ?
        ''', (todo_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete(self, todo_id):
        self.cursor.execute('DELETE FROM todos WHERE id = ?', (todo_id,))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def close(self):
        self.conn.close()