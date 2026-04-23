"""Tool Executor - Executes actions using available tools.

This module provides the ToolExecutor class that dispatches actions
to appropriate tool handlers. It uses modular tool implementations
from the agent/tools/ package.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from .tools.file_tools import FileTools, get_file_tool_handlers
from .tools.exec_tools import ExecTools, get_exec_tool_handlers
from .tools.search_tools import SearchTools, get_search_tool_handlers
from .tools.git_tools import GitTools, get_git_tool_handlers

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    requests = None


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


class ToolExecutor:
    """
    Responsible for executing actions using available tools.

    Phase: Act

    Uses modular tool implementations from agent/tools/ package.
    """

    def __init__(self, workspace_path: str):
        self.workspace = workspace_path
        self.action_history: list[ExecutionResult] = []

        # Initialize modular tools
        self._file_tools = FileTools(workspace_path)
        self._exec_tools = ExecTools(workspace_path)
        self._search_tools = SearchTools(workspace_path)
        self._git_tools = GitTools(workspace_path)

    def execute_action(self, action: Action) -> ExecutionResult:
        """
        Execute a single action and return the result.

        Args:
            action: The action to execute

        Returns:
            ExecutionResult with status and output
        """
        import time

        start_time = time.time()

        try:
            result = self._dispatch_action(action)
            execution_time = time.time() - start_time

            return ExecutionResult(
                status=ExecutionStatus.SUCCESS if not result.startswith("Error")
                else ExecutionStatus.FAILURE,
                command=action.command,
                output=result,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                status=ExecutionStatus.FAILURE,
                command=action.command,
                output="",
                error=str(e),
                execution_time=execution_time,
            )

    def _dispatch_action(self, action: Action) -> str:
        """Dispatch action to the appropriate handler using modular tools."""
        # Convert Action to dict for tool handlers
        action_dict = {
            "path": action.path,
            "content": action.content,
            "script": action.script,
            "query": action.query,
            "url": action.url,
            "modules": action.modules,
            "packages": action.packages,
            "files": action.files,
            "old_text": action.old_text,
            "git_args": action.git_args,
            "start": action.start,
            "end": action.end,
        }

        # File tools
        file_handlers = {
            "write": lambda: self._file_tools.write_file(action_dict),
            "edit": lambda: self._file_tools.edit_file(action_dict),
            "read": lambda: self._file_tools.read_file(action_dict),
            "mkdir": lambda: self._file_tools.mkdir(action_dict),
            "list_dir": lambda: self._file_tools.list_directory(action_dict),
            "list_files": lambda: self._file_tools.list_directory(action_dict),
            "create_file": lambda: self._file_tools.create_files(action_dict),
        }

        # Execution tools
        exec_handlers = {
            "execute": lambda: self._exec_tools.execute_script(action_dict),
            "check_dependencies": lambda: self._exec_tools.check_dependencies(action_dict),
            "run_tests": lambda: self._exec_tools.run_tests(action_dict),
            "pip_install": lambda: self._exec_tools.pip_install(action_dict),
        }

        # Search tools
        search_handlers = {
            "search": lambda: self._search_tools.search_files(action_dict),
            "search_web": lambda: self._search_tools.search_web(action_dict),
            "web_fetch": lambda: self._search_tools.fetch_url(action_dict),
        }

        # Git tools
        git_handlers = {
            "git": lambda: self._git_tools.git_command(action_dict),
        }

        # Combine all handlers
        handlers = {}
        handlers.update(file_handlers)
        handlers.update(exec_handlers)
        handlers.update(search_handlers)
        handlers.update(git_handlers)
        handlers["debug"] = lambda: ToolResult.ok(f"[DEBUG]\n{action.content or 'No content'}\n[/DEBUG]")
        handlers["finish"] = lambda: ToolResult.ok("Task completed successfully")

        handler = handlers.get(action.command)
        if not handler:
            return f"Error: Unknown command '{action.command}'"

        result = handler()
        return result.output

    def _resolve_path(self, path: str | None) -> str:
        """Resolve a path to be within the workspace."""
        if not path:
            return self.workspace
        from pathlib import Path

        target = Path(self.workspace) / path
        resolved = target.resolve()

        # Security check: ensure path is within workspace
        if not str(resolved).startswith(str(Path(self.workspace).resolve())):
            return "Error: Path escapes workspace"
        return str(resolved)

    def _write_file(self, action: Action) -> str:
        """Write content to a file."""
        if not action.path or action.content is None:
            return "Error: Missing path or content"

        if action.path.lower() in {".env", ".git", "config.py"}:
            return "Error: Permission denied"

        try:
            target = self._resolve_path(action.path)
            if target.startswith("Error:"):
                return target

            Path(target).parent.mkdir(parents=True, exist_ok=True)
            Path(target).write_text(action.content, encoding="utf-8")
            return f"Success: File {action.path} written"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    def _edit_file(self, action: Action) -> str:
        """Edit a file by replacing old_text with new_text."""
        if not action.path or not action.old_text:
            return "Error: Missing path or old_text"

        try:
            target = self._resolve_path(action.path)
            if target.startswith("Error:"):
                return target

            content = Path(target).read_text(encoding="utf-8")
            if action.old_text not in content:
                return "Error: old_text not found in file"

            new_content = content.replace(action.old_text, action.content or "", 1)
            Path(target).write_text(new_content, encoding="utf-8")
            return f"Success: File {action.path} edited"
        except Exception as e:
            return f"Error editing file: {str(e)}"

    def _read_file(self, action: Action) -> str:
        """Read file content with line numbers."""
        if not action.path:
            return "Error: Missing path"

        try:
            target = self._resolve_path(action.path)
            if target.startswith("Error:"):
                return target

            lines = Path(target).read_text(encoding="utf-8").splitlines()
            subset = lines[action.start - 1 : action.end]
            numbered = "\n".join(
                f"{i + action.start}: {line}" for i, line in enumerate(subset)
            )
            return f"Content of {action.path}:\n{numbered}"
        except Exception as e:
            return f"Error reading file: {str(e)}"

    def _execute_script(self, action: Action) -> str:
        """Execute a shell command or script."""
        if not action.script:
            return "Error: Missing script"

        try:
            result = subprocess.run(
                action.script,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.workspace,
                timeout=30,
            )
            output = f"Exit Code: {result.returncode}\nStdout:\n{result.stdout}\nStderr:\n{result.stderr}"
            return output
        except subprocess.TimeoutExpired:
            return "Error: Command timed out after 30 seconds"
        except Exception as e:
            return f"Error executing script: {str(e)}"

    def _search_files(self, action: Action) -> str:
        """Search for text in files."""
        if not action.query:
            return "Error: Missing query"

        from pathlib import Path

        matches = []
        search_path = Path(self.workspace)
        lowered = action.query.lower()

        for file_path in search_path.rglob("*"):
            if file_path.is_file():
                try:
                    for line_no, line in enumerate(
                        file_path.read_text(encoding="utf-8").splitlines(), start=1
                    ):
                        if lowered in line.lower():
                            matches.append(
                                f"{file_path.relative_to(search_path)}:{line_no}: {line}"
                            )
                except Exception:
                    continue

        return "\n".join(matches) if matches else "No matches found"

    def _search_web(self, action: Action) -> str:
        """Search the web for information."""
        if not action.query:
            return "Error: Missing query"
        if requests is None:
            return "Error: requests library not installed"

        # Simple web search using DuckDuckGo API
        try:
            import urllib.parse

            encoded = urllib.parse.quote(action.query)
            url = f"https://api.duckduckgo.com/?format=json&q={encoded}&t=harness_agent"

            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("AbstractText"):
                    return f"Answer: {data['AbstractText']}"

                results = []
                for topic in data.get("RelatedTopics", [])[:5]:
                    if "Text" in topic:
                        results.append(f"- {topic['Text']}")

                if results:
                    return f"Search results for '{action.query}':\n" + "\n".join(results)
                return f"No results found for: {action.query}"
            return f"Error: Search failed with status {response.status_code}"
        except Exception as e:
            return f"Error during web search: {str(e)}"

    def _fetch_url(self, action: Action) -> str:
        """Fetch content from a URL."""
        if not action.url:
            return "Error: Missing URL"
        if requests is None:
            return "Error: requests library not installed"

        try:
            response = requests.get(
                action.url,
                timeout=15,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )
            if response.status_code != 200:
                return f"Error: Fetch failed with status {response.status_code}"

            # Try JSON first
            try:
                data = response.json()
                return f"=== JSON Response ===\n{json.dumps(data, ensure_ascii=False, indent=2)[:3000]}"
            except Exception:
                pass

            # Clean HTML
            text = re.sub(r"<[^>]+>", " ", response.text)
            text = re.sub(r"\s+", " ", text).strip()
            return f"=== Page Content ===\n{text[:3000]}"

        except Exception as e:
            return f"Error fetching page: {str(e)}"

    def _list_directory(self, action: Action) -> str:
        """List directory contents."""
        try:
            target = Path(self._resolve_path(action.path or "."))
            if not target.exists():
                return f"Error: Directory {action.path} does not exist"

            entries = []
            for item in sorted(target.iterdir()):
                prefix = "[DIR]" if item.is_dir() else "[FILE]"
                entries.append(f"{prefix} {item.name}")
            return "\n".join(entries) if entries else "Directory is empty"
        except Exception as e:
            return f"Error listing directory: {str(e)}"

    def _check_dependencies(self, action: Action) -> str:
        """Check if Python modules are available."""
        available = [
            m for m in action.modules if importlib.util.find_spec(m) is not None
        ]
        missing = [
            m for m in action.modules if importlib.util.find_spec(m) is None
        ]
        return json.dumps({"available": available, "missing": missing})

    def _run_tests(self, action: Action) -> str:
        """Run pytest tests."""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                cwd=self.workspace,
                timeout=60,
            )
            output = result.stdout + result.stderr
            if result.returncode == 0:
                return f"✅ All tests passed!\n{output[:2000]}"
            return f"❌ Tests failed (exit code: {result.returncode})\n{output[:2000]}"
        except FileNotFoundError:
            return "Error: pytest not found"
        except Exception as e:
            return f"Error running tests: {str(e)}"

    def _git_command(self, action: Action) -> str:
        """Execute git commands."""
        if not action.git_args:
            return "Error: Missing git_args"

        allowed = {
            "status", "log", "diff", "branch", "checkout", "commit",
            "push", "pull", "fetch", "merge", "add", "reset", "stash"
        }
        args = action.git_args.strip().split()

        if args and args[0] not in allowed:
            return f"Error: Git command '{args[0]}' not allowed"

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
                return output[:3000] or "Git command executed successfully"
            return f"Git error (exit {result.returncode}):\n{output[:2000]}"
        except Exception as e:
            return f"Error executing git: {str(e)}"

    def _mkdir(self, action: Action) -> str:
        """Create a directory."""
        if not action.path:
            return "Error: Missing path"

        try:
            target = Path(self._resolve_path(action.path))
            target.mkdir(parents=True, exist_ok=True)
            return f"Success: Directory created"
        except Exception as e:
            return f"Error creating directory: {str(e)}"

    def _pip_install(self, action: Action) -> str:
        """Install Python packages."""
        if not action.packages:
            return "Error: No packages specified"

        try:
            result = subprocess.run(
                ["pip", "install"] + action.packages,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                return f"✅ Successfully installed: {', '.join(action.packages)}"
            return f"❌ Installation failed:\n{result.stdout + result.stderr}"
        except Exception as e:
            return f"Error installing packages: {str(e)}"

    def _create_files(self, action: Action) -> str:
        """Create multiple files at once."""
        if not action.files:
            return "Error: No files specified"

        results = []
        for spec in action.files:
            path = spec.get("path")
            content = spec.get("content", "")

            if not path:
                results.append(f"Error: Missing path in {spec}")
                continue

            try:
                file_path = Path(self.workspace) / path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                results.append(f"✅ Created: {path}")
            except Exception as e:
                results.append(f"❌ Failed to create {path}: {str(e)}")

        return "\n".join(results)

    def _debug(self, action: Action) -> str:
        """Print debug information."""
        return f"[DEBUG]\n{action.content or 'No content'}\n[/DEBUG]"

    def _finish(self, action: Action) -> str:
        """Mark task as finished."""
        return "Task completed successfully"

    def get_execution_summary(self) -> str:
        """Get a summary of recent executions."""
        if not self.action_history:
            return "No actions executed yet"

        lines = ["## Execution History\n"]
        for i, result in enumerate(self.action_history[-10:], 1):
            status_icon = "✅" if result.is_success() else "❌"
            lines.append(
                f"{i}. {status_icon} {result.command} ({result.execution_time:.2f}s)"
            )
        return "\n".join(lines)
