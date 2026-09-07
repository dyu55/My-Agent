"""Actions and execution results shared by the agent and tool layer."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class Action:
    """Represents an action to be executed."""

    command: str
    path: str | None = None
    content: str | None = None
    script: str | None = None
    query: str | None = None
    url: str | None = None
    modules: list[str] = field(default_factory=list)
    packages: list[str] = field(default_factory=list)
    files: list[dict[str, str]] = field(default_factory=list)
    old_text: str | None = None
    git_args: str | None = None
    start: int = 1
    end: int = 100


@dataclass
class ExecutionResult:
    """Result of executing an action."""

    status: ExecutionStatus
    command: str
    output: str
    error: str | None = None
    execution_time: float = 0.0

    def is_success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "command": self.command,
            "output": self.output[:1000],  # Truncate for storage
            "error": self.error,
            "execution_time": self.execution_time,
        }
