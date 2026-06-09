from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class TodoItem:
    id: int
    title: str
    description: Optional[str] = None
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)