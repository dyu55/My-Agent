"""Base classes for modular tool system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    output: str
    error: str | None = None

    @classmethod
    def ok(cls, output: str) -> "ToolResult":
        """Create a successful result."""
        return cls(success=True, output=output)

    @classmethod
    def err(cls, error: str, output: str = "") -> "ToolResult":
        """Create an error result."""
        return cls(success=False, output=output, error=error)


class BaseTool(ABC):
    """Abstract base class for all tools."""

    # Tool name used for registration
    name: str = "base"

    # Description for the LLM to understand when to use this tool
    description: str = "Base tool"

    @abstractmethod
    def execute(self, action: dict[str, Any]) -> ToolResult:
        """
        Execute the tool with given action parameters.

        Args:
            action: Dictionary of action parameters

        Returns:
            ToolResult with success status and output
        """
        pass

    def validate(self, action: dict[str, Any]) -> tuple[bool, str]:
        """
        Validate action parameters before execution.

        Args:
            action: Dictionary of action parameters

        Returns:
            Tuple of (is_valid, error_message)
        """
        return True, ""
