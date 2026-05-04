"""
MyAgent CLI - Claude Code style interactive coding agent

Interactive mode:
    ./myagent                    # Start interactive CLI
    >>> Implement user login
    >>> Add registration page
    >>> /task Add payment module

Commands:
    /task <desc>    Execute task
    /edit <file>    View file
    /read <file>    Read file
    /run <cmd>      Execute command
    /test           Run tests
    /git <args>     Git operations
    /search <query> Search memories
    /status         Show status
    /help           Help
    /exit           Exit

Shortcuts:
    Ctrl+C         Cancel current task
    Ctrl+D         Exit
"""

import os
import readline
import sys
from pathlib import Path
from enum import Enum
from typing import Optional

from agent import AgentEngine
from agent.engine import AgentConfig
from agent.external_memory_integration import create_external_memory_manager


class Mode(Enum):
    """CLI operating mode."""

    CHAT = "chat"
    TASK = "task"


class MichaelCLI:
    """
    Claude Code style interactive CLI.

    Features:
    - Task-first: Just type task description to execute
    - Smart editing: Agent auto-decides file modifications
    - Progress tracking: Shows task execution progress
    - Auto tests: Runs tests after task completion
    - Git integration: Auto-saves changes
    """

    DEFAULT_BANNER = """
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║   🤖 {name} - Local Coding Agent                                          ║
║                                                                            ║
║   💬 CHAT: 直接对话，回答问题，写文档                                     ║
║   🎯 TASK: Agent 执行，分解任务，写代码、跑测试                          ║
║                                                                            ║
║   {mode_indicator}                                                         ║
║                                                                            ║
║   Commands: /help for all commands, /mode to switch modes                 ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

    def __init__(
        self,
        workspace: Path | str = "workspace",
        model: str = "gemma4:latest",
        provider: str = "ollama",
        base_url: str = "http://localhost:11434",
        api_key: Optional[str] = None,
        cli_name: str = "myagent",
    ):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.model = model
        self.provider = provider
        self.base_url = base_url
        self.api_key = api_key
        self.cli_name = cli_name

        self.agent: Optional[AgentEngine] = None
        self.external_memory = create_external_memory_manager(str(self.workspace))
        self.current_mode = Mode.TASK  # TASK mode for agent execution by default

        self.is_running = False
        self.current_task: Optional[str] = None
        self.task_count = 0

        self._init_agent()

    def _init_agent(self) -> None:
        """Initialize the agent engine."""
        config = AgentConfig(
            model=self.model,
            provider=self.provider,
            base_url=self.base_url,
            api_key=self.api_key,
            workspace=self.workspace,  # Path object
        )
        self.agent = AgentEngine(config)

    def _get_banner(self) -> str:
        """Get custom banner with CLI name."""
        mode_info = {
            Mode.CHAT: "💬 [CHAT] 直接对话模式 - 输入问题直接调用模型",
            Mode.TASK: "🎯 [TASK] 任务执行模式 - 输入任务让 Agent 执行",
        }
        mode_indicator = mode_info[self.current_mode]
        return self.DEFAULT_BANNER.format(name=self.cli_name, mode_indicator=mode_indicator)

    def run(self) -> None:
        """Start interactive CLI"""
        self.is_running = True
        print(self._get_banner())
        print(f"📦 Model: {self.model} ({self.provider})")
        print(f"📁 Workspace: {self.workspace}\n")

        self._setup_readline()

        while self.is_running:
            try:
                user_input = self._read_input()
                if not user_input:
                    continue

                self._process_input(user_input)

            except KeyboardInterrupt:
                print("\n⚠️  Type /exit to quit, or enter new task to continue")
            except EOFError:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

        self.is_running = False

    def _setup_readline(self) -> None:
        """Setup readline"""
        try:
            readline.parse_and_bind("tab: complete")
            readline.parse_and_bind("set editing-mode vi")
        except Exception:
            pass

    def _read_input(self) -> str:
        """Read input"""
        try:
            if self.current_mode == Mode.CHAT:
                prompt = "💬 "
            elif self.current_task:
                prompt = "🔄 "
            else:
                prompt = "🎯 "
            return input(prompt).strip()
        except (KeyboardInterrupt, EOFError):
            raise

    def _process_input(self, user_input: str) -> None:
        """Process input"""
        user_input = user_input.strip()
        if not user_input:
            return

        # Command mode
        if user_input.startswith("/"):
            self._handle_command(user_input)
            return

        # Route based on mode
        if self.current_mode == Mode.CHAT:
            self._handle_chat(user_input)
        else:
            self._execute_task(user_input)

    def _handle_chat(self, user_input: str) -> None:
        """Handle chat mode - direct model conversation."""
        from utils.model_provider import ModelManager
        import requests

        print()

        # Build prompt with history
        prompt = """你是一个有帮助的 AI 助手。用户正在通过 CLI 与你对话。

