"""File operation tools."""

import json
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolResult


class FileTools:
    """Container for file operation tools."""

    def __init__(self, workspace: str):
        self.workspace = workspace

    def _resolve_path(self, path: str | None) -> str:
        """Resolve a path to be within the workspace."""
        if not path:
            return self.workspace

        target = Path(self.workspace) / path
        resolved = target.resolve()

        if not str(resolved).startswith(str(Path(self.workspace).resolve())):
            return "Error: Path escapes workspace"
        return str(resolved)

    def write_file(self, action: dict[str, Any]) -> ToolResult:
        """Write content to a file."""
        path = action.get("path")
        content = action.get("content")

        if not path or content is None:
            return ToolResult.err("Missing path or content", "Error: Missing path or content")

        if path.lower() in {".env", ".git", "config.py"}:
            return ToolResult.err("Permission denied", "Error: Permission denied")

        try:
            target = self._resolve_path(path)
            if target.startswith("Error:"):
                return ToolResult.err(target, f"Error: {target}")

            Path(target).parent.mkdir(parents=True, exist_ok=True)
            Path(target).write_text(content, encoding="utf-8")
            return ToolResult.ok(f"Success: File {path} written")
        except Exception as e:
            return ToolResult.err(f"Error writing file: {str(e)}", f"Error writing file: {str(e)}")

    def edit_file(self, action: dict[str, Any]) -> ToolResult:
        """Edit a file by replacing old_text with new_text."""
        path = action.get("path")
        old_text = action.get("old_text")
        content = action.get("content", "")

        if not path or not old_text:
            return ToolResult.err("Missing path or old_text", "Error: Missing path or old_text")

        try:
            target = self._resolve_path(path)
            if target.startswith("Error:"):
                return ToolResult.err(target, f"Error: {target}")

            file_content = Path(target).read_text(encoding="utf-8")
            if old_text not in file_content:
                return ToolResult.err(
                    "old_text not found in file",
                    "Error: old_text not found in file"
                )

            new_content = file_content.replace(old_text, content, 1)
            Path(target).write_text(new_content, encoding="utf-8")
            return ToolResult.ok(f"Success: File {path} edited")
        except FileNotFoundError:
            return ToolResult.err(f"File not found: {path}", f"Error: File not found: {path}")
        except Exception as e:
            return ToolResult.err(f"Error editing file: {str(e)}", f"Error editing file: {str(e)}")

    def read_file(self, action: dict[str, Any]) -> ToolResult:
        """Read file content with line numbers."""
        path = action.get("path")
        start = action.get("start", 1)
        end = action.get("end", 100)

        if not path:
            return ToolResult.err("Missing path", "Error: Missing path")

        try:
            target = self._resolve_path(path)
            if target.startswith("Error:"):
                return ToolResult.err(target, f"Error: {target}")

            lines = Path(target).read_text(encoding="utf-8").splitlines()
            subset = lines[start - 1:end]
            numbered = "\n".join(
                f"{i + start}: {line}" for i, line in enumerate(subset)
            )
            return ToolResult.ok(f"Content of {path}:\n{numbered}")
        except FileNotFoundError:
            return ToolResult.err(f"File not found: {path}", f"Error: File not found: {path}")
        except Exception as e:
            return ToolResult.err(f"Error reading file: {str(e)}", f"Error reading file: {str(e)}")

    def mkdir(self, action: dict[str, Any]) -> ToolResult:
        """Create a directory."""
        path = action.get("path")

        if not path:
            return ToolResult.err("Missing path", "Error: Missing path")

        try:
            target = Path(self._resolve_path(path))
            target.mkdir(parents=True, exist_ok=True)
            return ToolResult.ok("Success: Directory created")
        except Exception as e:
            return ToolResult.err(f"Error creating directory: {str(e)}", f"Error creating directory: {str(e)}")

    def list_directory(self, action: dict[str, Any]) -> ToolResult:
        """List directory contents."""
        path = action.get("path", ".")

        try:
            target = Path(self._resolve_path(path))
            if not target.exists():
                return ToolResult.err(f"Directory does not exist", f"Error: Directory {path} does not exist")

            entries = []
            for item in sorted(target.iterdir()):
                prefix = "[DIR]" if item.is_dir() else "[FILE]"
                entries.append(f"{prefix} {item.name}")
            return ToolResult.ok("\n".join(entries) if entries else "Directory is empty")
        except Exception as e:
            return ToolResult.err(f"Error listing directory: {str(e)}", f"Error listing directory: {str(e)}")

    def create_files(self, action: dict[str, Any]) -> ToolResult:
        """Create multiple files at once."""
        files = action.get("files", [])

        if not files:
            return ToolResult.err("No files specified", "Error: No files specified")

        results = []
        for spec in files:
            path = spec.get("path")
            content = spec.get("content", "")

            if not path:
                results.append(f"Error: Missing path in {spec}")
                continue

            try:
                file_path = Path(self.workspace) / path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                results.append(f"Created: {path}")
            except Exception as e:
                results.append(f"Failed to create {path}: {str(e)}")

        return ToolResult.ok("\n".join(results))


def get_file_tool_handlers(workspace: str) -> dict[str, callable]:
    """Get file tool handlers for ToolExecutor."""
    tools = FileTools(workspace)
    return {
        "write": tools.write_file,
        "edit": tools.edit_file,
        "read": tools.read_file,
        "mkdir": tools.mkdir,
        "list_dir": tools.list_directory,
        "list_files": tools.list_directory,
        "create_file": tools.create_files,
    }
