from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4

@dataclass
class TodoItem:
    id: str = field(default_factory=lambda: uuid4().hex)
    title: str = ""
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: str | None = None
    done: bool = False