你可以:
- 回答问题
- 帮助调试代码
- 解释概念
- 提供建议

尽量简洁明了。"""

        try:
            model_manager = ModelManager(
                default_provider=self.provider,
                default_model=self.model,
            )
            # Try with longer timeout for remote server
            response = model_manager.chat(
                prompt + f"\n\n用户: {user_input}",
                timeout=60  # 60 second timeout
            )
            print(response)
        except requests.exceptions.Timeout:
            print(f"❌ LLM 调用超时 (60s)")
            print("   请尝试切换到 TASK 模式，输入任务让 Agent 执行")
        except Exception as e:
            print(f"❌ LLM 调用失败: {e}")
            print("   请检查模型服务是否运行中")

    def _handle_command(self, user_input: str) -> None:
        """Handle command"""
        parts = user_input.split(maxsplit=1)
        cmd = parts[0].lstrip("/").lower()
        args = parts[1] if len(parts) > 1 else ""

        handlers = {
            "task": self._cmd_task,
            "t": self._cmd_task,
            "mode": self._switch_mode,
            "edit": self._cmd_edit,
            "read": self._cmd_read,
            "run": self._cmd_run,
            "test": self._cmd_test,
            "git": self._cmd_git,
            "status": self._cmd_status,
            "help": self._cmd_help,
            "h": self._cmd_help,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
            "q": self._cmd_exit,
            # External memory commands
            "em": self._cmd_external_memory,
            "external-memory": self._cmd_external_memory,
            "memory": self._cmd_external_memory,
            "mem": self._cmd_external_memory,
            "search": self._cmd_search,
        }

        handler = handlers.get(cmd)
        if handler:
            handler(args)
        else:
            print(f"❌ Unknown command: /{cmd}")
            print("   Type /help for available commands")

    def _execute_task(self, task: str) -> None:
        """Execute task"""
        self.task_count += 1
        self.current_task = task

        print(f"\n{'='*70}")
        print(f"🚀 Task #{self.task_count}: {task}")
        print(f"{'='*70}\n")

        try:
            # Start external memory workflow
            self.external_memory.start_workflow(task)

            # Execute task
            result = self.agent.run(task)

            # Add checkpoint
            self.external_memory.add_checkpoint(
                "write_code",
                "success",
                f"Task completed: {task[:50]}",
                {"result": result[:200] if result else ""}
            )

            print(f"\n{'='*70}")
            print(f"✅ Task completed")
            print(f"{'='*70}")
            print(f"📊 Result: {result}")

            # Auto-prompt for git commit
            self._prompt_git_commit()

        except KeyboardInterrupt:
            print("\n\n⚠️  Task cancelled")
            self.external_memory.add_checkpoint(
                "write_code",
                "cancelled",
                "Task cancelled by user",
                {}
            )
        except Exception as e:
            print(f"\n❌ Task failed: {e}")
            self.external_memory.add_checkpoint(
                "write_code",
                "failed",
                f"Task failed: {str(e)}",
                {}
            )
        finally:
            self.current_task = None

    def _prompt_git_commit(self) -> None:
        """Prompt user for git commit"""
        print("\nCommit changes? (y/n): ", end="")
        try:
            response = input().strip().lower()
            if response == "y":
                result = self.external_memory.commit()
                print(f"✅ Committed: {result.get('summary', 'OK')}")
        except (KeyboardInterrupt, EOFError):
            pass

    # ==================== Command handlers ====================

    def _cmd_task(self, args: str) -> None:
        """Execute task"""
        if not args:
            print("Usage: /task <task description>")
            return
        self._execute_task(args)

    def _cmd_edit(self, args: str) -> None:
        """Edit/view file"""
        if not args:
            print("Usage: /edit <file path>")
            return
        file_path = self.workspace / args
        if not file_path.exists():
            print(f"❌ File not found: {args}")
            return
        print(f"📝 Reading file: {file_path}")
        print(file_path.read_text(encoding="utf-8")[:1000])

    def _cmd_read(self, args: str) -> None:
        """Read file"""
        self._cmd_edit(args)

    def _cmd_run(self, args: str) -> None:
        """Execute command"""
        if not args:
            print("Usage: /run <command>")
            return
        print(f"\n⚡ Executing: {args}\n")
        import subprocess
        try:
            result = subprocess.run(
                args,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.workspace),
                timeout=60,
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(f"❌ Stderr: {result.stderr}")
            print(f"\n📊 Exit code: {result.returncode}")
        except subprocess.TimeoutExpired:
            print("❌ Command timed out (60s)")
        except Exception as e:
            print(f"❌ Execution failed: {e}")

    def _cmd_test(self, args: str) -> None:
        """Run tests"""
        print("\n🧪 Running tests...\n")
        import subprocess
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                cwd=str(self.workspace),
                timeout=120,
            )
            print(result.stdout or result.stderr)
            if result.returncode == 0:
                print("✅ All tests passed!")
            else:
                print("❌ Some tests failed")
        except FileNotFoundError:
            print("❌ pytest not installed")
        except Exception as e:
            print(f"❌ Tests failed: {e}")

    def _cmd_git(self, args: str) -> None:
        """Git operations"""
        if not args:
            args = "status"
        print(f"\n🔀 Git: {args}\n")
        import subprocess
        try:
            result = subprocess.run(
                ["git"] + args.split(),
                capture_output=True,
                text=True,
                cwd=str(self.workspace),
                timeout=30,
            )
            print(result.stdout or result.stderr)
        except Exception as e:
            print(f"❌ Git failed: {e}")

    def _cmd_status(self, args: str) -> None:
        """Show status"""
        print(f"""
