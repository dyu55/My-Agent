"""Integration tests for cli/interface.py — CLIInterface end-to-end flows."""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from rich.console import Console

from cli.interface import CLIInterface, Mode, ChatHistory, Message


# ── Fixtures ─────────────────────────────────────────────


@pytest.fixture
def mock_model_manager():
    """Create a mock ModelManager."""
    mm = MagicMock()
    mm.current_model = "test-model"
    mm.current_provider = "test-provider"
    mm.get_status.return_value = "test-model (test-provider)"
    mm.chat.return_value = "Hello! How can I help?"
    mm.chat_stream.return_value = iter(["Hello! ", "How can I help?"])
    return mm


@pytest.fixture
def cli(tmp_path, mock_model_manager):
    """Create a CLIInterface with mocked dependencies."""
    with patch("cli.interface.ModelManager", return_value=mock_model_manager):
        c = CLIInterface(
            workspace=tmp_path,
            model="test-model",
            provider="test-provider",
            base_url="http://localhost:11434",
            default_mode=Mode.CHAT,
        )
    # Replace display console to capture output
    buf = io.StringIO()
    c.display.console = Console(file=buf, width=80, no_color=True, force_terminal=False)
    return c, buf


def _output(cli_tuple):
    """Get output from (CLI, buffer) tuple."""
    return cli_tuple[1].getvalue()


# ── Initialization ───────────────────────────────────────


class TestCLIInit:
    def test_creates_workspace(self, tmp_path, mock_model_manager):
        ws = tmp_path / "new_workspace"
        with patch("cli.interface.ModelManager", return_value=mock_model_manager):
            c = CLIInterface(workspace=ws, model="m", provider="p")
        assert ws.exists()

    def test_default_mode_is_chat(self, tmp_path, mock_model_manager):
        with patch("cli.interface.ModelManager", return_value=mock_model_manager):
            c = CLIInterface(workspace=tmp_path, model="m", provider="p")
        assert c.current_mode == Mode.CHAT

    def test_custom_default_mode(self, tmp_path, mock_model_manager):
        with patch("cli.interface.ModelManager", return_value=mock_model_manager):
            c = CLIInterface(workspace=tmp_path, model="m", provider="p", default_mode=Mode.TASK)
        assert c.current_mode == Mode.TASK

    def test_initializes_command_registry(self, cli):
        c, _ = cli
        assert c.commands is not None
        assert len(c.commands.get_all()) > 0

    def test_initializes_chat_history(self, cli):
        c, _ = cli
        assert c.history is not None
        assert len(c.history.messages) == 0

    def test_creates_prompt_tool(self, cli):
        c, _ = cli
        assert c.prompt_tool is not None


# ── Mode Switching ───────────────────────────────────────


class TestModeSwitch:
    def test_switch_from_chat_to_task(self, cli):
        c, _ = cli
        assert c.current_mode == Mode.CHAT
        c._switch_mode()
        assert c.current_mode == Mode.TASK

    def test_switch_from_task_to_chat(self, cli):
        c, _ = cli
        c.current_mode = Mode.TASK
        c._switch_mode()
        assert c.current_mode == Mode.CHAT

    def test_switch_updates_prompt_tool(self, cli):
        c, _ = cli
        with patch.object(c.prompt_tool, "set_mode") as mock_set:
            c._switch_mode()
            mock_set.assert_called_with("task")

    def test_multiple_switches(self, cli):
        c, _ = cli
        for _ in range(5):
            c._switch_mode()
        assert c.current_mode == Mode.TASK  # odd number of switches from CHAT


# ── Input Processing ─────────────────────────────────────


class TestProcessInput:
    def test_empty_input_ignored(self, cli):
        c, _ = cli
        with patch.object(c, "_handle_command") as mock_cmd:
            c._process_input("")
            mock_cmd.assert_not_called()

    def test_slash_routes_to_command(self, cli):
        c, _ = cli
        with patch.object(c, "_handle_command") as mock_cmd:
            c._process_input("/help")
            mock_cmd.assert_called_once_with("/help")

    def test_chat_mode_routes_to_chat(self, cli):
        c, _ = cli
        c.current_mode = Mode.CHAT
        with patch.object(c, "_handle_chat") as mock_chat:
            c._process_input("hello")
            mock_chat.assert_called_once_with("hello")

    def test_task_mode_routes_to_task(self, cli):
        c, _ = cli
        c.current_mode = Mode.TASK
        with patch.object(c, "_execute_task") as mock_task:
            c._process_input("build an API")
            mock_task.assert_called_once_with("build an API")


