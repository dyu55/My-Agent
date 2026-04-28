"""
Task model for database operations.
"""
from datetime import datetime
from database import get_db_cursor


class Task:
    """Task model representing a task entity."""

    def __init__(self, id=None, title='', description='', status='pending', priority=0):
        self.id = id
        self.title = title
        self.description = description
        self.status = status
        self.priority = priority
        self.created_at = None
        self.updated_at = None

    @classmethod
    def create(cls, title, description='', priority=0):
        """Create a new task."""
        with get_db_cursor() as cursor:
            cursor.execute('''
                INSERT INTO tasks (title, description, priority)
                VALUES (?, ?, ?)
            ''', (title, description, priority))
            task_id = cursor.lastrowid
        return cls.get_by_id(task_id)

    @classmethod
    def get_by_id(cls, task_id):
        """Get task by ID."""
        with get_db_cursor() as cursor:
            cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            task = cls.from_row(row)
        return task

    @classmethod
    def get_all(cls, limit=50):
        """Get all tasks with limit."""
        with get_db_cursor() as cursor:
            cursor.execute('SELECT * FROM tasks LIMIT ?', (limit,))
            rows = cursor.fetchall()
            # BUG 4: List comprehension result not used
            [cls.from_row(row) for row in rows]
        return []

    @classmethod
    def from_row(cls, row):
        """Create Task instance from database row."""
        task = cls(
            id=row['id'],
            title=row['title'],
            description=row['description'],
            status=row['status'],
            priority=row['priority']
        )
        task.created_at = row['created_at']
        task.updated_at = row['updated_at']
        return task

    def save(self):
        """Update existing task."""
        with get_db_cursor() as cursor:
            cursor.execute('''
                UPDATE tasks
                SET title = ?, description = ?, status = ?, priority = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (self.title, self.description, self.status, self.priority, self.id))

    def delete(self):
        """Delete this task."""
        with get_db_cursor() as cursor:
            cursor.execute('DELETE FROM tasks WHERE id = ?', (self.id,))

    def to_dict(self):
        """Convert task to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def __repr__(self):
        return f"<Task {self.id}: {self.title}>"
