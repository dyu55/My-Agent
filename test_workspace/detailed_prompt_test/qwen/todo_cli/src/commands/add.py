from __future__ import annotations
from typing import List
from src.models import TodoItem
from src import storage

def add(title: str, priority: str, due_date: str | None = None) -> TodoItem:
    todos: List[TodoItem] = storage.load_todos()
    new_todo: TodoItem = TodoItem(title=title, priority=priority, due_date=due_date)
    todos.append(new_todo)
    storage.save_todos(todos)
    return new_todo