# ── Command Handling ─────────────────────────────────────


class TestHandleCommand:
    def test_mode_command(self, cli):
        c, _ = cli
        with patch.object(c, "_switch_mode") as mock_switch:
            c._handle_command("/mode")
            mock_switch.assert_called_once()

    def test_task_command_with_args(self, cli):
        c, _ = cli
        with patch.object(c, "_execute_task") as mock_exec:
            c._handle_command("/task build a REST API")
            mock_exec.assert_called_once_with("build a REST API")

    def test_task_command_no_args_shows_error(self, cli):
        c, _ = cli
        c._handle_command("/task")
        out = _output(cli)
        assert "Usage" in out or "Error" in out.lower()

    def test_model_command_no_args(self, cli):
        c, _ = cli
        # Patch _get_display so the commands module uses our captured console
        d = c.display
        with patch("cli.commands._get_display", return_value=d):
            c._handle_command("/model")
        out = _output(cli)
        assert "test-model" in out

    def test_unknown_command(self, cli):
        c, _ = cli
        d = c.display
        with patch("cli.commands._get_display", return_value=d):
            c._handle_command("/nonexistent")
        out = _output(cli)
        assert "Unknown" in out or "unknown" in out.lower()

    def test_registry_command(self, cli):
        c, _ = cli
        d = c.display
        with patch("cli.commands._get_display", return_value=d):
            c._handle_command("/status")
        out = _output(cli)
        assert "test-model" in out

    def test_help_command(self, cli):
        c, _ = cli
        d = c.display
        with patch("cli.commands._get_display", return_value=d):
            c._handle_command("/help")
        out = _output(cli)
        assert "Commands" in out

    def test_clear_command(self, cli):
        c, _ = cli
        # Should not crash
        c._handle_command("/clear")


# ── Chat Handling ────────────────────────────────────────


class TestHandleChat:
    def test_chat_calls_model(self, cli, mock_model_manager):
        c, _ = cli
        c._handle_chat("What is Python?")
        mock_model_manager.chat_stream.assert_called_once()

    def test_chat_displays_response(self, cli, mock_model_manager):
        c, _ = cli
        mock_model_manager.chat_stream.return_value = iter(["Python is ", "a programming language."])
        c._handle_chat("What is Python?")
        out = _output(cli)
        assert "Python is" in out

    def test_chat_adds_to_history(self, cli, mock_model_manager):
        c, _ = cli
        c._handle_chat("Hello")
        assert len(c.history.messages) == 2  # user + assistant
        assert c.history.messages[0].role == "user"
        assert c.history.messages[0].content == "Hello"
        assert c.history.messages[1].role == "assistant"

    def test_chat_error_handling(self, cli, mock_model_manager):
        c, _ = cli
        mock_model_manager.chat_stream.side_effect = RuntimeError("Connection failed")
        c._handle_chat("Hello")
        out = _output(cli)
        assert "Connection failed" in out or "Error" in out

    def test_chat_with_context(self, cli, mock_model_manager):
        c, _ = cli
        # Add some history
        c.history.add("user", "Previous question")
        c.history.add("assistant", "Previous answer")
        c._handle_chat("Follow up question")
        # Verify the prompt includes history
        call_args = mock_model_manager.chat_stream.call_args[0][0]
        assert "Previous question" in call_args
        assert "Follow up question" in call_args


# ── Task Execution ───────────────────────────────────────


