"""Git operation tools."""

import subprocess
from typing import Any

from .base import ToolResult


# Allowed git commands for security
ALLOWED_GIT_COMMANDS = {
    "status", "log", "diff", "branch", "checkout", "commit",
    "push", "pull", "fetch", "merge", "add", "reset", "stash",
    "show", "remote", "init", "clone", "tag", "describe", "rev-parse"
}


class GitTools:
    """Container for git tools."""

    def __init__(self, workspace: str):
        self.workspace = workspace

    def git_command(self, action: dict[str, Any]) -> ToolResult:
        """Execute git commands."""
        git_args = action.get("git_args")

        if not git_args:
            return ToolResult.err("Missing git_args", "Error: Missing git_args")

        args = git_args.strip().split()

        if args and args[0] not in ALLOWED_GIT_COMMANDS:
            return ToolResult.err(
                f"Git command '{args[0]}' not allowed",
                f"Error: Git command '{args[0]}' not allowed"
            )

        try:
            result = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                cwd=self.workspace,
                timeout=30,
            )
            output = result.stdout + result.stderr
            if result.returncode == 0:
                return ToolResult.ok(output[:3000] or "Git command executed successfully")
            return ToolResult.err(
                f"Git error (exit {result.returncode})",
                f"Git error (exit {result.returncode}):\n{output[:2000]}"
            )
        except Exception as e:
            return ToolResult.err(f"Error executing git: {str(e)}", f"Error executing git: {str(e)}")


def get_git_tool_handlers(workspace: str) -> dict[str, callable]:
    """Get git tool handlers for ToolExecutor."""
    tools = GitTools(workspace)
    return {
        "git": tools.git_command,
    }
