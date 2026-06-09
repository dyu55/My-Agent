"""Command registry and built-in commands."""

import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from utils.monitor import ProcessMonitor, MonitorConfig
from utils.model_provider import ModelManager, ModelProviderFactory


@dataclass
class Command:
    """Represents a CLI command."""

    name: str
    description: str
    aliases: list[str] = field(default_factory=list)
    handler: Callable[["CLIContext", list[str]], None] | None = None

    def matches(self, input_str: str) -> bool:
        """Check if input matches this command or its aliases."""
        parts = input_str.lstrip("/").split()
        if not parts:
            return False
        name = parts[0].lower()
        return name == self.name.lower() or name in [a.lower() for a in self.aliases]


@dataclass
class CLIContext:
    """Context available during CLI execution."""

    model_manager: ModelManager
    workspace: Path
    is_executing_task: bool = False
    task_result: str | None = None
    mcp_client: Any = None
    current_monitor: ProcessMonitor | None = None
    external_memory_manager: Any = None
    think_model: str | None = None
    think_provider: str | None = None
    execute_model: str | None = None
    execute_provider: str | None = None

    @property
    def current_model(self) -> str:
        return self.model_manager.current_model

    @property
    def current_provider(self) -> str:
        return self.model_manager.current_provider


# Lazy display import to avoid circular deps
_display = None


def _get_display():
    global _display
    if _display is None:
        from .display import Display
        _display = Display()
    return _display