📊 {self.cli_name} Status
────────────────────
Tasks: {self.task_count}
Current task: {self.current_task or "none"}
Model: {self.model}
Provider: {self.provider}
Workspace: {self.workspace}
────────────────────
External Memory: {'enabled' if self.external_memory.is_enabled() else 'disabled'}
""")

    def _cmd_help(self, args: str) -> None:
        """Show help"""
        print(f"""
📖 Command Help

Type task description directly to execute, for example:
  → Implement user login functionality
  → Add a registration page

/Commands:
  /task <desc>    Execute task
  /edit <file>    View file
  /read <file>    View file (same as /edit)
  /run <cmd>      Execute shell command
  /test           Run pytest
  /git <args>     Git operations
  /status         Show status
  /search <query> Search memories
  /help           Show this help

Shortcuts:
  Ctrl+C          Cancel current task
  Ctrl+D          Exit

External Memory:
  /em start        Start external memory workflow
  /em status       Show workflow status
  /em commit       Commit changes
""")

    def _cmd_exit(self, args: str) -> None:
        """Exit"""
        print("\n👋 Goodbye!")
        self.is_running = False

    def _switch_mode(self, args: str) -> None:
        """Switch between CHAT and TASK modes."""
        if self.current_mode == Mode.CHAT:
            self.current_mode = Mode.TASK
            print("\n🎯 [TASK] 已切换到任务执行模式 - 输入任务描述执行")
        else:
            self.current_mode = Mode.CHAT
            print("\n💬 [CHAT] 已切换到直接对话模式 - 输入问题直接调用模型回答")

    def _cmd_external_memory(self, args: str) -> None:
        """External memory command"""
        parts = args.split() if args else []
        result = self.external_memory.handle_command(parts)
        print(result)

    def _cmd_search(self, args: str) -> None:
        """
        Search memories - Layer 1 MVP

        Usage: /search <query> [--tags TAG1,TAG2] [--limit N]
        Example: /search authentication --limit 5
        """
        # 解析参数
        import shlex
        parts = shlex.split(args) if args else []

        query = ""
        tags = None
        limit = 5

        i = 0
        while i < len(parts):
            if parts[i] == "--tags" and i + 1 < len(parts):
                tags = parts[i + 1].split(",")
                i += 2
            elif parts[i] == "--limit" and i + 1 < len(parts):
                limit = int(parts[i + 1])
                i += 2
            elif parts[i] == "--help":
                print(self._search_help())
                return
            else:
                query = parts[i]
                i += 1

        if not query:
            print("Usage: /search <query> [--tags TAG1,TAG2] [--limit N]")
            print("Example: /search authentication --limit 5")
            return

        # 执行搜索
        results = self.external_memory.search_memories(
            query=query,
            limit=limit,
            tags=tags
        )

        if not results:
            print(f"🔍 No memories found for: '{query}'")
            return

        print(f"\n🔍 Search results for: '{query}'")
        print("=" * 60)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. [Similarity: {result['similarity']:.2%}]")
            print(f"   📝 {result['content'][:100]}...")
            if result.get("tags"):
                print(f"   🏷️  Tags: {', '.join(result['tags'])}")
            if result.get("session_id"):
                print(f"   💾 Session: {result['session_id']}")

    def _search_help(self) -> str:
        """Search command help"""
        return """
