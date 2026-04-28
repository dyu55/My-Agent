from __future__ import annotations
from src.models import TodoItem
from src import storage

def delete_todo(todo_id: str) -> TodoItem | None:
    todos = storage.load_todos()
    for index, todo in enumerate(todos):
        if todo.id == todo_id:
            removed: TodoItem = todos.pop(index)
            storage.save_todos(todos)
            return removed
    return None