"""Execute policy-checked actions through the modular tool registry."""

import ast
from dataclasses import asdict
from pathlib import Path
from time import perf_counter
from typing import Any

from .actions import Action as Action
from .actions import ExecutionResult as ExecutionResult
from .actions import ExecutionStatus as ExecutionStatus
from .tool_policy import ToolPolicy
from .tools.base import ToolResult
from .tools.registry import ToolRegistry


class ToolExecutor:
    """Coordinate dispatch and diagnostics; tool modules own all side effects."""

    def __init__(
        self,
        workspace_path: str,
        tool_policy: dict[str, Any] | ToolPolicy | None = None,
        *,
        registry: ToolRegistry | None = None,
    ):
        self.workspace = workspace_path
        self.action_history: list[ExecutionResult] = []
        self.tool_policy = ToolPolicy.from_config(tool_policy)
        self.registry = registry or ToolRegistry(workspace_path)

    def execute_action(self, action: Action) -> ExecutionResult:
        """Preserve structured success/error signals and record every attempt."""
        start = perf_counter()
        try:
            tool_result = self._dispatch_action(action)
            output = tool_result.output
            if tool_result.success:
                output += self._syntax_diagnostic(action)
            elif not output:
                output = f"Error: {tool_result.error or 'Tool execution failed'}"
            result = ExecutionResult(
                status=ExecutionStatus.SUCCESS
                if tool_result.success
                else ExecutionStatus.FAILURE,
                command=action.command,
                output=output,
                error=tool_result.error if not tool_result.success else None,
                execution_time=perf_counter() - start,
            )
        except Exception as exc:
            result = ExecutionResult(
                status=ExecutionStatus.FAILURE,
                command=action.command,
                output="",
                error=str(exc),
                execution_time=perf_counter() - start,
            )
        self.action_history.append(result)
        return result

    def _dispatch_action(self, action: Action) -> ToolResult:
        payload = asdict(action)
        payload.pop("command")
        handler = self.registry.get(action.command)
        if handler is None:
            return ToolResult.err(f"Unknown command '{action.command}'")
        decision = self.tool_policy.evaluate(action.command, payload)
        if not decision.allows_execution:
            return ToolResult.err(decision.reason or "Blocked by tool policy")
        return handler(payload)

    def _syntax_diagnostic(self, action: Action) -> str:
        if action.command not in {"write", "edit"} or not action.path:
            return ""
        if not action.path.endswith(".py"):
            return ""
        resolved = self.registry.file_tools._resolve_path(action.path)
        if resolved.startswith("Error:"):
            return ""
        target = Path(resolved)
        try:
            ast.parse(target.read_text(encoding="utf-8"), filename=str(target))
        except SyntaxError as exc:
            return (
                f"\n[Static Diagnostic Warning]: SyntaxError in {action.path} "
                f"(line {exc.lineno}): {exc.msg}"
            )
        return ""

    def get_execution_summary(self) -> str:
        if not self.action_history:
            return "No actions executed yet"
        lines = ["## Execution History\n"]
        for index, result in enumerate(self.action_history[-10:], 1):
            icon = "✅" if result.is_success() else "❌"
            lines.append(
                f"{index}. {icon} {result.command} ({result.execution_time:.2f}s)"
            )
        return "\n".join(lines)
