"""Unit tests for cli/commands.py."""

import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from cli.commands import Command, CommandRegistry, CLIContext


# ── Helpers ──────────────────────────────────────────────


@pytest.fixture
def mock_ctx(tmp_path):
    """Create a mock CLIContext."""
    ctx = MagicMock(spec=CLIContext)
    ctx.current_model = "gemma4:latest"
    ctx.current_provider = "ollama"
    ctx.workspace = tmp_path
    ctx.is_executing_task = False
    ctx.task_result = None
    ctx.mcp_client = None
    ctx.current_monitor = None
    ctx.external_memory_manager = None
    ctx.model_manager = MagicMock()
    ctx.model_manager.current_model = "gemma4:latest"
    ctx.model_manager.current_provider = "ollama"
    ctx.model_manager.get_status.return_value = "gemma4:latest (ollama)"
    return ctx


@pytest.fixture
def registry():
    """Create a fresh CommandRegistry."""
    return CommandRegistry()


@pytest.fixture
def mock_display():
    """Mock the Display module used by commands."""
    buf = io.StringIO()
    console = Console(file=buf, width=80, no_color=True, force_terminal=False)
    d = MagicMock()
    d.console = console
    d.help_table = MagicMock()
    d.status_panel = MagicMock()
    d.context_panel = MagicMock()
    d.model_info = MagicMock()
    d.provider_list = MagicMock()
    d.directory_listing = MagicMock()
    d.command_output = MagicMock()
    d.error = MagicMock()
    d.success = MagicMock()
    d.info = MagicMock()
    d.warning = MagicMock()
    d.plain = MagicMock()
    d.stream_text = MagicMock()
    d.mcp_status = MagicMock()
    d.spinner = MagicMock()
    d.spinner.return_value.__enter__ = MagicMock()
    d.spinner.return_value.__exit__ = MagicMock()
    return d, buf


# ── Command dataclass ────────────────────────────────────


class TestCommand:
    def test_matches_exact_name(self):
        cmd = Command(name="help", description="Help", aliases=["h"])
        assert cmd.matches("/help") is True

    def test_matches_alias(self):
        cmd = Command(name="help", description="Help", aliases=["h", "?"])
        assert cmd.matches("/h") is True
        assert cmd.matches("/?") is True

    def test_no_match(self):
        cmd = Command(name="help", description="Help", aliases=["h"])
        assert cmd.matches("/exit") is False

    def test_matches_strips_slash(self):
        cmd = Command(name="help", description="Help")
        assert cmd.matches("/help") is True

    def test_matches_case_insensitive(self):
        cmd = Command(name="Help", description="Help", aliases=["H"])
        assert cmd.matches("/help") is True
        assert cmd.matches("/HELP") is True

    def test_matches_with_args(self):
        cmd = Command(name="run", description="Run", aliases=["!"])
        assert cmd.matches("/run ls -la") is True

    def test_no_match_empty_string(self):
        cmd = Command(name="help", description="Help")
        assert cmd.matches("") is False


# ── CommandRegistry ──────────────────────────────────────


class TestCommandRegistry:
    def test_register_adds_command(self, registry):
        initial_count = len(registry.get_all())
        registry.register(Command(name="custom", description="Custom"))
        assert len(registry.get_all()) == initial_count + 1

    def test_find_existing_command(self, registry):
        cmd = registry.find("/help")
        assert cmd is not None
        assert cmd.name == "help"

    def test_find_by_alias(self, registry):
        cmd = registry.find("/h")
        assert cmd is not None
        assert cmd.name == "help"

    def test_find_nonexistent(self, registry):
        cmd = registry.find("/nonexistent")
        assert cmd is None

    def test_builtins_registered(self, registry):
        all_cmds = registry.get_all()
        names = {c.name for c in all_cmds}
        assert "help" in names
        assert "exit" in names
        assert "clear" in names
        assert "model" in names
        assert "provider" in names
        assert "run" in names
        assert "task" in names
        assert "ls" in names
        assert "status" in names
        assert "mcp" in names

    def test_find_with_args(self, registry):
        cmd = registry.find("/run ls")
        assert cmd is not None
        assert cmd.name == "run"


# ── Command Handlers ─────────────────────────────────────


class TestCmdHelp:
    def test_help_calls_display(self, registry, mock_ctx, mock_display):
        d, buf = mock_display
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_help(mock_ctx, [])
        d.help_table.assert_called_once()
        args = d.help_table.call_args[0][0]
        # Should have all registered commands
        assert len(args) > 10
        # Each entry is (cmd_str, description, category)
        cmd_strings = [a[0] for a in args]
        assert any("/help" in s for s in cmd_strings)


