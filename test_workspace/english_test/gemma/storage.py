import json
from pathlib import Path
from typing import List
from models import TodoItem

class TodoStorage:
    def __init__(self, filepath: str = "~/.todos.json"):
        self.filepath = Path(filepath).expanduser()

    def load(self) -> List[TodoItem]:
        if not self.filepath.exists():
            return []
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
                return [TodoItem.from_dict(item) for item in data]
        except (json.JSONDecodeError, IOError):
            return []

    def save(self, todos: List[TodoItem]) -> None:
        with open(self.filepath, 'w') as f:
            json.dump([item.to_dict() for item in todos], f, indent=4)