class TestExecuteTask:
    def test_task_calls_agent(self, cli):
        c, _ = cli
        # AgentEngine is imported inside _execute_task: `from agent import AgentEngine`
        with patch("agent.AgentEngine") as mock_engine_cls:
            mock_agent = MagicMock()
            mock_agent.run.return_value = "Task completed"
            mock_engine_cls.return_value = mock_agent
            c._execute_task("Build a calculator")
            mock_agent.run.assert_called_once_with("Build a calculator")

    def test_task_increments_count(self, cli):
        c, _ = cli
        assert c.task_count == 0
        with patch("agent.AgentEngine") as mock_engine_cls:
            mock_agent = MagicMock()
            mock_agent.run.return_value = "Done"
            mock_engine_cls.return_value = mock_agent
            c._execute_task("task 1")
            c._execute_task("task 2")
        assert c.task_count == 2

    def test_task_shows_header(self, cli):
        c, _ = cli
        with patch("agent.AgentEngine") as mock_engine_cls:
            mock_agent = MagicMock()
            mock_agent.run.return_value = "Done"
            mock_engine_cls.return_value = mock_agent
            c._execute_task("Build something")
        out = _output(cli)
        assert "Task #1" in out
        assert "Build something" in out

    def test_task_shows_result(self, cli):
        c, _ = cli
        with patch("agent.AgentEngine") as mock_engine_cls:
            mock_agent = MagicMock()
            mock_agent.run.return_value = "Created 5 files"
            mock_engine_cls.return_value = mock_agent
            c._execute_task("task")
        out = _output(cli)
        assert "Created 5 files" in out

    def test_task_handles_keyboard_interrupt(self, cli):
        c, _ = cli
        with patch("agent.AgentEngine") as mock_engine_cls:
            mock_agent = MagicMock()
            mock_agent.run.side_effect = KeyboardInterrupt()
            mock_engine_cls.return_value = mock_agent
            c._execute_task("task")
        out = _output(cli)
        assert "cancel" in out.lower()

    def test_task_handles_exception(self, cli):
        c, _ = cli
        with patch("agent.AgentEngine") as mock_engine_cls:
            mock_agent = MagicMock()
            mock_agent.run.side_effect = RuntimeError("Agent crashed")
            mock_engine_cls.return_value = mock_agent
            c._execute_task("task")
        out = _output(cli)
        assert "Agent crashed" in out

    def test_task_sets_executing_flag(self, cli):
        c, _ = cli
        assert c.is_executing_task is False

        def check_flag(task):
            assert c.is_executing_task is True
            return "Done"

        with patch("agent.AgentEngine") as mock_engine_cls:
            mock_agent = MagicMock()
            mock_agent.run.side_effect = check_flag
            mock_engine_cls.return_value = mock_agent
            c._execute_task("task")

        assert c.is_executing_task is False  # Reset after

    def test_task_resets_flag_on_error(self, cli):
        c, _ = cli
        with patch("agent.AgentEngine") as mock_engine_cls:
            mock_agent = MagicMock()
            mock_agent.run.side_effect = RuntimeError("fail")
            mock_engine_cls.return_value = mock_agent
            c._execute_task("task")
        assert c.is_executing_task is False


# ── ChatHistory ──────────────────────────────────────────


class TestChatHistory:
    def test_add_message(self):
        h = ChatHistory()
        h.add("user", "Hello")
        assert len(h.messages) == 1
        assert h.messages[0].role == "user"
        assert h.messages[0].content == "Hello"

    def test_max_history(self):
        h = ChatHistory(max_history=3)
        for i in range(5):
            h.add("user", f"msg {i}")
        assert len(h.messages) == 3
        assert h.messages[0].content == "msg 2"

    def test_get_recent(self):
        h = ChatHistory()
        for i in range(10):
            h.add("user", f"msg {i}")
        recent = h.get_recent(3)
        assert len(recent) == 3
        assert recent[0].content == "msg 7"

    def test_get_conversation(self):
        h = ChatHistory()
        h.add("user", "Hello")
        h.add("assistant", "Hi there")
        conv = h.get_conversation("System prompt")
        assert conv[0]["role"] == "system"
        assert conv[0]["content"] == "System prompt"
        assert conv[1]["role"] == "user"
        assert conv[2]["role"] == "assistant"


# ── Stop ─────────────────────────────────────────────────


class TestStop:
    def test_stop_sets_flag(self, cli):
        c, _ = cli
        c.is_running = True
        c.stop()
        assert c.is_running is False
