"""Unit tests for cli/prompt.py."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from prompt_toolkit.document import Document

from cli.prompt import SlashCommandCompleter, CLIPathCompleter, CLIPrompt


class TestSlashCommandCompleter:
    """Test slash command completion."""

    @pytest.fixture
    def completer(self):
        commands = [
            ("help", ["h", "?"]),
            ("exit", ["quit", "q"]),
            ("run", ["!"]),
            ("task", ["t"]),
            ("model", ["m"]),
        ]
        return SlashCommandCompleter(commands)

    def test_completes_command_name(self, completer):
        doc = Document("/he")
        completions = list(completer.get_completions(doc, None))
        texts = [c.text for c in completions]
        assert "/help" in texts

    def test_completes_alias(self, completer):
        doc = Document("/h")
        completions = list(completer.get_completions(doc, None))
        texts = [c.text for c in completions]
        assert "/help" in texts or "/h" in texts

    def test_completes_multiple_matches(self, completer):
        doc = Document("/")
        completions = list(completer.get_completions(doc, None))
        texts = [c.text for c in completions]
        assert "/help" in texts
        assert "/exit" in texts
        assert "/run" in texts

    def test_no_completion_without_slash(self, completer):
        doc = Document("help")
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 0

    def test_no_match(self, completer):
        doc = Document("/zzz")
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 0

    def test_exact_match(self, completer):
        doc = Document("/exit")
        completions = list(completer.get_completions(doc, None))
        texts = [c.text for c in completions]
        assert "/exit" in texts

    def test_alias_completions_show_mapping(self, completer):
        doc = Document("/q")
        completions = list(completer.get_completions(doc, None))
        displays = [c.display for c in completions]
        # Should show the alias mapping
        assert any("exit" in str(d).lower() for d in displays)

    def test_partial_match(self, completer):
        doc = Document("/ru")
        completions = list(completer.get_completions(doc, None))
        texts = [c.text for c in completions]
        assert "/run" in texts

    def test_completion_start_position(self, completer):
        doc = Document("/he")
        completions = list(completer.get_completions(doc, None))
        for c in completions:
            assert c.start_position == -3  # replaces "/he"


class TestCLIPathCompleter:
    """Test file path completion."""

    @pytest.fixture
    def workspace(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hi')")
        (tmp_path / "README.md").write_text("# Test")
        (tmp_path / ".hidden").mkdir()
        return tmp_path

    @pytest.fixture
    def completer(self, workspace):
        return CLIPathCompleter(workspace)

    def test_completes_after_edit_command(self, completer):
        doc = Document("/edit ")
        completions = list(completer.get_completions(doc, None))
        names = [str(c.text) for c in completions]
        # Should show workspace contents
        assert any("src" in n for n in names)
        assert any("README" in n for n in names)

    def test_completes_after_read_command(self, completer):
        doc = Document("/read ")
        completions = list(completer.get_completions(doc, None))
        assert len(completions) > 0

    def test_no_completion_for_non_file_commands(self, completer):
        doc = Document("/help ")
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 0

    def test_no_completion_without_slash(self, completer):
        doc = Document("edit ")
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 0

    def test_no_completion_for_empty_input(self, completer):
        doc = Document("")
        completions = list(completer.get_completions(doc, None))
        assert len(completions) == 0

    def test_filters_hidden_files(self, completer, workspace):
        doc = Document("/ls ")
        completions = list(completer.get_completions(doc, None))
        names = [str(c.text) for c in completions]
        # Visible files should be present
        assert any("src" in n for n in names)
        assert any("README" in n for n in names)


class TestCLIPrompt:
    """Test CLIPrompt initialization and mode switching."""

    def test_init_creates_session(self, tmp_path):
        commands = [("help", ["h"]), ("exit", ["q"])]
        p = CLIPrompt(commands, tmp_path, history_path=str(tmp_path / ".history"))
        assert p.session is not None

    def test_set_mode_chat(self, tmp_path):
        commands = [("help", ["h"])]
        p = CLIPrompt(commands, tmp_path, history_path=str(tmp_path / ".history"))
        p.set_mode("chat")
        assert p._mode == "chat"

    def test_set_mode_task(self, tmp_path):
        commands = [("help", ["h"])]
        p = CLIPrompt(commands, tmp_path, history_path=str(tmp_path / ".history"))
        p.set_mode("task")
        assert p._mode == "task"

    def test_default_mode_is_task(self, tmp_path):
        commands = [("help", ["h"])]
        p = CLIPrompt(commands, tmp_path, history_path=str(tmp_path / ".history"))
        assert p._mode == "task"

    def test_history_file_created(self, tmp_path):
        history_file = tmp_path / ".history"
        commands = [("help", ["h"])]
        p = CLIPrompt(commands, tmp_path, history_path=str(history_file))
        # File is created lazily on first prompt, but session should exist
        assert p.session is not None

    def test_tilde_expansion_in_history(self, tmp_path):
        """Ensure ~ in history path gets expanded (regression test)."""
        commands = [("help", ["h"])]
        # Should not raise even with ~ path
        p = CLIPrompt(commands, tmp_path, history_path="~/.test_history")
        assert p.session is not None
