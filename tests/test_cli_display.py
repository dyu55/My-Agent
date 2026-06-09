"""Unit tests for cli/display.py."""

import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from rich.console import Console

from cli.display import Display


@pytest.fixture
def display():
    """Create a Display instance with captured output."""
    buf = io.StringIO()
    d = Display()
    d.console = Console(file=buf, width=80, no_color=True, force_terminal=False)
    return d, buf


def _output(display_tuple):
    """Get the string output from a (Display, buffer) tuple."""
    return display_tuple[1].getvalue()


class TestBanner:
    def test_banner_renders_model_info(self, display):
        d, buf = display
        d.banner("gemma4:latest", "ollama", Path("/tmp/ws"), "TASK")
        out = _output(display)
        assert "gemma4:latest" in out
        assert "ollama" in out
        assert "/tmp/ws" in out
        assert "TASK" in out

    def test_banner_renders_chat_mode(self, display):
        d, buf = display
        d.banner("model", "provider", Path("/tmp"), "CHAT")
        out = _output(display)
        assert "CHAT" in out
        assert "MyAgent CLI" in out

    def test_banner_shows_help_hint(self, display):
        d, buf = display
        d.banner("m", "p", Path("/tmp"), "CHAT")
        out = _output(display)
        assert "/help" in out


class TestHelpTable:
    def test_help_table_renders_commands(self, display):
        d, buf = display
        commands = [
            ("/help, /h, /?", "Show help", ""),
            ("/exit, /quit, /q", "Exit CLI", ""),
            ("/run, /!", "Run command", ""),
        ]
        d.help_table(commands)
        out = _output(display)
        assert "Show help" in out
        assert "Exit CLI" in out
        assert "Run command" in out

    def test_help_table_empty(self, display):
        d, buf = display
        d.help_table([])
        out = _output(display)
        assert "Commands" in out


class TestStatusPanel:
    def test_status_panel_renders_data(self, display):
        d, buf = display
        d.status_panel({"Model": "gemma4", "Provider": "ollama"})
        out = _output(display)
        assert "gemma4" in out
        assert "ollama" in out
        assert "Status" in out


class TestContextPanel:
    def test_context_panel_renders(self, display):
        d, buf = display
        d.context_panel({"Model": "test", "Workspace": "/tmp"})
        out = _output(display)
        assert "test" in out
        assert "/tmp" in out
        assert "Context" in out


class TestTaskDisplay:
    def test_task_header(self, display):
        d, buf = display
        d.task_header(1, "Build a REST API")
        out = _output(display)
        assert "Task #1" in out
        assert "Build a REST API" in out

    def test_task_result_success(self, display):
        d, buf = display
        d.task_result("Created 3 files", success=True)
        out = _output(display)
        assert "Created 3 files" in out
        assert "Done" in out

    def test_task_result_failure(self, display):
        d, buf = display
        d.task_result("Syntax error", success=False)
        out = _output(display)
        assert "Syntax error" in out
        assert "Failed" in out

    def test_task_cancelled(self, display):
        d, buf = display
        d.task_cancelled()
        out = _output(display)
        assert "cancelled" in out.lower()


class TestMessages:
    def test_error(self, display):
        d, buf = display
        d.error("Something broke")
        out = _output(display)
        assert "Something broke" in out

    def test_success(self, display):
        d, buf = display
        d.success("All good")
        out = _output(display)
        assert "All good" in out

    def test_info(self, display):
        d, buf = display
        d.info("FYI")
        out = _output(display)
        assert "FYI" in out

    def test_warning(self, display):
        d, buf = display
        d.warning("Careful")
        out = _output(display)
        assert "Careful" in out

    def test_plain(self, display):
        d, buf = display
        d.plain("raw text")
        out = _output(display)
        assert "raw text" in out


class TestStreamText:
    def test_plain_text(self, display):
        d, buf = display
        d.stream_text("Hello world")
        out = _output(display)
        assert "Hello world" in out

    def test_markdown_text(self, display):
        d, buf = display
        d.stream_text("## Heading\n\nSome **bold** text")
        out = _output(display)
        assert "Heading" in out

    def test_code_block(self, display):
        d, buf = display
        d.stream_text("```python\nprint('hi')\n```")
        out = _output(display)
        assert "print" in out


class TestFileContent:
    def test_file_content_with_syntax(self, display):
        d, buf = display
        d.file_content(
            Path("test.py"),
            "def hello():\n    return 'hi'",
            lexer="python",
        )
        out = _output(display)
        assert "def hello" in out
        assert "test.py" in out

    def test_file_content_auto_detect(self, display):
        d, buf = display
        d.file_content(Path("data.json"), '{"key": "value"}')
        out = _output(display)
        assert "key" in out


class TestCommandOutput:
    def test_command_output(self, display):
        d, buf = display
        d.command_output("line 1\nline 2", title="Shell")
        out = _output(display)
        assert "line 1" in out
        assert "line 2" in out
        assert "Shell" in out


class TestDirectoryListing:
    def test_directory_listing_with_files_and_dirs(self, display):
        d, buf = display
        entries = [
            ("src", True, ""),
            ("main.py", False, "1.2K"),
            ("README.md", False, "3.4K"),
        ]
        d.directory_listing(Path("/tmp/ws"), entries)
        out = _output(display)
        assert "src" in out
        assert "main.py" in out
        assert "README.md" in out
        assert "1.2K" in out
        assert "DIR" in out

    def test_directory_listing_empty(self, display):
        d, buf = display
        d.directory_listing(Path("/tmp/empty"), [])
        out = _output(display)
        assert "empty" in out


class TestModelInfo:
    def test_model_info_basic(self, display):
        d, buf = display
        d.model_info("gemma4", "ollama")
        out = _output(display)
        assert "gemma4" in out
        assert "ollama" in out

    def test_model_info_with_available(self, display):
        d, buf = display
        d.model_info("gemma4", "ollama", available=["gemma4", "qwen"])
        out = _output(display)
        assert "gemma4" in out
        assert "qwen" in out


class TestProviderList:
    def test_provider_list(self, display):
        d, buf = display
        d.provider_list("ollama", ["ollama", "openai", "anthropic"])
        out = _output(display)
        assert "ollama" in out
        assert "openai" in out
        assert "current" in out


class TestMcpStatus:
    def test_mcp_status(self, display):
        d, buf = display
        servers = {
            "fs": {"state": "connected", "tools": ["read", "write"]},
            "db": {"state": "disconnected", "tools": []},
        }
        d.mcp_status(servers)
        out = _output(display)
        assert "fs" in out
        assert "db" in out
        assert "connected" in out
        assert "read" in out


class TestDivider:
    def test_divider(self, display):
        d, buf = display
        d.divider()
        out = _output(display)
        assert "─" in out


class TestClear:
    def test_clear_does_not_crash(self, display):
        d, buf = display
        d.clear()  # Should not raise
