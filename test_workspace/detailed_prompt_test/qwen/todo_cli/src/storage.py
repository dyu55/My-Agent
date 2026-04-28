from __future__ import annotations
import json
from pathlib import Path
from typing import List
from src.models import TodoItem

STORAGE_PATH: Path = Path.home() / ".todos.json"

def load_todos() -> List[TodoItem]:
    if not STORAGE_PATH.exists():
        return []
    with open(STORAGE_PATH, "r", encoding="utf-8") as file:
        data: list[dict[str, Any]] = json.load(file)
    return [TodoItem(**item) for item in data]

def save_todos(todos: List[TodoItem]) -> None:
    with open(STORAGE_PATH, "w", encoding="utf-8") as file:
        json.dump([item.__dict__ for item in todos], file, indent=2)