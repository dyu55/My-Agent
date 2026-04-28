from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class Snippet:
    name: str
    language: str
    content: str
    description: str
    tags: List[str] = field(default_factory=list)
    id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_tuple(self):
        return (self.name, self.language, self.content, self.description, self.tags)