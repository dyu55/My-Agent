"""Interactive CLI interface for MyAgent."""

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .commands import CLIContext, CommandRegistry
from .display import Display
from .prompt import CLIPrompt
from utils.model_provider import ModelManager


class Mode(Enum):
    """CLI operating mode."""

    CHAT = "chat"
    TASK = "task"


@dataclass
class Message:
    """A chat message."""

    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ChatHistory:
    """Manages chat history."""

    messages: list[Message] = field(default_factory=list)
    max_history: int = 100

    def add(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

    def get_conversation(self, system_prompt: str) -> list[dict[str, str]]:
        result = [{"role": "system", "content": system_prompt}]
        for msg in self.messages:
            result.append({"role": msg.role, "content": msg.content})
        return result

    def get_recent(self, count: int = 10) -> list[Message]:
        return self.messages[-count:]


class CLIInterface:
    """Interactive CLI for MyAgent with rich display and smart input."""

    SYSTEM_PROMPT = """You are a helpful AI assistant. The user is chatting with you via CLI.

You can:
- Answer questions
- Help debug code
- Explain concepts
- Give advice

Be concise. If code execution is needed, suggest using /run."""

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

        self.model_manager = ModelManager(
            default_provider=provider,
            default_model=model,
        )

        self.commands = CommandRegistry()
        self.history = ChatHistory()
        self.context = CLIContext(
            model_manager=self.model_manager,
            workspace=self.workspace,
            think_model=os.environ.get("THINK_MODEL"),
            think_provider=os.environ.get("THINK_PROVIDER"),
            execute_model=os.environ.get("EXECUTE_MODEL"),
            execute_provider=os.environ.get("EXECUTE_PROVIDER"),
        )

        self.display = Display()

        # Build prompt with command completions
        cmd_list = [(cmd.name, cmd.aliases) for cmd in self.commands.get_all()]
        # Add hardcoded aliases
        cmd_list.extend([
            ("mode", []),
        ])
        self.prompt_tool = CLIPrompt(
            commands=cmd_list,
            workspace=self.workspace,
        )

        self.is_running = False
        self.is_executing_task = False
        self.task_count = 0

    def run(self) -> None:
        """Start the interactive CLI."""
        self.is_running = True

        self.display.banner(
            model=self.model_manager.current_model,
            provider=self.model_manager.current_provider,
            workspace=self.workspace,
            mode=self.current_mode.value.upper(),
        )

        self.prompt_tool.set_mode(self.current_mode.value)

        while self.is_running:
            user_input = self.prompt_tool.prompt()

            if user_input is None:  # Ctrl+D
                self.display.info("Goodbye!")
                break

            if not user_input:
                continue

            self._process_input(user_input)

        self.is_running = False

    def _switch_mode(self) -> None:
        if self.current_mode == Mode.CHAT:
            self.current_mode = Mode.TASK
        else:
            self.current_mode = Mode.CHAT
        self.prompt_tool.set_mode(self.current_mode.value)
        mode_label = self.current_mode.value.upper()
        style = "green" if self.current_mode == Mode.TASK else "yellow"
        self.display.info(f"Switched to [{mode_label}] mode")

    def _process_input(self, user_input: str) -> None:
        if not user_input.strip():
            return

        if user_input.startswith("/"):
            self._handle_command(user_input)
            return

        if self.current_mode == Mode.CHAT:
            self._handle_chat(user_input)
        else:
            self._handle_task(user_input)

    def _handle_command(self, user_input: str) -> None:
        parts = user_input.split(maxsplit=1)
        cmd_name = parts[0]
        args = parts[1].split() if len(parts) > 1 else []

        # Handle mode switch directly
        if cmd_name.lstrip("/") in ("mode",):
            self._switch_mode()
            return

        # Handle task command directly (needs args)
        if cmd_name.lstrip("/") in ("task", "t"):
            if args:
                self._execute_task(" ".join(args))
            else:
                self.display.error("Usage: /task <description>")
            return

        # Handle model/provider directly (delegate to commands with custom flow)
        if cmd_name.lstrip("/") in ("model", "m"):
            self.commands._cmd_model(self.context, args)
            return

        if cmd_name.lstrip("/") in ("provider", "p"):
            self.commands._cmd_provider(self.context, args)
            return

        # Registry lookup
        cmd = self.commands.find(cmd_name)
        if cmd and cmd.handler:
            try:
                cmd.handler(self.context, args)
            except SystemExit:
                self.is_running = False
        else:
            self.display.error(f"Unknown command: {cmd_name}")
            self.display.info("Type /help for available commands")

    def _handle_chat(self, user_input: str) -> None:
        self.history.add("user", user_input)

        prompt = self.SYSTEM_PROMPT
        for msg in self.history.get_recent(10):
            prompt += f"\n\n{msg.role.upper()}: {msg.content}"

        try:
            response_parts = []
            for chunk in self.model_manager.chat_stream(prompt):
                self.display.console.print(chunk, end="", highlight=False)
                response_parts.append(chunk)
            self.display.console.print()  # newline after streaming
            response = "".join(response_parts)
            self.history.add("assistant", response)
        except Exception as e:
            self.display.error(f"LLM call failed: {e}")

    def _handle_task(self, user_input: str) -> None:
        self._execute_task(user_input)

    def _execute_task(self, task: str) -> None:
        from agent import AgentEngine
        from agent.engine import AgentConfig

        self.task_count += 1
        self.is_executing_task = True
        self.context.is_executing_task = True

        self.display.task_header(self.task_count, task)

        try:
            config = AgentConfig(
                workspace=self.workspace,
                model=self.model_manager.current_model,
                provider=self.model_manager.current_provider,
                base_url=self.base_url,
                api_key=self.api_key,
                progress_callback=self._on_agent_progress,
                think_model=self.context.think_model,
                think_provider=self.context.think_provider,
                execute_model=self.context.execute_model,
                execute_provider=self.context.execute_provider,
            )

            agent = AgentEngine(config)
            result = agent.run(task)

            self.context.task_result = result
            self.display.task_result(str(result), success=True)

        except KeyboardInterrupt:
            self.display.task_cancelled()
        except Exception as e:
            self.display.task_result(str(e), success=False)
        finally:
            self.is_executing_task = False
            self.context.is_executing_task = False

    def _on_agent_progress(self, phase: str, detail: str, elapsed: float = 0) -> None:
        """Callback for real-time agent progress updates."""
        from rich.text import Text
        from rich.panel import Panel

        if phase == "plan":
            self.display.console.print(
                Panel(Text(detail, style="cyan"), title="Planning", border_style="cyan", padding=(0, 1))
            )
        elif phase == "action":
            self.display.console.print(
                Panel(Text(detail, style="yellow"), title="Action", border_style="yellow", padding=(0, 1))
            )
        elif phase == "result":
            style = "green" if "Error" not in detail else "red"
            self.display.console.print(
                Panel(Text(detail[:300], style=style), title="Result", border_style=style, padding=(0, 1))
            )
        elif phase == "reflect":
            self.display.console.print(
                Panel(Text(detail, style="magenta"), title="Reflect", border_style="magenta", padding=(0, 1))
            )

    def stop(self) -> None:
        self.is_running = False