class TestCmdExit:
    def test_exit_stops_monitor(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        mock_ctx.current_monitor = MagicMock()
        with patch("cli.commands._get_display", return_value=d):
            with pytest.raises(SystemExit):
                registry._cmd_exit(mock_ctx, [])
        mock_ctx.current_monitor.stop.assert_called_once()

    def test_exit_without_monitor(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        mock_ctx.current_monitor = None
        with patch("cli.commands._get_display", return_value=d):
            with pytest.raises(SystemExit):
                registry._cmd_exit(mock_ctx, [])


class TestCmdClear:
    def test_clear_calls_display(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_clear(mock_ctx, [])
        d.clear.assert_called_once()


class TestCmdModel:
    def test_model_no_args_shows_info(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_model(mock_ctx, [])
        d.model_info.assert_called_once_with("gemma4:latest", "ollama")

    def test_model_switch_success(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        mock_ctx.model_manager.set_model.return_value = True
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_model(mock_ctx, ["qwen:9b"])
        mock_ctx.model_manager.set_model.assert_called_once_with("ollama", "qwen:9b")
        d.success.assert_called_once()

    def test_model_switch_with_provider(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        mock_ctx.model_manager.set_model.return_value = True
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_model(mock_ctx, ["openai/gpt-4"])
        mock_ctx.model_manager.set_model.assert_called_once_with("openai", "gpt-4")

    def test_model_switch_failure(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        mock_ctx.model_manager.set_model.return_value = False
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_model(mock_ctx, ["bad-model"])
        d.error.assert_called_once()


class TestCmdProvider:
    def test_provider_no_args_shows_list(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        with patch("cli.commands._get_display", return_value=d):
            with patch("cli.commands.ModelProviderFactory") as mock_factory:
                mock_factory.list_providers.return_value = ["ollama", "openai"]
                registry._cmd_provider(mock_ctx, [])
        d.provider_list.assert_called_once()

    def test_provider_switch(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        mock_ctx.model_manager.set_model.return_value = True
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_provider(mock_ctx, ["openai"])
        mock_ctx.model_manager.set_model.assert_called_once_with("openai", None)
        d.success.assert_called_once()


class TestCmdContext:
    def test_context_shows_info(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_context(mock_ctx, [])
        d.context_panel.assert_called_once()
        args = d.context_panel.call_args[0][0]
        assert args["Model"] == "gemma4:latest"
        assert args["Provider"] == "ollama"

    def test_context_with_task_result(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        mock_ctx.task_result = "Task completed successfully"
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_context(mock_ctx, [])
        args = d.context_panel.call_args[0][0]
        assert "Last result" in args


class TestCmdLs:
    def test_ls_shows_files(self, registry, mock_ctx, mock_display, tmp_path):
        d, _ = mock_display
        (tmp_path / "test.py").write_text("print('hi')")
        (tmp_path / "src").mkdir()
        mock_ctx.workspace = tmp_path
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_ls(mock_ctx, [])
        d.directory_listing.assert_called_once()
        entries = d.directory_listing.call_args[0][1]
        names = [e[0] for e in entries]
        assert "test.py" in names
        assert "src" in names

    def test_ls_nonexistent_path(self, registry, mock_ctx, mock_display, tmp_path):
        d, _ = mock_display
        mock_ctx.workspace = tmp_path
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_ls(mock_ctx, ["nonexistent"])
        d.error.assert_called_once()

    def test_ls_with_subdir(self, registry, mock_ctx, mock_display, tmp_path):
        d, _ = mock_display
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "file.txt").write_text("content")
        mock_ctx.workspace = tmp_path
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_ls(mock_ctx, ["sub"])
        d.directory_listing.assert_called_once()
        entries = d.directory_listing.call_args[0][1]
        names = [e[0] for e in entries]
        assert "file.txt" in names

    def test_ls_empty_dir(self, registry, mock_ctx, mock_display, tmp_path):
        d, _ = mock_display
        empty = tmp_path / "empty"
        empty.mkdir()
        mock_ctx.workspace = tmp_path
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_ls(mock_ctx, ["empty"])
        d.directory_listing.assert_called_once()
        entries = d.directory_listing.call_args[0][1]
        assert len(entries) == 0


class TestCmdCd:
    def test_cd_no_args(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_cd(mock_ctx, [])
        d.success.assert_called_once()

    def test_cd_existing_dir(self, registry, mock_ctx, mock_display, tmp_path):
        d, _ = mock_display
        subdir = tmp_path / "sub"
        subdir.mkdir()
        mock_ctx.workspace = tmp_path
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_cd(mock_ctx, ["sub"])
        d.success.assert_called_once()
        assert mock_ctx.workspace == subdir.resolve()

    def test_cd_nonexistent(self, registry, mock_ctx, mock_display, tmp_path):
        d, _ = mock_display
        mock_ctx.workspace = tmp_path
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_cd(mock_ctx, ["nonexistent"])
        d.error.assert_called_once()


class TestCmdRun:
    def test_run_no_args(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_run(mock_ctx, [])
        d.error.assert_called_once()

    def test_run_success(self, registry, mock_ctx, mock_display, tmp_path):
        d, _ = mock_display
        mock_ctx.workspace = tmp_path
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_run(mock_ctx, ["echo", "hello"])
        d.command_output.assert_called_once()
        output = d.command_output.call_args[0][0]
        assert "hello" in output

    def test_run_with_stderr(self, registry, mock_ctx, mock_display, tmp_path):
        d, _ = mock_display
        mock_ctx.workspace = tmp_path
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_run(mock_ctx, ["python", "-c", "import sys; sys.stderr.write('err\\n')"])
        d.command_output.assert_called_once()


class TestCmdStatus:
    def test_status_shows_info(self, registry, mock_ctx, mock_display):
        d, _ = mock_display
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_status(mock_ctx, [])
        d.status_panel.assert_called_once()
        args = d.status_panel.call_args[0][0]
        assert args["Model"] == "gemma4:latest"
        assert args["Task running"] == "No"


class TestCmdTaskStub:
    def test_task_stub_does_nothing(self, registry, mock_ctx, mock_display):
        """The /task command is handled by interface, not the registry."""
        d, _ = mock_display
        with patch("cli.commands._get_display", return_value=d):
            registry._cmd_task(mock_ctx, ["some task"])
        # Should not call any display method
        d.help_table.assert_not_called()
        d.error.assert_not_called()
