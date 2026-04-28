from __future__ import annotations
from src.models import TodoItem
from src import storage

def mark_done(todo_id: str) -> TodoItem | None:
    todos = storage.load_todos()
    for todo in todos:
        if todo.id == todo_id:
            todo.done = True
            storage.save_todos(todos)
            return todo
    return None