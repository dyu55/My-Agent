"""Result Reflector - Analyzes results and provides feedback for self-correction."""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ErrorCategory(Enum):
    SYNTAX_ERROR = "syntax_error"
    LOGIC_ERROR = "logic_error"
    TOOL_ERROR = "tool_error"
    MODEL_HALLUCINATION = "model_hallucination"
    DEPENDENCY_ERROR = "dependency_error"
    UNKNOWN = "unknown"


@dataclass
class Reflection:
    """Result of reflecting on execution results."""

    is_successful: bool
    error_category: ErrorCategory | None
    error_message: str | None
    suggestion: str | None
    should_retry: bool
    should_abandon: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_successful": self.is_successful,
            "error_category": self.error_category.value if self.error_category else None,
            "error_message": self.error_message,
            "suggestion": self.suggestion,
            "should_retry": self.should_retry,
            "should_abandon": self.should_abandon,
        }


class ResultReflector:
    """
    Responsible for analyzing execution results and determining next steps.

    Phase: Reflect

    Uses pattern matching and LLM analysis to:
    1. Classify errors
    2. Determine if retry is needed
    3. Provide suggestions for correction
    """

    # Error patterns for automatic classification
    SYNTAX_PATTERNS = [
        "SyntaxError",
        "IndentationError",
        "TabError",
        "unexpected EOF",
        "invalid syntax",
        "expected ':'",
    ]

    LOGIC_PATTERNS = [
        "AttributeError",
        "TypeError",
        "ValueError",
        "KeyError",
        "IndexError",
        "NoneType",
        "is not iterable",
        "unsupported operand",
    ]

    TOOL_PATTERNS = [
        "Permission denied",
        "File not found",
        "Directory not found",
        "Access denied",
        "Command not found",
        "not allowed",
    ]

    DEPENDENCY_PATTERNS = [
        "ModuleNotFoundError",
        "ImportError",
        "No module named",
        "Import cython",
        "pip install",
    ]

    def __init__(self, llm_client: Any | None = None):
        self.llm = llm_client
        self.reflection_history: list[Reflection] = []

    def reflect(
        self,
        action_command: str,
        execution_output: str,
        is_error: bool,
        context: str = "",
    ) -> Reflection:
        """
        Analyze execution result and provide reflection.

        Args:
            action_command: The command that was executed
            execution_output: The output from execution
            is_error: Whether the execution resulted in an error
            context: Additional context for analysis

        Returns:
            Reflection with classification and suggestions
        """
        if not is_error and not execution_output.startswith("Error"):
            reflection = Reflection(
                is_successful=True,
                error_category=None,
                error_message=None,
                suggestion=None,
                should_retry=False,
                should_abandon=False,
            )
            self.reflection_history.append(reflection)
            return reflection

        # Classify the error
        error_category = self._classify_error(execution_output)
        error_message = self._extract_error_message(execution_output)

        # Determine if we should retry
        should_retry, suggestion = self._determine_retry_strategy(
            error_category, error_message, action_command, context
        )

        reflection = Reflection(
            is_successful=False,
            error_category=error_category,
            error_message=error_message,
            suggestion=suggestion,
            should_retry=should_retry,
            should_abandon=not should_retry,
        )
        self.reflection_history.append(reflection)
        return reflection

    def _classify_error(self, output: str) -> ErrorCategory:
        """Classify an error based on patterns."""
        for pattern in self.SYNTAX_PATTERNS:
            if pattern in output:
                return ErrorCategory.SYNTAX_ERROR

        for pattern in self.LOGIC_PATTERNS:
            if pattern in output:
                return ErrorCategory.LOGIC_ERROR

        for pattern in self.TOOL_PATTERNS:
            if pattern in output:
                return ErrorCategory.TOOL_ERROR

        for pattern in self.DEPENDENCY_PATTERNS:
            if pattern in output:
                return ErrorCategory.DEPENDENCY_ERROR

        # Check for model-related issues
        if "json" in output.lower() and ("parse" in output.lower() or "decode" in output.lower()):
            return ErrorCategory.MODEL_HALLUCINATION

        return ErrorCategory.UNKNOWN

    def _extract_error_message(self, output: str) -> str:
        """Extract a clean error message from output."""
        lines = output.split("\n")
        error_lines = [l for l in lines if "Error" in l or "error" in l or "Exception" in l]
        return "\n".join(error_lines[:3]) if error_lines else output[:500]

    def _determine_retry_strategy(
        self,
        error_category: ErrorCategory,
        error_message: str,
        action_command: str,
        context: str,
    ) -> tuple[bool, str]:
        """
        Determine if we should retry and provide a suggestion.

        Returns:
            Tuple of (should_retry, suggestion)
        """
        suggestions = {
            ErrorCategory.SYNTAX_ERROR: (
                True,
                f"Fix the syntax error in the {action_command} operation. "
                "Common issues: missing colons, incorrect indentation, "
                "unmatched brackets or quotes.",
            ),
            ErrorCategory.LOGIC_ERROR: (
                True,
                f"The {action_command} operation produced unexpected results. "
                "Review the logic and check variable types and values.",
            ),
            ErrorCategory.TOOL_ERROR: (
                False,
                f"The {action_command} operation failed due to tool/permission issues. "
                "Try an alternative approach or skip this step.",
            ),
            ErrorCategory.DEPENDENCY_ERROR: (
                True,
                f"Missing dependencies detected. Run pip_install for required packages "
                f"before retrying the {action_command} operation.",
            ),
            ErrorCategory.MODEL_HALLUCINATION: (
                True,
                "The model produced invalid output. Retry with clearer instructions.",
            ),
            ErrorCategory.UNKNOWN: (
                True,
                f"Unexpected error in {action_command}. Try a different approach.",
            ),
        }

        return suggestions.get(
            error_category, (True, f"Unknown error in {action_command}")
        )

    def reflect_with_llm(
        self,
        action_command: str,
        execution_output: str,
        task_description: str,
        execution_history: list[str],
    ) -> Reflection:
        """
        Use LLM for more sophisticated reflection and analysis.

        This is called when automatic classification is insufficient.

        Args:
            action_command: The command that was executed
            execution_output: The output from execution
            task_description: The current task being worked on
            execution_history: Recent execution history for context

        Returns:
            Reflection with LLM-generated suggestions
        """
        if not self.llm:
            return self.reflect(action_command, execution_output, True)

        prompt = f"""You are a code debugging expert. Analyze this execution failure:

## Task
{task_description}

## Failed Operation
{action_command}

## Execution Output
{execution_output}

## Recent Operation History
{chr(10).join(execution_history[-5:])}

## Output Format
Return a JSON object:
{{
  "analysis": "In-depth analysis of the error",
  "error_type": "syntax/logic/tool/dependency/unknown",
  "suggestion": "Specific fix suggestion",
  "should_retry": true/false,
  "alternative_approach": "If retry is false, describe alternative approach"
}}
"""

        try:
            response = self.llm.chat(prompt)
            if isinstance(response, str):
                data = json.loads(response)
            else:
                data = response

            error_type_map = {
                "syntax": ErrorCategory.SYNTAX_ERROR,
                "logic": ErrorCategory.LOGIC_ERROR,
                "tool": ErrorCategory.TOOL_ERROR,
                "dependency": ErrorCategory.DEPENDENCY_ERROR,
            }

            return Reflection(
                is_successful=False,
                error_category=error_type_map.get(data.get("error_type", ""), ErrorCategory.UNKNOWN),
                error_message=data.get("analysis", ""),
                suggestion=data.get("suggestion", ""),
                should_retry=data.get("should_retry", True),
                should_abandon=not data.get("should_retry", True),
            )
        except Exception:
            # Fallback to pattern matching
            return self.reflect(action_command, execution_output, True)

    def get_reflection_summary(self) -> str:
        """Get a summary of recent reflections."""
        if not self.reflection_history:
            return "No reflections recorded yet"

        lines = ["## Reflection Summary\n"]
        successful = sum(1 for r in self.reflection_history if r.is_successful)
        failed = len(self.reflection_history) - successful

        lines.append(f"Total: {len(self.reflection_history)} | ✅ {successful} | ❌ {failed}\n")

        for i, r in enumerate(self.reflection_history[-5:], 1):
            status = "✅" if r.is_successful else "❌"
            category = r.error_category.value if r.error_category else "success"
            lines.append(f"{i}. {status} {category}")

        return "\n".join(lines)
