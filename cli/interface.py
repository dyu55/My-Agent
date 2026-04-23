"""Interactive CLI interface for chatting with the model."""

import json
import os
import readline
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .commands import CLIContext, CommandRegistry
from utils.model_provider import ModelManager


@dataclass
class Message:
    """A chat message."""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ChatHistory:
    """Manages chat history."""

    messages: list[Message] = field(default_factory=list)
    max_history: int = 100

    def add(self, role: str, content: str) -> None:
        """Add a message to history."""
        self.messages.append(Message(role=role, content=content))
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

    def get_conversation(self, system_prompt: str) -> list[dict[str, str]]:
        """Get messages formatted for API."""
        result = [{"role": "system", "content": system_prompt}]
        for msg in self.messages:
            result.append({"role": msg.role, "content": msg.content})
        return result

    def get_recent(self, count: int = 10) -> list[Message]:
        """Get recent messages."""
        return self.messages[-count:]


class CLIInterface:
    """
    Interactive CLI for chatting with the model.

    Features:
    - REPL loop for continuous conversation
    - Command handling (/help, /model, etc.)
    - Chat history management
    - Streaming output
    - Task execution integration
    - Multi-model support (Ollama, OpenAI, Anthropic)
    """

    BANNER = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🤖 MyAgent CLI - 与模型对话                              ║
║                                                           ║
║   输入 /help 查看可用命令                                  ║
║   输入 /task <描述> 让 agent 执行任务                      ║
║   输入 /model 查看/切换模型                               ║
║   输入 exit 或 /quit 退出                                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""

    SYSTEM_PROMPT = """你是一个有帮助的 AI 助手。用户正在通过 CLI 与你对话。

你可以:
- 回答问题
- 帮助调试代码
- 解释概念
- 提供建议

尽量简洁明了。如果需要执行代码，使用 /run 命令格式。
"""

    def __init__(
        self,
        workspace: Path | str = "workspace",
        model: str = "gemma4:latest",
        provider: str = "ollama",
        base_url: str = "http://localhost:11434",
        api_key: str | None = None,
    ):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.base_url = base_url
        self.api_key = api_key

        # Initialize model manager
        self.model_manager = ModelManager(
            default_provider=provider,
            default_model=model,
        )

        self.commands = CommandRegistry()
        self.history = ChatHistory()
        self.context = CLIContext(
            model_manager=self.model_manager,
            workspace=self.workspace,
        )

        self.is_running = False
        self.is_executing_task = False

    def run(self) -> None:
        """Start the interactive CLI."""
        self.is_running = True
        print(self.BANNER)

        print(f"📦 模型: {self.model_manager.get_status()}")
        print(f"📁 工作目录: {self.workspace}\n")

        self._setup_readline()

        while self.is_running:
            try:
                user_input = self._read_input()
                if not user_input:
                    continue

                self._process_input(user_input)

            except KeyboardInterrupt:
                print("\n(输入 /exit 退出)")
            except EOFError:
                print("\n再见!")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}")

        self.is_running = False

    def _setup_readline(self) -> None:
        """Setup readline for better input experience."""
        try:
            readline.parse_and_bind("tab: complete")
            readline.parse_and_bind("set editing-mode vi")
        except Exception:
            pass  # Ignore readline errors

    def _read_input(self) -> str:
        """Read input from user."""
        try:
            return input(">>> ").strip()
        except (KeyboardInterrupt, EOFError):
            raise

    def _process_input(self, user_input: str) -> None:
        """Process user input."""
        # Skip empty input
        if not user_input.strip():
            return

        # Check for commands
        if user_input.startswith("/"):
            self._handle_command(user_input)
        else:
            self._handle_chat(user_input)

    def _handle_command(self, user_input: str) -> None:
        """Handle a CLI command."""
        parts = user_input.split(maxsplit=1)
        cmd_name = parts[0]
        args = parts[1].split() if len(parts) > 1 else []

        # Handle /task specially
        if cmd_name.lstrip("/") in ["task", "t"]:
            if args:
                self._execute_task(" ".join(args))
            else:
                print("❌ 请提供任务描述: /task <描述>")
            return

        # Handle /model via command handler
        if cmd_name.lstrip("/") in ["model", "m"]:
            self.commands._cmd_model(self.context, args)
            return

        # Handle /provider via command handler
        if cmd_name.lstrip("/") in ["provider", "p"]:
            self.commands._cmd_provider(self.context, args)
            return

        # Find and execute command
        cmd = self.commands.find(cmd_name)
        if cmd and cmd.handler:
            cmd.handler(self.context, args)
        else:
            print(f"❌ 未知命令: {cmd_name}")
            print("   输入 /help 查看可用命令")

    def _handle_chat(self, user_input: str) -> None:
        """Handle chat message."""
        print()  # Spacing

        # Add to history
        self.history.add("user", user_input)

        # Build prompt from history
        prompt = self.SYSTEM_PROMPT
        for msg in self.history.get_recent(10):
            prompt += f"\n\n{msg.role.upper()}: {msg.content}"

        try:
            # Send to model
            response = self.model_manager.chat(prompt)

            # Print response
            print(response)

            # Add response to history
            self.history.add("assistant", response)

        except Exception as e:
            print(f"❌ LLM 调用失败: {e}")
            print("   请检查模型服务是否运行中")

    def _execute_task(self, task: str) -> None:
        """Execute a task using the agent."""
        from agent import AgentEngine
        from agent.engine import AgentConfig

        print(f"\n🔄 开始执行任务: {task}\n")
        print("=" * 60)
        self.is_executing_task = True
        self.context.is_executing_task = True

        try:
            config = AgentConfig(
                workspace=self.workspace,
                model=self.model_manager.current_model,
                provider=self.model_manager.current_provider,
                base_url=self.base_url,
                api_key=self.api_key,
            )
            agent = AgentEngine(config)
            result = agent.run(task)

            self.context.task_result = result
            print(f"\n{'=' * 60}")
            print(f"✅ 任务完成: {result}")

        except Exception as e:
            print(f"\n❌ 任务执行失败: {e}")
        finally:
            self.is_executing_task = False
            self.context.is_executing_task = False

    def stop(self) -> None:
        """Stop the CLI."""
        self.is_running = False


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="MyAgent CLI - 与本地模型对话")
    parser.add_argument("--model", "-m", default=os.environ.get("MODEL_NAME", "gemma4:latest"), help="模型名称")
    parser.add_argument("--provider", "-p", default=os.environ.get("ACTIVE_PROVIDER", "ollama"), help="Provider")
    parser.add_argument("--base-url", "-u", default=None, help="API Base URL")
    parser.add_argument("--workspace", "-w", default="workspace", help="工作目录")
    parser.add_argument("--api-key", "-k", default=None, help="API Key")

    args = parser.parse_args()

    # Determine base URL based on provider
    if args.base_url:
        base_url = args.base_url
    elif args.provider == "ollama":
        base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    elif args.provider == "rsxermu":
        base_url = os.environ.get("RSXERMU_BASE_URL", "https://rsxermu666.cn")
    else:
        base_url = "http://localhost:11434"

    cli = CLIInterface(
        workspace=args.workspace,
        model=args.model,
        provider=args.provider,
        base_url=base_url,
        api_key=args.api_key,
    )

    try:
        cli.run()
    except KeyboardInterrupt:
        print("\n再见!")


if __name__ == "__main__":
    main()