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
        name = input_str.lstrip("/").split()[0].lower()
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
    external_memory_manager: Any = None  # 外部记忆管理器

    @property
    def current_model(self) -> str:
        return self.model_manager.current_model

    @property
    def current_provider(self) -> str:
        return self.model_manager.current_provider


class CommandRegistry:
    """Registry for all CLI commands."""

    def __init__(self):
        self.commands: list[Command] = []
        self._register_builtins()

    def _register_builtins(self) -> None:
        """Register built-in commands."""
        self.register(Command(name="help", description="显示帮助信息", aliases=["h", "?"], handler=self._cmd_help))
        self.register(Command(name="exit", description="退出 CLI", aliases=["quit", "q"], handler=self._cmd_exit))
        self.register(Command(name="clear", description="清屏", aliases=["cls"], handler=self._cmd_clear))
        self.register(Command(name="model", description="显示/切换模型", aliases=["m"], handler=self._cmd_model))
        self.register(Command(name="provider", description="显示/切换 provider", aliases=["p"], handler=self._cmd_provider))
        self.register(Command(name="context", description="显示当前上下文", aliases=["c"], handler=self._cmd_context))
        self.register(Command(name="ls", description="列出工作目录文件", aliases=["dir"], handler=self._cmd_ls))
        self.register(Command(name="cd", description="切换工作目录", handler=self._cmd_cd))
        self.register(Command(name="run", description="执行命令", aliases=["!"], handler=self._cmd_run))
        self.register(Command(name="task", description="执行任务", aliases=["t"], handler=self._cmd_task))
        self.register(Command(name="status", description="显示 agent 状态", aliases=["s"], handler=self._cmd_status))
        # MCP
        self.register(Command(name="mcp", description="MCP 服务器管理", handler=self._cmd_mcp))
        # Watch
        self.register(Command(name="watch", description="监控进程输出", handler=self._cmd_watch))
        # Skills
        self.register(Command(name="code-review", description="代码审查", aliases=["review", "cr"], handler=self._cmd_code_review))
        self.register(Command(name="security-review", description="安全审查", aliases=["security", "sec"], handler=self._cmd_security_review))
        self.register(Command(name="simplify", description="代码简化重构", aliases=["refactor"], handler=self._cmd_simplify))
        self.register(Command(name="init", description="初始化 CLAUDE.md", handler=self._cmd_init))
        # External Memory
        self.register(Command(name="external-memory", description="外部记忆模式", aliases=["em", "memory"], handler=self._cmd_external_memory))
        self.register(Command(name="memory-status", description="查看记忆状态", aliases=["mem"], handler=self._cmd_memory_status))

    def register(self, command: Command) -> None:
        self.commands.append(command)

    def find(self, input_str: str) -> Command | None:
        for cmd in self.commands:
            if cmd.matches(input_str):
                return cmd
        return None

    def get_all(self) -> list[Command]:
        return self.commands

    # Command handlers

    def _cmd_help(self, ctx: CLIContext, args: list[str]) -> None:
        print("\n📖 可用命令:\n")
        for cmd in self.commands:
            aliases = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
            print(f"  /{cmd.name}{aliases} - {cmd.description}")
        print("\n💡 提示: 直接输入内容与模型对话")
        print("   输入 /task <描述> 让 agent 执行任务\n")

    def _cmd_exit(self, ctx: CLIContext, args: list[str]) -> None:
        if ctx.current_monitor:
            ctx.current_monitor.stop()
        print("👋 再见!")
        sys.exit(0)

    def _cmd_clear(self, ctx: CLIContext, args: list[str]) -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def _cmd_model(self, ctx: CLIContext, args: list[str]) -> None:
        """Display or switch models."""
        if not args:
            # List current model
            print(f"📦 当前模型: {ctx.current_model}")
            print(f"🌐 当前 Provider: {ctx.current_provider}")
            print()
            return

        # Parse model name (may include provider prefix)
        model_arg = args[0]

        if "/" in model_arg:
            # Format: provider/model
            provider, model = model_arg.split("/", 1)
            success = ctx.model_manager.set_model(provider.lower(), model)
        else:
            # Just model name, use current provider
            success = ctx.model_manager.set_model(ctx.current_provider, model_arg)

        if success:
            print(f"✅ 模型已切换为: {ctx.model_manager.get_status()}")
        else:
            print(f"❌ 切换模型失败")

    def _cmd_provider(self, ctx: CLIContext, args: list[str]) -> None:
        """Display or switch providers."""
        if not args:
            print(f"🌐 当前 provider: {ctx.current_provider}")
            print("\n可用 providers:")
            for p in ModelProviderFactory.list_providers():
                print(f"   - {p}")
            print()
            return

        provider = args[0].lower()
        model = args[1] if len(args) > 1 else None

        success = ctx.model_manager.set_model(provider, model)
        if success:
            print(f"✅ Provider 已切换为: {ctx.model_manager.get_status()}")
        else:
            print(f"❌ 切换 provider 失败")

    def _cmd_context(self, ctx: CLIContext, args: list[str]) -> None:
        print(f"\n📊 当前上下文:")
        print(f"   模型: {ctx.current_model}")
        print(f"   Provider: {ctx.current_provider}")
        print(f"   工作目录: {ctx.workspace}")
        print(f"   任务执行中: {'是' if ctx.is_executing_task else '否'}")
        if ctx.task_result:
            print(f"   上次结果: {ctx.task_result[:100]}...")
        if ctx.mcp_client:
            print(f"   MCP 状态: {ctx.mcp_client.get_status()}")
        print()

    def _cmd_ls(self, ctx: CLIContext, args: list[str]) -> None:
        path = ctx.workspace / (args[0] if args else ".")
        if not path.exists():
            print(f"❌ 目录不存在: {path}")
            return
        print(f"\n📁 {path}:\n")
        for item in sorted(path.iterdir()):
            prefix = "📂" if item.is_dir() else "📄"
            print(f"   {prefix} {item.name}")
        print()

    def _cmd_cd(self, ctx: CLIContext, args: list[str]) -> None:
        if not args:
            ctx.workspace = Path.cwd()
            print(f"✅ 已切换到: {ctx.workspace}")
            return
        new_path = ctx.workspace / args[0]
        if not new_path.exists():
            print(f"❌ 目录不存在: {new_path}")
            return
        ctx.workspace = new_path.resolve()
        print(f"✅ 已切换到: {ctx.workspace}")

    def _cmd_run(self, ctx: CLIContext, args: list[str]) -> None:
        if not args:
            print("❌ 请提供要执行的命令")
            return
        cmd = " ".join(args)
        print(f"\n⚡ 执行: {cmd}\n")
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(ctx.workspace))
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"❌ Stderr: {result.stderr}")
            print(f"\n📊 Exit code: {result.returncode}\n")
        except Exception as e:
            print(f"❌ 执行失败: {e}\n")

    def _cmd_task(self, ctx: CLIContext, args: list[str]) -> None:
        pass  # Handled by interface

    def _cmd_status(self, ctx: CLIContext, args: list[str]) -> None:
        print(f"\n🤖 Agent 状态:")
        print(f"   任务执行中: {'是 ✅' if ctx.is_executing_task else '否'}")
        print(f"   模型: {ctx.current_model}")
        print(f"   Provider: {ctx.current_provider}")
        print(f"   工作目录: {ctx.workspace}")
        if ctx.task_result:
            print(f"   上次结果: {ctx.task_result[:100]}...")
        if ctx.mcp_client:
            print(f"   MCP 服务器: {ctx.mcp_client.get_status()}")
        print()

    def _cmd_mcp(self, ctx: CLIContext, args: list[str]) -> None:
        """MCP server management."""
        if not ctx.mcp_client:
            try:
                from mcp import create_mcp_client
                ctx.mcp_client = create_mcp_client()
            except ImportError:
                print("❌ MCP 模块未安装")
                return

        if not args or args[0] == "status":
            status = ctx.mcp_client.get_status()
            print("\n🔌 MCP 服务器状态:")
            for name, info in status.items():
                state_icon = {"connected": "🟢", "disconnected": "⚪", "error": "🔴"}.get(info["state"], "❓")
                print(f"   {state_icon} {name}: {info['state']}")
                if info["tools"]:
                    print(f"      工具: {', '.join(info['tools'])}")
            print()
        elif args[0] == "connect" and len(args) > 1:
            server_name = args[1]
            if ctx.mcp_client.connect(server_name):
                print(f"✅ 已连接到 MCP 服务器: {server_name}")
            else:
                print(f"❌ 连接 MCP 服务器失败: {server_name}")
        elif args[0] == "disconnect" and len(args) > 1:
            ctx.mcp_client.disconnect(args[1])
            print(f"✅ 已断开 MCP 服务器: {args[1]}")
        elif args[0] == "tools":
            tools = ctx.mcp_client.list_tools()
            print("\n🔧 可用工具:")
            for tool in tools:
                print(f"   - {tool['name']}: {tool['description']}")
            print()
        else:
            print("用法: /mcp [status|connect <name>|disconnect <name>|tools]")

    def _cmd_watch(self, ctx: CLIContext, args: list[str]) -> None:
        """Watch process output."""
        if not args:
            if ctx.current_monitor and ctx.current_monitor.state.value == "running":
                print("\n📺 当前监控状态:")
                print(ctx.current_monitor.get_summary())
                print("\n最近的输出:")
                print(ctx.current_monitor.get_recent_output())
            else:
                print("用法: /watch <command> [args...]")
            return

        # Stop existing monitor
        if ctx.current_monitor:
            ctx.current_monitor.stop()

        # Parse command
        cmd = " ".join(args)
        print(f"\n📺 开始监控: {cmd}")
        print("按 Ctrl+C 停止监控\n")

        config = MonitorConfig()
        ctx.current_monitor = ProcessMonitor(config)

        if ctx.current_monitor.start(cmd, cwd=ctx.workspace):
            try:
                # Keep running until interrupted
                while ctx.current_monitor.state.value == "running":
                    time.sleep(0.5)
                    # Print new events
                    recent = ctx.current_monitor.get_recent_output(10)
                    if recent:
                        print(recent)
            except KeyboardInterrupt:
                ctx.current_monitor.stop()
                print("\n\n📊 监控结果:")
                print(ctx.current_monitor.get_summary())
        else:
            print(f"❌ 启动监控失败")

    def _cmd_code_review(self, ctx: CLIContext, args: list[str]) -> None:
        """Run code review on workspace."""
        print("\n🔍 代码审查中...")
        try:
            from skills import CodeReviewSkill, SkillContext
            skill = CodeReviewSkill()
            skill_ctx = SkillContext(
                workspace=ctx.workspace,
                model=ctx.current_model,
                provider=ctx.current_provider,
            )
            result = skill.execute(skill_ctx, " ".join(args))
            print(result)
        except ImportError:
            print("❌ Skills 模块未安装")
        except Exception as e:
            print(f"❌ 代码审查失败: {e}")

    def _cmd_security_review(self, ctx: CLIContext, args: list[str]) -> None:
        """Run security review on workspace."""
        print("\n🔒 安全审查中...")
        try:
            from skills import SecurityReviewSkill, SkillContext
            skill = SecurityReviewSkill()
            skill_ctx = SkillContext(
                workspace=ctx.workspace,
                model=ctx.current_model,
                provider=ctx.current_provider,
            )
            result = skill.execute(skill_ctx, " ".join(args))
            print(result)
        except ImportError:
            print("❌ Skills 模块未安装")
        except Exception as e:
            print(f"❌ 安全审查失败: {e}")

    def _cmd_simplify(self, ctx: CLIContext, args: list[str]) -> None:
        """Simplify code in workspace."""
        print("\n🔧 代码简化中...")
        try:
            from skills import SimplifySkill, SkillContext
            skill = SimplifySkill()
            skill_ctx = SkillContext(
                workspace=ctx.workspace,
                model=ctx.current_model,
                provider=ctx.current_provider,
            )
            result = skill.execute(skill_ctx, " ".join(args))
            print(result)
        except ImportError:
            print("❌ Skills 模块未安装")
        except Exception as e:
            print(f"❌ 代码简化失败: {e}")

    def _cmd_init(self, ctx: CLIContext, args: list[str]) -> None:
        """Initialize CLAUDE.md."""
        print("\n📝 初始化项目文档...")
        try:
            from skills import InitSkill, SkillContext
            skill = InitSkill()
            skill_ctx = SkillContext(
                workspace=ctx.workspace,
                model=ctx.current_model,
                provider=ctx.current_provider,
            )
            result = skill.execute(skill_ctx, " ".join(args))
            print(result)
        except ImportError:
            print("❌ Skills 模块未安装")
        except Exception as e:
            print(f"❌ 初始化失败: {e}")

    def _cmd_external_memory(self, ctx: CLIContext, args: list[str]) -> None:
        """External memory mode management."""
        # 延迟加载避免循环依赖
        from agent.external_memory_integration import create_external_memory_manager

        if ctx.external_memory_manager is None:
            ctx.external_memory_manager = create_external_memory_manager(str(ctx.workspace))

        result = ctx.external_memory_manager.handle_command(args)
        print(result)

    def _cmd_memory_status(self, ctx: CLIContext, args: list[str]) -> None:
        """Display memory status."""
        from memory.state_manager import StateManager

        state_manager = StateManager(
            state_dir=str(ctx.workspace / "memory"),
            session_logs_dir=str(ctx.workspace / "memory" / "session_logs")
        )

        if not args or args[0] == "summary":
            print("\n" + state_manager.get_summary())
            return

        subcommand = args[0].lower()

        if subcommand == "features":
            features = state_manager.get_features()
            if not features:
                print("没有已记录的功能")
                return
            print("\n## 功能清单\n")
            for f in features:
                progress = state_manager.get_feature_progress(f["id"])
                print(f"- [{f['status']}] {f['name']} (任务: {progress['completed']}/{progress['total']})")
            print()
        elif subcommand == "sessions":
            sessions = state_manager.get_recent_sessions(limit=5)
            if not sessions:
                print("没有最近的会话")
                return
            print("\n## 最近会话\n")
            for s in sessions:
                started = s.get("started_at", "")[:16]
                ended = s.get("ended_at", "")
                status = "进行中" if not ended else "已结束"
                print(f"- [{status}] {s.get('task_name', 'Unknown')} ({started})")
            print()
        else:
            print(state_manager.get_summary())
