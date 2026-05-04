"""Interactive CLI interface for chatting with the model."""

import os
import sys
import tty
import termios
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .commands import CLIContext, CommandRegistry
from utils.model_provider import ModelManager


class Mode(Enum):
    """CLI operating mode."""

    CHAT = "chat"  # Direct model conversation
    TASK = "task"  # Agent task execution (Plan/Act/Reflect)


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
    - Dual modes: CHAT (direct model) and TASK (agent execution)
    - Shift+Tab to switch between modes
    - Command handling (/help, /model, etc.)
    - Chat history management
    - Multi-model support (Ollama, OpenAI, Anthropic)
    """

    MODES = {
        Mode.CHAT: {
            "emoji": "💬",
            "label": "CHAT",
            "prompt": ">>> ",
            "description": "直接对话模式 - 直接调用模型回答问题",
        },
        Mode.TASK: {
            "emoji": "🎯",
            "label": "TASK",
            "prompt": "🎯> ",
            "description": "任务执行模式 - Agent 分解并执行任务",
        },
    }

    BANNER_TEMPLATE = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🤖 MyAgent CLI                                           ║
║                                                           ║
║   💬 CHAT: 直接对话，回答问题，写文档                      ║
║   🎯 TASK: Agent 执行，分解任务，写代码、跑测试           ║
║                                                           ║
║   {mode_indicator}                                        ║
║                                                           ║
║   输入 /help 查看可用命令                                  ║
║   输入 /mode 切换模式                                      ║
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
        default_mode: Mode = Mode.CHAT,
    ):
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.base_url = base_url
        self.api_key = api_key
        self.current_mode = default_mode

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

        # Terminal settings for raw mode
        self._old_settings: termios.tcflag_t | None = None

    def _get_banner(self) -> str:
        """Generate banner with current mode indicator."""
        mode_info = self.MODES[self.current_mode]
        mode_indicator = f"[{mode_info['emoji']} {mode_info['label']}] {mode_info['description']}"

        return self.BANNER_TEMPLATE.format(mode_indicator=mode_indicator)

    def _get_prompt(self) -> str:
        """Get current mode's prompt string."""
        return self.MODES[self.current_mode]["prompt"]

    def _get_mode_info(self) -> str:
        """Get current mode info for display."""
        mode_info = self.MODES[self.current_mode]
        return f"{mode_info['emoji']} [{mode_info['label']}]"

    def run(self) -> None:
        """Start the interactive CLI."""
        self.is_running = True
        print(self._get_banner())

        print(f"📦 模型: {self.model_manager.get_status()}")
        print(f"📁 工作目录: {self.workspace}\n")

        # Save terminal settings if available
        self._old_settings = None
        try:
            self._old_settings = termios.tcgetattr(sys.stdin)
        except Exception:
            pass  # Not available (e.g., piped/redirected stdin)

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

        # Restore terminal settings
        if self._old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self._old_settings)

        self.is_running = False

    def _read_input(self) -> str:
        """Read input with Shift+Tab mode switching support."""
        prompt = self._get_prompt()
        print(prompt, end="", flush=True)

        # Check if termios works (some environments don't support raw mode on stdin)
        try:
            fd = sys.stdin.fileno()
            termios.tcgetattr(fd)  # Test if this raises
            termios_available = True
        except Exception:
            termios_available = False

        if not termios_available or self._old_settings is None:
            # Fallback: use standard input
            return input().strip()

        # Setup terminal for raw character input
        tty.setcbreak(fd)

        line = ""
        cursor_pos = 0

        while True:
            try:
                ch = sys.stdin.read(1)

                # Check for Shift+Tab (ESC [ Z)
                if ch == "\x1b":
                    # Read next chars to check for [Z
                    seq = ch
                    ch2 = sys.stdin.read(1)
                    seq += ch2
                    if ch2 == "[":
                        ch3 = sys.stdin.read(1)
                        seq += ch3
                        if ch3 == "Z":
                            # Shift+Tab detected!
                            self._switch_mode()
                            # Clear current line and print new banner
                            print(f"\r{' ' * (len(prompt) + len(line) + 20)}\r")
                            print(self._get_banner())
                            print(f"📦 模型: {self.model_manager.get_status()}")
                            print(f"📁 工作目录: {self.workspace}\n")
                            print(prompt, end="", flush=True)
                            line = ""
                            cursor_pos = 0
                            continue

                # Handle Enter
                if ch == "\r" or ch == "\n":
                    print()
                    break

                # Handle backspace
                if ch == "\x7f" or ch == "\x08":
                    if cursor_pos > 0:
                        line = line[:cursor_pos - 1] + line[cursor_pos:]
                        cursor_pos -= 1
                        print("\b \b", end="", flush=True)
                    continue

                # Handle Ctrl+C
                if ch == "\x03":
                    print("^C")
                    return ""

                # Handle Tab - fall back to standard input
                if ch == "\t":
                    # Tab pressed, restore terminal and use standard input
                    termios.tcsetattr(fd, termios.TCSADRAIN, self._old_settings)
                    return input().strip()

                # Handle regular characters
                if ch and ch.isprintable():
                    line = line[:cursor_pos] + ch + line[cursor_pos:]
                    cursor_pos += 1
                    print(ch, end="", flush=True)

            except (KeyboardInterrupt, EOFError):
                print()
                break

        return line.strip()

    def _switch_mode(self) -> None:
        """Switch between CHAT and TASK modes."""
        if self.current_mode == Mode.CHAT:
            self.current_mode = Mode.TASK
            mode_info = self.MODES[self.current_mode]
            print(f"\n{mode_info['emoji']} [{mode_info['label']}] 已切换到任务执行模式")
            print("   输入任务描述，让 Agent 分解并执行")
        else:
            self.current_mode = Mode.CHAT
            mode_info = self.MODES[self.current_mode]
            print(f"\n{mode_info['emoji']} [{mode_info['label']}] 已切换到直接对话模式")
            print("   输入问题或指令，直接调用模型回答")

    def _process_input(self, user_input: str) -> None:
        """Process user input based on current mode."""
        # Skip empty input
        if not user_input.strip():
            return

        # Check for commands first (works in all modes)
        if user_input.startswith("/"):
            self._handle_command(user_input)
            return

        # Non-command input: route based on mode
        if self.current_mode == Mode.CHAT:
            self._handle_chat(user_input)
        else:
            self._handle_task(user_input)

    def _handle_command(self, user_input: str) -> None:
        """Handle a CLI command."""
        parts = user_input.split(maxsplit=1)
        cmd_name = parts[0]
        args = parts[1].split() if len(parts) > 1 else []

        # Handle /mode switch
        if cmd_name.lstrip("/") in ["mode"]:
            self._switch_mode()
            return

        # Handle /task in TASK mode or explicitly
        if cmd_name.lstrip("/") in ["task", "t"]:
            if args:
                self._execute_task(" ".join(args))
            else:
                print("❌ 请提供任务描述: /task <描述>")
            return

        # Handle model/provider via command handler
        if cmd_name.lstrip("/") in ["model", "m"]:
            self.commands._cmd_model(self.context, args)
            return

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
        """Handle chat message (direct model conversation)."""
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

    def _handle_task(self, user_input: str) -> None:
        """Handle task input (delegate to agent engine)."""
        self._execute_task(user_input)

    def _execute_task(self, task: str) -> None:
        """Execute a task using the agent."""
        from agent import AgentEngine
        from agent.engine import AgentConfig

        print(f"\n🎯 开始执行任务: {task}\n")
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
    parser.add_argument(
        "--mode",
        "-M",
        default="chat",
        choices=["chat", "task"],
        help="默认模式: chat (直接对话) 或 task (任务执行)",
    )

    args = parser.parse_args()

    # Determine base URL based on provider
    if args.base_url:
        base_url = args.base_url
    elif args.provider == "ollama":
        base_url = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    else:
        base_url = "http://localhost:11434"

    # Parse default mode
    default_mode = Mode.TASK if args.mode == "task" else Mode.CHAT

    cli = CLIInterface(
        workspace=args.workspace,
        model=args.model,
        provider=args.provider,
        base_url=base_url,
        api_key=args.api_key,
        default_mode=default_mode,
    )

    try:
        cli.run()
    except KeyboardInterrupt:
        print("\n再见!")


if __name__ == "__main__":
    main()