class CommandRegistry:
    """Registry for all CLI commands."""

    def __init__(self):
        self.commands: list[Command] = []
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in commands."""
        self.register(Command(name="help", description="Show help", aliases=["h", "?"], handler=self._cmd_help))
        self.register(Command(name="exit", description="Exit CLI", aliases=["quit", "q"], handler=self._cmd_exit))
        self.register(Command(name="clear", description="Clear screen", aliases=["cls"], handler=self._cmd_clear))
        self.register(Command(name="model", description="Show/switch model", aliases=["m"], handler=self._cmd_model))
        self.register(Command(name="provider", description="Show/switch provider", aliases=["p"], handler=self._cmd_provider))
        self.register(Command(name="context", description="Show current context", aliases=["c"], handler=self._cmd_context))
        self.register(Command(name="ls", description="List workspace files", aliases=["dir"], handler=self._cmd_ls))
        self.register(Command(name="cd", description="Change workspace directory", handler=self._cmd_cd))
        self.register(Command(name="run", description="Run shell command", aliases=["!"], handler=self._cmd_run))
        self.register(Command(name="task", description="Execute task", aliases=["t"], handler=self._cmd_task))
        self.register(Command(name="status", description="Show agent status", aliases=["s"], handler=self._cmd_status))
        self.register(Command(name="mcp", description="MCP server management", handler=self._cmd_mcp))
        self.register(Command(name="watch", description="Monitor process output", handler=self._cmd_watch))
        self.register(Command(name="code-review", description="Code review", aliases=["review", "cr"], handler=self._cmd_code_review))
        self.register(Command(name="security-review", description="Security review", aliases=["security", "sec"], handler=self._cmd_security_review))
        self.register(Command(name="simplify", description="Code simplification", aliases=["refactor"], handler=self._cmd_simplify))
        self.register(Command(name="init", description="Initialize CLAUDE.md", handler=self._cmd_init))
        self.register(Command(name="external-memory", description="External memory mode", aliases=["em", "memory"], handler=self._cmd_external_memory))
        self.register(Command(name="memory-status", description="View memory state", aliases=["mem"], handler=self._cmd_memory_status))
        self.register(Command(name="cost", description="Show API cost report", handler=self._cmd_cost))
        self.register(Command(name="cache", description="Show LLM cache stats", handler=self._cmd_cache))

    def register(self, command: Command) -> None:
        self.commands.append(command)

    def find(self, input_str: str) -> Command | None:
        for cmd in self.commands:
            if cmd.matches(input_str):
                return cmd
        return None

    def get_all(self) -> list[Command]:
        return self.commands

    # ── Command handlers ─────────────────────────────────

    def _cmd_help(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        commands = [
            (f"/{cmd.name}, {', '.join('/' + a for a in cmd.aliases)}" if cmd.aliases else f"/{cmd.name}",
             cmd.description,
             "")
            for cmd in self.commands
        ]
        d.help_table(commands)

    def _cmd_exit(self, ctx: CLIContext, args: list[str]) -> None:
        if ctx.current_monitor:
            ctx.current_monitor.stop()
        _get_display().info("Goodbye!")
        sys.exit(0)

    def _cmd_clear(self, ctx: CLIContext, args: list[str]) -> None:
        _get_display().clear()

    def _cmd_model(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()

        if not args:
            # Show all models
            d.model_info(ctx.current_model, ctx.current_provider)
            if ctx.think_model:
                think = f"{ctx.think_provider or ctx.current_provider}/{ctx.think_model}"
                print(f"  🧠 Think:    {think}")
            if ctx.execute_model:
                exec_m = f"{ctx.execute_provider or ctx.current_provider}/{ctx.execute_model}"
                print(f"  ⚡ Execute:  {exec_m}")
            return

        # Subcommand: think or execute
        if args[0].lower() in ("think", "execute"):
            role = args[0].lower()
            if len(args) < 2:
                d.error(f"Usage: /model {role} <model_name>")
                return
            model_arg = args[1]
            if "/" in model_arg:
                provider, model = model_arg.split("/", 1)
            else:
                provider = ctx.current_provider
                model = model_arg

            if role == "think":
                ctx.think_model = model
                ctx.think_provider = provider
                d.success(f"Think model set to: {provider}/{model}")
            else:
                ctx.execute_model = model
                ctx.execute_provider = provider
                d.success(f"Execute model set to: {provider}/{model}")
            return

        # Default: set the main model
        model_arg = args[0]
        if "/" in model_arg:
            provider, model = model_arg.split("/", 1)
            success = ctx.model_manager.set_model(provider.lower(), model)
        else:
            success = ctx.model_manager.set_model(ctx.current_provider, model_arg)

        if success:
            d.success(f"Model switched to: {ctx.model_manager.get_status()}")
        else:
            d.error("Failed to switch model")

    def _cmd_provider(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        if not args:
            providers = ModelProviderFactory.list_providers()
            d.provider_list(ctx.current_provider, providers)
            return

        provider = args[0].lower()
        model = args[1] if len(args) > 1 else None
        success = ctx.model_manager.set_model(provider, model)
        if success:
            d.success(f"Provider switched to: {ctx.model_manager.get_status()}")
        else:
            d.error("Failed to switch provider")

    def _cmd_context(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        data = {
            "Model": ctx.current_model,
            "Provider": ctx.current_provider,
            "Workspace": str(ctx.workspace),
            "Task running": "Yes" if ctx.is_executing_task else "No",
        }
        if ctx.task_result:
            data["Last result"] = ctx.task_result[:100]
        if ctx.mcp_client:
            data["MCP"] = ctx.mcp_client.get_status()
        d.context_panel(data)

    def _cmd_ls(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        path = ctx.workspace / (args[0] if args else ".")
        if not path.exists():
            d.error(f"Directory not found: {path}")
            return

        entries = []
        try:
            for item in sorted(path.iterdir()):
                if item.is_dir():
                    entries.append((item.name, True, ""))
                else:
                    size = item.stat().st_size
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f}K"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f}M"
                    entries.append((item.name, False, size_str))
        except PermissionError:
            d.error(f"Permission denied: {path}")
            return

        d.directory_listing(path, entries)

    def _cmd_cd(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        if not args:
            ctx.workspace = Path.cwd()
            d.success(f"Changed to: {ctx.workspace}")
            return
        new_path = ctx.workspace / args[0]
        if not new_path.exists():
            d.error(f"Directory not found: {new_path}")
            return
        ctx.workspace = new_path.resolve()
        d.success(f"Changed to: {ctx.workspace}")

    def _cmd_run(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        if not args:
            d.error("Usage: /run <command>")
            return

        cmd = " ".join(args)
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, cwd=str(ctx.workspace), timeout=60,
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += ("\n" if output else "") + result.stderr
            if not output:
                output = f"(no output, exit code: {result.returncode})"
            d.command_output(output, title=f"Shell  exit:{result.returncode}")
        except subprocess.TimeoutExpired:
            d.error("Command timed out (60s)")
        except Exception as e:
            d.error(f"Execution failed: {e}")

    def _cmd_task(self, ctx: CLIContext, args: list[str]) -> None:
        pass  # Handled by interface

    def _cmd_status(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        data = {
            "Task running": "Yes" if ctx.is_executing_task else "No",
            "Model": ctx.current_model,
            "Provider": ctx.current_provider,
            "Workspace": str(ctx.workspace),
        }
        if ctx.task_result:
            data["Last result"] = ctx.task_result[:100]
        if ctx.mcp_client:
            data["MCP"] = ctx.mcp_client.get_status()
        d.status_panel(data)

    def _cmd_mcp(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        if not ctx.mcp_client:
            try:
                from mcp import create_mcp_client
                ctx.mcp_client = create_mcp_client()
            except ImportError:
                d.error("MCP module not installed")
                return

        if not args or args[0] == "status":
            status = ctx.mcp_client.get_status()
            d.mcp_status(status)
        elif args[0] == "connect" and len(args) > 1:
            server_name = args[1]
            if ctx.mcp_client.connect(server_name):
                d.success(f"Connected to MCP server: {server_name}")
            else:
                d.error(f"Failed to connect: {server_name}")
        elif args[0] == "disconnect" and len(args) > 1:
            ctx.mcp_client.disconnect(args[1])
            d.success(f"Disconnected: {args[1]}")
        elif args[0] == "tools":
            tools = ctx.mcp_client.list_tools()
            table_data = [(t["name"], t["description"]) for t in tools]
            d.info(f"Available tools: {len(table_data)}")
            for name, desc in table_data:
                d.plain(f"  {name}: {desc}")
        else:
            d.info("Usage: /mcp [status|connect <name>|disconnect <name>|tools]")

    def _cmd_watch(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        if not args:
            if ctx.current_monitor and ctx.current_monitor.state.value == "running":
                d.info("Current monitor:")
                d.plain(ctx.current_monitor.get_summary())
                d.plain(ctx.current_monitor.get_recent_output())
            else:
                d.info("Usage: /watch <command> [args...]")
            return

        if ctx.current_monitor:
            ctx.current_monitor.stop()

        cmd = " ".join(args)
        d.info(f"Monitoring: {cmd}")

        config = MonitorConfig()
        ctx.current_monitor = ProcessMonitor(config)

        if ctx.current_monitor.start(cmd, cwd=ctx.workspace):
            try:
                while ctx.current_monitor.state.value == "running":
                    time.sleep(0.5)
                    recent = ctx.current_monitor.get_recent_output(10)
                    if recent:
                        d.plain(recent)
            except KeyboardInterrupt:
                ctx.current_monitor.stop()
                d.info("Monitor stopped")
                d.plain(ctx.current_monitor.get_summary())
        else:
            d.error("Failed to start monitor")

    def _cmd_code_review(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        d.info("Running code review...")
        try:
            from skills import CodeReviewSkill, SkillContext
            skill = CodeReviewSkill()
            skill_ctx = SkillContext(
                workspace=ctx.workspace,
                model=ctx.current_model,
                provider=ctx.current_provider,
            )
            with d.spinner("Reviewing code..."):
                result = skill.execute(skill_ctx, " ".join(args))
            d.stream_text(result)
        except ImportError:
            d.error("Skills module not installed")
        except Exception as e:
            d.error(f"Code review failed: {e}")

    def _cmd_security_review(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        d.info("Running security review...")
        try:
            from skills import SecurityReviewSkill, SkillContext
            skill = SecurityReviewSkill()
            skill_ctx = SkillContext(
                workspace=ctx.workspace,
                model=ctx.current_model,
                provider=ctx.current_provider,
            )
            with d.spinner("Scanning..."):
                result = skill.execute(skill_ctx, " ".join(args))
            d.stream_text(result)
        except ImportError:
            d.error("Skills module not installed")
        except Exception as e:
            d.error(f"Security review failed: {e}")

    def _cmd_simplify(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        d.info("Simplifying code...")
        try:
            from skills import SimplifySkill, SkillContext
            skill = SimplifySkill()
            skill_ctx = SkillContext(
                workspace=ctx.workspace,
                model=ctx.current_model,
                provider=ctx.current_provider,
            )
            with d.spinner("Analyzing..."):
                result = skill.execute(skill_ctx, " ".join(args))
            d.stream_text(result)
        except ImportError:
            d.error("Skills module not installed")
        except Exception as e:
            d.error(f"Simplification failed: {e}")

    def _cmd_init(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        d.info("Initializing CLAUDE.md...")
        try:
            from skills import InitSkill, SkillContext
            skill = InitSkill()
            skill_ctx = SkillContext(
                workspace=ctx.workspace,
                model=ctx.current_model,
                provider=ctx.current_provider,
            )
            with d.spinner("Generating..."):
                result = skill.execute(skill_ctx, " ".join(args))
            d.stream_text(result)
        except ImportError:
            d.error("Skills module not installed")
        except Exception as e:
            d.error(f"Init failed: {e}")

    def _cmd_external_memory(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        from agent.external_memory_integration import create_external_memory_manager

        if ctx.external_memory_manager is None:
            ctx.external_memory_manager = create_external_memory_manager(str(ctx.workspace))

        result = ctx.external_memory_manager.handle_command(args)
        d.plain(result)

    def _cmd_memory_status(self, ctx: CLIContext, args: list[str]) -> None:
        d = _get_display()
        from memory.state_manager import StateManager

        state_manager = StateManager(
            state_dir=str(ctx.workspace / "memory"),
            session_logs_dir=str(ctx.workspace / "memory" / "session_logs"),
        )

        if not args or args[0] == "summary":
            d.plain(state_manager.get_summary())
            return

        subcommand = args[0].lower()

        if subcommand == "features":
            features = state_manager.get_features()
            if not features:
                d.info("No features recorded")
                return
            for f in features:
                progress = state_manager.get_feature_progress(f["id"])
                d.plain(f"  [{f['status']}] {f['name']} (tasks: {progress['completed']}/{progress['total']})")
        elif subcommand == "sessions":
            sessions = state_manager.get_recent_sessions(limit=5)
            if not sessions:
                d.info("No recent sessions")
                return
            for s in sessions:
                started = s.get("started_at", "")[:16]
                ended = s.get("ended_at", "")
                status = "active" if not ended else "done"
                d.plain(f"  [{status}] {s.get('task_name', 'Unknown')} ({started})")
        else:
            d.plain(state_manager.get_summary())

    def _cmd_cost(self, ctx: CLIContext, args: list[str]) -> None:
        """Show API cost report."""
        d = _get_display()
        try:
            from utils.cost_tracker import get_global_tracker
            tracker = get_global_tracker()
            report = tracker.get_report()
            d.plain(report)
        except Exception as e:
            d.error(f"Cost tracker not available: {e}")

    def _cmd_cache(self, ctx: CLIContext, args: list[str]) -> None:
        """Show LLM cache stats."""
        d = _get_display()
        try:
            from utils.llm_cache import get_global_cache
            cache = get_global_cache()
            stats = cache.stats
            d.status_panel({
                "Total requests": stats.total_requests,
                "Cache hits": stats.cache_hits,
                "Cache misses": stats.cache_misses,
                "Hit rate": f"{stats.hit_rate * 100:.1f}%",
                "Entries": len(cache._cache),
            })
        except Exception as e:
            d.error(f"Cache not available: {e}")
