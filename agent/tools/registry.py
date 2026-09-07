"""Tool registration and lazy construction, with request-local arguments."""

from collections.abc import Callable
from importlib import import_module
from threading import RLock
from typing import Any

from .base import ToolResult
from .exec_tools import ExecTools
from .file_tools import FileTools
from .git_tools import GitTools
from .search_tools import SearchTools

ToolHandler = Callable[[dict[str, Any]], ToolResult]


class ToolRegistry:
    """Own tool instances and route explicit payloads without shared action state."""

    def __init__(self, workspace: str):
        self.workspace = workspace
        self.file_tools = FileTools(workspace)
        self.exec_tools = ExecTools(workspace)
        self.search_tools = SearchTools(workspace)
        self.git_tools = GitTools(workspace)
        self._instances: dict[str, Any] = {}
        self._lock = RLock()
        self._handlers: dict[str, ToolHandler] = {
            "write": self.file_tools.write_file,
            "edit": self.file_tools.edit_file,
            "read": self.file_tools.read_file,
            "mkdir": self.file_tools.mkdir,
            "list_dir": self.file_tools.list_directory,
            "list_files": self.file_tools.list_directory,
            "create_file": self.file_tools.create_files,
            "execute": self.exec_tools.execute_script,
            "check_dependencies": self.exec_tools.check_dependencies,
            "pip_install": self.exec_tools.pip_install,
            "search": self.search_tools.search_files,
            "search_web": self.search_tools.search_web,
            "web_fetch": self.search_tools.fetch_url,
            "git": self.git_tools.git_command,
            "debug": lambda action: ToolResult.ok(
                f"[DEBUG]\n{action.get('content') or 'No content'}\n[/DEBUG]"
            ),
            "finish": lambda action: ToolResult.ok("Task completed successfully"),
        }
        self.register(
            "discover_tests",
            self._lazy(
                "test_tools",
                "TestTools",
                "discover_tests",
                lambda value: ToolResult.ok("\n".join(value)),
            ),
        )
        self.register("run_tests", self._lazy("test_tools", "TestTools", "run_tests"))
        for command in ("lint", "type_check", "security_scan", "complexity"):
            self.register(command, self._lazy("quality_tools", "QualityTools", command))
        for command, formatter in (
            ("analyze_imports", lambda value: ToolResult.ok("\n".join(value))),
            ("generate_requirements", ToolResult.ok),
        ):
            self.register(
                command,
                self._lazy(
                    "dependency_tools",
                    "DependencyTools",
                    command,
                    formatter,
                ),
            )
        for command, method in {
            "gen_dockerfile": "dockerfile_gen",
            "gen_compose": "compose_gen",
            "gen_ci": "github_actions_gen",
            "deploy_checklist": "deploy_checklist",
        }.items():
            self.register(
                command,
                self._lazy("deploy_tools", "DeployTools", method, ToolResult.ok),
            )

    def _lazy(
        self, module, class_name, method, formatter=ToolResult.from_result
    ) -> ToolHandler:
        def handle(action):
            with self._lock:
                if module not in self._instances:
                    cls = getattr(import_module(f"agent.tools.{module}"), class_name)
                    self._instances[module] = cls(self.workspace)
                instance = self._instances[module]
            return formatter(getattr(instance, method)())

        return handle

    def register(
        self, command: str, handler: ToolHandler, *, replace: bool = False
    ) -> None:
        """Register an extension, rejecting accidental command overrides."""
        with self._lock:
            if command in self._handlers and not replace:
                raise ValueError(f"Tool '{command}' is already registered")
            self._handlers[command] = handler

    def get(self, command: str) -> ToolHandler | None:
        with self._lock:
            return self._handlers.get(command)
