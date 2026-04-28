from __future__ import annotations
from typing import List
from src.models import TodoItem
from src import storage

def list_todos() -> List[TodoItem]:
    return storage.load_todos()