/search <query> [--tags TAG1,TAG2] [--limit N]

Search through stored memories using query text.

Options:
  <query>           Search query text
  --tags TAG1,TAG2  Filter by tags (comma-separated)
  --limit N         Maximum results (default: 5)

Examples:
  /search authentication
  /search login --tags auth,security --limit 10
  /search refactor --tags python
"""

    def stop(self) -> None:
        """Stop CLI"""
        self.is_running = False


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Michael - Local Coding Agent")
    parser.add_argument(
        "--model", "-m",
        default=os.environ.get("MODEL_NAME", "gemma4:latest"),
        help="Model name"
    )
    parser.add_argument(
        "--provider", "-p",
        choices=["ollama", "rsxermu"],
        default=os.environ.get("ACTIVE_PROVIDER", "ollama"),
        help="Provider"
    )
    parser.add_argument(
        "--base-url", "-u",
        default=None,
        help="API Base URL"
    )
    parser.add_argument(
        "--workspace", "-w",
        default="workspace",
        help="Workspace directory"
    )
    parser.add_argument(
        "--api-key", "-k",
        default=None,
        help="API Key"
    )

    args = parser.parse_args()

    # Determine base URL
    if args.base_url:
        base_url = args.base_url
    elif args.provider == "ollama":
        base_url = os.environ.get("OLLAMA_HOST", "http://192.168.0.124:11434")
    else:
        base_url = os.environ.get("RSXERMU_BASE_URL", "https://rsxermu666.cn")

    cli = MichaelCLI(
        workspace=args.workspace,
        model=args.model,
        provider=args.provider,
        base_url=base_url,
        api_key=args.api_key,
    )

    try:
        cli.run()
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()