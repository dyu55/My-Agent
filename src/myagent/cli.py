from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .engine import Engine
from .models import Limits, Permissions
from .providers import DemoModel, RemoteModel
from .store import RunStore
from .tools import ToolRegistry
from .workspace import Workspace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MyAgent — plan, execute, verify, resume")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "resume", "demo", "runs", "show", "undo", "tools", "serve", "doctor"):
        command = commands.add_parser(name)
        command.add_argument("--workspace", type=Path, default=Path.cwd())
        if name == "run":
            command.add_argument("task")
            command.add_argument(
                "--provider",
                choices=["ollama", "openai"],
                default=os.getenv("MYAGENT_PROVIDER", "ollama"),
            )
            command.add_argument("--model", default=os.getenv("MYAGENT_MODEL", ""))
            command.add_argument("--base-url", default=os.getenv("MYAGENT_BASE_URL", ""))
        if name in {"resume", "show", "undo"}:
            command.add_argument("run_id")
        if name in {"run", "resume", "demo"}:
            command.add_argument("--allow-write", action="store_true")
            command.add_argument("--allow-exec", action="store_true")
            command.add_argument("--max-calls", type=int, default=40)
            command.add_argument("--max-seconds", type=float, default=600)
            command.add_argument("--json", action="store_true")
        if name == "resume":
            command.add_argument("--acknowledge-interrupted", action="store_true")
        if name == "show":
            command.add_argument("--json", action="store_true")
        if name == "serve":
            command.add_argument("--port", type=int, default=8001)
    args = parser.parse_args(argv)
    console = Console(stderr=True)
    try:
        if args.command == "serve":
            import uvicorn

            from .viewer import create_app

            uvicorn.run(create_app(args.workspace), host="127.0.0.1", port=args.port)
            return 0
        store = RunStore(args.workspace)
        workspace = Workspace(args.workspace, store)
        if args.command == "runs":
            table = Table("Run", "Status", "Task", "Updated")
            for run in store.list_runs():
                table.add_row(run.id, run.status, run.task[:70], run.updated_at[:19])
            console.print(table)
            return 0
        if args.command == "show":
            run = store.load(args.run_id)
            if args.json:
                print(
                    json.dumps(
                        {
                            "run": run.model_dump(),
                            "events": store.events(run.id),
                            "changes": store.diff(run.id, workspace.resolve),
                        },
                        indent=2,
                    )
                )
            else:
                console.print(f"[bold]{run.task}[/bold]", markup=False)
                console.print(f"Status: {run.status}\n{run.summary}", markup=False)
                for step in run.steps:
                    console.print(f"  {step.status:10} {step.title}", markup=False)
                console.print(
                    f"\nInspect in your browser: myagent serve --workspace {args.workspace}",
                    markup=False,
                )
            return 0
        if args.command == "undo":
            paths = workspace.undo(args.run_id)
            console.print(
                f"Restored {len(paths)} file-tool changes. Command side effects are not restored."
            )
            return 0
        if args.command == "tools":
            registry = ToolRegistry(workspace, "", Permissions(), Limits())
            print(json.dumps(registry.catalog(), indent=2))
            return 0
        if args.command == "doctor":
            import pytest

            print(
                json.dumps(
                    {
                        "python": sys.version.split()[0],
                        "pytest": pytest.__version__,
                        "workspace": str(workspace.root),
                        "state_writable": os.access(store.directory, os.W_OK),
                        "provider_configured": bool(os.getenv("MYAGENT_MODEL")),
                        "model_service": "not contacted",
                    },
                    indent=2,
                )
            )
            return 0
        if args.command == "demo":
            if any(
                workspace.root.joinpath(path).exists()
                for path in ("temperatures.py", "test_temperatures.py")
            ):
                raise ValueError("Demo files already exist; choose a new demo workspace")
            model = DemoModel()
            permissions = Permissions(write=True, execute=True)
        elif args.command == "resume":
            run = store.load(args.run_id)
            model = (
                DemoModel()
                if run.provider == "demo"
                else RemoteModel(
                    run.provider, run.model, run.base_url, os.getenv("MYAGENT_API_KEY", "")
                )
            )
            permissions = Permissions(write=args.allow_write, execute=args.allow_exec)
        else:
            base_url = args.base_url or (
                "http://localhost:11434"
                if args.provider == "ollama"
                else "https://api.openai.com/v1"
            )
            model = RemoteModel(
                args.provider, args.model, base_url, os.getenv("MYAGENT_API_KEY", "")
            )
            permissions = Permissions(write=args.allow_write, execute=args.allow_exec)

        def report(kind, payload):
            if kind == "tool_completed":
                marker = "✓" if payload["ok"] else "✗"
                console.print(
                    f"  {marker} {payload['tool']}: {payload.get('error') or payload.get('output', '')[:180]}",
                    markup=False,
                )
            elif kind in {"step_completed", "permission_required", "paused", "failed"}:
                console.print(f"  {kind}: {payload.get('summary', payload)}", markup=False)

        engine = Engine(
            args.workspace,
            model,
            permissions,
            Limits(max_calls=args.max_calls, max_seconds=args.max_seconds),
            on_event=None if args.json else report,
        )
        if args.command == "resume":
            run = engine.advance(args.run_id, args.acknowledge_interrupted)
        else:
            task = (
                "Build a tested temperature conversion module with absolute-zero validation."
                if args.command == "demo"
                else args.task
            )
            if args.command == "demo" and not args.json:
                console.print(
                    "Demo replay · deterministic decisions, real file changes and pytest execution."
                )
            run = engine.new(task)
        if args.json:
            print(run.model_dump_json(indent=2))
        else:
            console.print(f"\nRun {run.id} · {run.status}\n{run.summary}", markup=False)
            if run.status == "paused":
                console.print(
                    f"Resume: myagent resume {run.id} --workspace {args.workspace}", markup=False
                )
        return 0 if run.status == "succeeded" else 2 if run.status == "paused" else 1
    except (ValueError, OSError, RuntimeError) as exc:
        console.print(f"Error: {exc}", style="red", markup=False)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
