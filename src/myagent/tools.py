from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from defusedxml import ElementTree
from pydantic import Field

from .models import Action, Limits, Permissions, StrictModel, ToolResult
from .workspace import Workspace


class Empty(StrictModel):
    pass


class ReadFile(StrictModel):
    path: str
    start_line: int = Field(default=1, ge=1)
    lines: int = Field(default=250, ge=1, le=500)


class WriteFile(StrictModel):
    path: str
    content: str = Field(max_length=1_000_000)
    expected_sha256: str | None = None


class EditFile(StrictModel):
    path: str
    old: str = Field(min_length=1, max_length=200_000)
    new: str = Field(max_length=200_000)
    expected_sha256: str


class Search(StrictModel):
    pattern: str = Field(min_length=1, max_length=300)
    case_sensitive: bool = False


class Command(StrictModel):
    argv: list[str] = Field(min_length=1, max_length=80)
    cwd: str = "."


class TestCommand(StrictModel):
    path: str = "."


def process(argv: list[str], cwd: Path, timeout: float) -> ToolResult:
    if not all(isinstance(arg, str) and "\x00" not in arg for arg in argv):
        raise ValueError("Command arguments must be strings without NUL characters")
    if argv and argv[0] in {"python", "python3"}:
        argv = [sys.executable, *argv[1:]]
    started = time.monotonic()
    with tempfile.TemporaryFile() as output:
        try:
            child = subprocess.Popen(
                argv,
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as exc:
            return ToolResult(ok=False, error=f"Unable to start command: {exc.strerror}")
        stopped = ""
        try:
            while child.poll() is None:
                if time.monotonic() - started >= timeout:
                    stopped = "Command timed out"
                elif os.fstat(output.fileno()).st_size > 4_000_000:
                    stopped = "Command output exceeded 4 MB"
                if stopped:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                    break
                time.sleep(0.02)
        except BaseException:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            raise
        size = os.fstat(output.fileno()).st_size
        if size > 4_000_000:
            stopped = stopped or "Command output exceeded 4 MB"
        output.seek(max(0, size - 16000))
        text = output.read(16000).decode("utf-8", "replace")
        return ToolResult(
            ok=child.returncode == 0 and not stopped,
            output=text,
            error=stopped
            or (f"Command exited with status {child.returncode}" if child.returncode else ""),
            data={
                "returncode": child.returncode,
                "truncated": size > 16000,
                "seconds": round(time.monotonic() - started, 3),
            },
        )


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    permission: str
    schema: type[StrictModel]
    handler: Callable


class ToolRegistry:
    def __init__(self, workspace: Workspace, run_id: str, permissions: Permissions, limits: Limits):
        self.workspace, self.run_id = workspace, run_id
        self.permissions, self.limits = permissions, limits
        self.tools: dict[str, Tool] = {}
        self.register(
            Tool(
                "list_files",
                "List workspace files, excluding dependency and private directories",
                "read",
                Empty,
                self.list_files,
            )
        )
        self.register(
            Tool(
                "read_file",
                "Read UTF-8 file lines and its SHA-256 for a subsequent edit",
                "read",
                ReadFile,
                self.read_file,
            )
        )
        self.register(
            Tool(
                "search", "Find literal text in workspace source files", "read", Search, self.search
            )
        )
        self.register(
            Tool(
                "repo_map",
                "Inspect Python AST symbols and the repository file tree",
                "read",
                Empty,
                self.repo_map,
            )
        )
        self.register(
            Tool(
                "write_file",
                "Create or replace a file; existing files require expected_sha256 from read_file",
                "write",
                WriteFile,
                self.write_file,
            )
        )
        self.register(
            Tool(
                "edit_file",
                "Replace one exact, unique text span using its expected file SHA-256",
                "write",
                EditFile,
                self.edit_file,
            )
        )
        self.register(
            Tool(
                "run_command",
                "Run an argument array without a shell; execution permission grants arbitrary process access",
                "execute",
                Command,
                self.run_command,
            )
        )
        self.register(
            Tool(
                "run_tests",
                "Run pytest and inspect both process status and its JUnit report; no tests is a failure",
                "execute",
                TestCommand,
                self.run_tests,
            )
        )
        self.register(
            Tool(
                "git_diff",
                "Inspect the current Git diff without changing repository history",
                "read",
                Empty,
                self.git_diff,
            )
        )

    def register(self, tool: Tool):
        if tool.name in self.tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self.tools[tool.name] = tool

    def catalog(self) -> list[dict]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "permission": tool.permission,
                "arguments": tool.schema.model_json_schema(),
            }
            for tool in self.tools.values()
        ]

    def permission_for(self, action: Action) -> str:
        tool = self.tools.get(action.tool)
        return tool.permission if tool else "read"

    def check_permission(self, action: Action) -> str:
        permission = self.permission_for(action)
        if permission == "write" and not self.permissions.write:
            return "write"
        if permission == "execute" and not self.permissions.execute:
            return "execute"
        return ""

    def execute(self, action: Action) -> ToolResult:
        tool = self.tools.get(action.tool)
        if not tool:
            return ToolResult(ok=False, error=f"Unknown tool: {action.tool}")
        permission = self.check_permission(action)
        if permission:
            return ToolResult(
                ok=False,
                error=f"{permission} permission is required",
                requires_permission=permission,
            )
        try:
            arguments = tool.schema.model_validate(action.arguments)
            return tool.handler(arguments)
        except (ValueError, OSError, SyntaxError, UnicodeError) as exc:
            return ToolResult(ok=False, error=f"{type(exc).__name__}: {exc}")

    def list_files(self, args: Empty) -> ToolResult:
        files = [str(p.relative_to(self.workspace.root)) for p in self.workspace.files()]
        return ToolResult(ok=True, output="\n".join(files), data={"files": files})

    def read_file(self, args: ReadFile) -> ToolResult:
        data = self.workspace.read(args.path, args.start_line, args.lines)
        return ToolResult(ok=True, output=data.pop("text"), data=data)

    def search(self, args: Search) -> ToolResult:
        matches = []
        needle = args.pattern if args.case_sensitive else args.pattern.casefold()
        for path in self.workspace.files():
            if path.stat().st_size > 200_000:
                continue
            try:
                for i, line in enumerate(path.read_text().splitlines(), 1):
                    if needle in (line if args.case_sensitive else line.casefold()):
                        matches.append(
                            {
                                "path": str(path.relative_to(self.workspace.root)),
                                "line": i,
                                "text": line[:500],
                            }
                        )
                    if len(matches) == 100:
                        return ToolResult(ok=True, data={"matches": matches, "truncated": True})
            except (OSError, UnicodeError):
                continue
        return ToolResult(ok=True, data={"matches": matches, "truncated": False})

    def repo_map(self, args: Empty) -> ToolResult:
        return ToolResult(ok=True, output=self.workspace.repo_map())

    def write_file(self, args: WriteFile) -> ToolResult:
        data = self.workspace.write(self.run_id, args.path, args.content, args.expected_sha256)
        return ToolResult(
            ok=True,
            output=f"Wrote {args.path}" if data["changed"] else "File already matches",
            data=data,
        )

    def edit_file(self, args: EditFile) -> ToolResult:
        data = self.workspace.edit(self.run_id, args.path, args.old, args.new, args.expected_sha256)
        return ToolResult(ok=True, output=f"Edited {args.path}", data=data)

    def run_command(self, args: Command) -> ToolResult:
        cwd = self.workspace.resolve(args.cwd)
        if not cwd.is_dir():
            raise ValueError("Command working directory does not exist")
        return process(args.argv, cwd, self.limits.command_timeout)

    def run_tests(self, args: TestCommand) -> ToolResult:
        target = self.workspace.resolve(args.path)
        if not target.exists():
            raise ValueError("Test path does not exist")
        with tempfile.TemporaryDirectory(prefix="myagent-tests-") as directory:
            report = Path(directory) / "report.xml"
            result = process(
                [sys.executable, "-m", "pytest", str(target), "-q", f"--junitxml={report}"],
                self.workspace.root,
                self.limits.command_timeout,
            )
            try:
                if report.stat().st_size > 4_000_000:
                    raise ValueError("JUnit report exceeds 4 MB")
                root = ElementTree.parse(report).getroot()
                cases = root.findall(".//testcase")
                failed = sum(case.find("failure") is not None for case in cases)
                errors = sum(case.find("error") is not None for case in cases)
                skipped = sum(case.find("skipped") is not None for case in cases)
                passed = len(cases) - failed - errors - skipped
                result.data.update(
                    {
                        "tests": len(cases),
                        "passed": passed,
                        "failed": failed,
                        "errors": errors,
                        "skipped": skipped,
                        "verification": True,
                    }
                )
                result.ok = result.ok and passed > 0 and failed == 0 and errors == 0
                if not result.ok and not result.error:
                    result.error = "Tests failed or no executable tests passed"
            except Exception:
                result.ok = False
                result.error = result.error or "JUnit report is missing or invalid"
            return result

    def git_diff(self, args: Empty) -> ToolResult:
        return process(
            [
                "git",
                "--no-pager",
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--",
                ".",
                ":(exclude).env",
                ":(exclude).env.*",
                ":(exclude).myagent",
            ],
            self.workspace.root,
            self.limits.command_timeout,
        )
