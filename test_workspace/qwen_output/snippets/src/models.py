from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
 @dataclass
class Snippet:
    id: Optional[int] = None
    name: str = ""
    language: str = ""
    content: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
 def to_dict(self) -> dict[str, Any]:
        return { "id": self.id,
            "name": self.name, "language": self.language,
            "content": self.content, "description": self.description,
            "tags": self.tags, "created_at": self.created_at.isoformat() if self.created_at el
else None, "updated_at": self.updated_at.isoformat() if self.updated_at el
else None, }