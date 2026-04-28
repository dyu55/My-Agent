from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class TodoItem:
    id: int
    task: str
    priority: str = "Medium"
    due_date: Optional[str] = None
    completed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'TodoItem':
        return cls(**data)