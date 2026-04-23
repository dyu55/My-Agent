"""Execution tools - script execution, testing, package management."""

import subprocess
from pathlib import Path
from typing import Any

import importlib.util

from .base import ToolResult


class ExecTools:
    """Container for execution tools."""

    def __init__(self, workspace: str):
        self.workspace = workspace

    def execute_script(self, action: dict[str, Any]) -> ToolResult:
        """Execute a shell command or script."""
        script = action.get("script")

        if not script:
            return ToolResult.err("Missing script", "Error: Missing script")

        try:
            result = subprocess.run(
                script,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.workspace,
                timeout=30,
            )
            output = f"Exit Code: {result.returncode}\nStdout:\n{result.stdout}\nStderr:\n{result.stderr}"
            return ToolResult.ok(output)
        except subprocess.TimeoutExpired:
            return ToolResult.err("Command timed out after 30 seconds", "Error: Command timed out after 30 seconds")
        except Exception as e:
            return ToolResult.err(f"Error executing script: {str(e)}", f"Error executing script: {str(e)}")

    def check_dependencies(self, action: dict[str, Any]) -> ToolResult:
        """Check if Python modules are available."""
        modules = action.get("modules", [])

        if not modules:
            return ToolResult.ok('{"available": [], "missing": []}')

        available = [
            m for m in modules if importlib.util.find_spec(m) is not None
        ]
        missing = [
            m for m in modules if importlib.util.find_spec(m) is None
        ]
        result = {"available": available, "missing": missing}
        return ToolResult.ok(str(result))

    def run_tests(self, action: dict[str, Any]) -> ToolResult:
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
                return ToolResult.ok(f"All tests passed!\n{output[:2000]}")
            return ToolResult.err(
                f"Tests failed (exit code: {result.returncode})",
                f"Tests failed (exit code: {result.returncode})\n{output[:2000]}"
            )
        except FileNotFoundError:
            return ToolResult.err("pytest not found", "Error: pytest not found")
        except Exception as e:
            return ToolResult.err(f"Error running tests: {str(e)}", f"Error running tests: {str(e)}")

    def pip_install(self, action: dict[str, Any]) -> ToolResult:
        """Install Python packages."""
        packages = action.get("packages", [])

        if not packages:
            return ToolResult.err("No packages specified", "Error: No packages specified")

        try:
            result = subprocess.run(
                ["pip", "install"] + packages,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                return ToolResult.ok(f"Successfully installed: {', '.join(packages)}")
            return ToolResult.err(
                "Installation failed",
                f"Installation failed:\n{result.stdout + result.stderr}"
            )
        except Exception as e:
            return ToolResult.err(f"Error installing packages: {str(e)}", f"Error installing packages: {str(e)}")


def get_exec_tool_handlers(workspace: str) -> dict[str, callable]:
    """Get execution tool handlers for ToolExecutor."""
    tools = ExecTools(workspace)
    return {
        "execute": tools.execute_script,
        "check_dependencies": tools.check_dependencies,
        "run_tests": tools.run_tests,
        "pip_install": tools.pip_install,
    }
