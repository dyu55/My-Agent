"""Base classes for modular tool system."""

import json
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

    @classmethod
    def from_result(cls, result: Any, stringify: bool = True) -> "ToolResult":
        """
        Create a ToolResult from a result object.

        Args:
            result: The result object (TestResult, QualityResult, etc.)
            stringify: If True, convert result to string; if False, use as output

        Returns:
            ToolResult with result data
        """
        if hasattr(result, "is_success"):
            # Result has success check method
            success = result.is_success
        elif hasattr(result, "passed"):
            # TestResult
            success = result.passed > 0
        elif hasattr(result, "score"):
            # QualityResult
            success = result.score >= 70
        else:
            success = True

        if stringify:
            output = cls._stringify_result(result)
        else:
            output = str(result)

        return cls(success=success, output=output)

    @staticmethod
    def _stringify_result(result: Any) -> str:
        """Convert a result object to a readable string."""
        if hasattr(result, "to_dict"):
            return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
        elif hasattr(result, "__dict__"):
            return json.dumps(result.__dict__, indent=2, ensure_ascii=False, default=str)
        else:
            return str(result)


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
