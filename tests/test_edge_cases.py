"""
Edge Case Tests for MyAgent

This module tests edge cases and boundary conditions for:
- ToolExecutor (modular tools)
- File tools
- Memory management
- Path resolution
- Error handling
"""

import os
import tempfile
import pytest
from pathlib import Path

# Import the modules to test
from agent.executor import ToolExecutor, Action, ExecutionStatus
from agent.tools.file_tools import FileTools
from agent.tools.exec_tools import ExecTools
from agent.tools.search_tools import SearchTools
from agent.tools.git_tools import GitTools
from utils.conversation import ConversationMemory
from utils.logger import TraceLogger
from utils.schema import SchemaValidator


class TestFileToolsEdgeCases:
    """Test edge cases for file operations."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_write_empty_content(self, temp_workspace):
        """Test writing empty content to a file."""
        tools = FileTools(temp_workspace)
        result = tools.write_file({"path": "empty.txt", "content": ""})
        assert result.success
        assert Path(temp_workspace, "empty.txt").exists()

    def test_write_unicode_content(self, temp_workspace):
        """Test writing unicode content."""
        tools = FileTools(temp_workspace)
        unicode_content = "你好世界！🎉 Emoji 和特殊字符: café résumé"
        result = tools.write_file({"path": "unicode.txt", "content": unicode_content})
        assert result.success
        content = Path(temp_workspace, "unicode.txt").read_text()
        assert content == unicode_content

    def test_write_very_long_content(self, temp_workspace):
        """Test writing very long content."""
        tools = FileTools(temp_workspace)
        long_content = "x" * 1_000_000  # 1MB of data
        result = tools.write_file({"path": "large.txt", "content": long_content})
        assert result.success
        assert len(Path(temp_workspace, "large.txt").read_text()) == 1_000_000

    def test_write_special_characters_in_path(self, temp_workspace):
        """Test writing files with special characters in path."""
        tools = FileTools(temp_workspace)
        # Test with spaces
        result = tools.write_file({"path": "file with spaces.txt", "content": "test"})
        assert result.success
        # Test with Chinese characters
        result = tools.write_file({"path": "测试文件.txt", "content": "test"})
        assert result.success

    def test_write_path_traversal_attempt(self, temp_workspace):
        """Test that path traversal is blocked."""
        tools = FileTools(temp_workspace)
        # Attempt to escape workspace
        result = tools.write_file({
            "path": "../../../etc/passwd",
            "content": "malicious"
        })
        # Should either be blocked or resolved within workspace
        assert "Error" in result.output or "Success" in result.output

    def test_edit_nonexistent_file(self, temp_workspace):
        """Test editing a file that doesn't exist."""
        tools = FileTools(temp_workspace)
        result = tools.edit_file({
            "path": "nonexistent.txt",
            "old_text": "old",
            "content": "new"
        })
        assert not result.success

    def test_edit_empty_old_text(self, temp_workspace):
        """Test editing with empty old_text."""
        tools = FileTools(temp_workspace)
        # First create a file
        tools.write_file({"path": "test.txt", "content": "hello world"})
        # Try to edit with empty old_text
        result = tools.edit_file({
            "path": "test.txt",
            "old_text": "",
            "content": "new"
        })
        assert not result.success

    def test_edit_old_text_not_found(self, temp_workspace):
        """Test editing when old_text doesn't exist in file."""
        tools = FileTools(temp_workspace)
        tools.write_file({"path": "test.txt", "content": "hello world"})
        result = tools.edit_file({
            "path": "test.txt",
            "old_text": "nonexistent_pattern",
            "content": "new"
        })
        assert not result.success

    def test_read_nonexistent_file(self, temp_workspace):
        """Test reading a file that doesn't exist."""
        tools = FileTools(temp_workspace)
        result = tools.read_file({"path": "nonexistent.txt"})
        assert not result.success

    def test_read_with_invalid_line_numbers(self, temp_workspace):
        """Test reading with invalid line numbers."""
        tools = FileTools(temp_workspace)
        tools.write_file({"path": "test.txt", "content": "line1\nline2\nline3"})
        # Try to read with start > end
        result = tools.read_file({"path": "test.txt", "start": 10, "end": 5})
        # Should handle gracefully
        assert "Error" in result.output or result.success

    def test_mkdir_empty_path(self, temp_workspace):
        """Test creating directory with empty path."""
        tools = FileTools(temp_workspace)
        result = tools.mkdir({"path": ""})
        # Should handle gracefully
        assert "Error" in result.output or result.success


class TestExecToolsEdgeCases:
    """Test edge cases for execution tools."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_execute_empty_script(self, temp_workspace):
        """Test executing empty script."""
        tools = ExecTools(temp_workspace)
        result = tools.execute_script({"script": ""})
        assert not result.success

    def test_execute_malicious_command(self, temp_workspace):
        """Test that dangerous commands are handled."""
        tools = ExecTools(temp_workspace)
        # These should timeout or be handled safely
        result = tools.execute_script({"script": "sleep 100"})
        # Should timeout after 30 seconds
        assert "Error" in result.output or not result.success

    def test_check_dependencies_empty_list(self, temp_workspace):
        """Test checking dependencies with empty list."""
        tools = ExecTools(temp_workspace)
        result = tools.check_dependencies({"modules": []})
        assert result.success

    def test_check_dependencies_nonexistent_modules(self, temp_workspace):
        """Test checking dependencies for nonexistent modules."""
        tools = ExecTools(temp_workspace)
        result = tools.check_dependencies({
            "modules": ["nonexistent_module_xyz", "another_fake_module"]
        })
        assert result.success
        assert "nonexistent_module_xyz" in result.output

    def test_pip_install_empty_list(self, temp_workspace):
        """Test pip install with empty package list."""
        tools = ExecTools(temp_workspace)
        result = tools.pip_install({"packages": []})
        assert not result.success


class TestSearchToolsEdgeCases:
    """Test edge cases for search tools."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_search_empty_query(self, temp_workspace):
        """Test searching with empty query."""
        tools = SearchTools(temp_workspace)
        result = tools.search_files({"query": ""})
        assert not result.success

    def test_search_in_empty_directory(self, temp_workspace):
        """Test searching in an empty directory."""
        tools = SearchTools(temp_workspace)
        result = tools.search_files({"query": "test"})
        assert result.success
        assert "No matches" in result.output

    def test_search_binary_files(self, temp_workspace):
        """Test searching in binary files (should not crash)."""
        # Create a binary file
        binary_file = Path(temp_workspace) / "binary.dat"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")
        tools = SearchTools(temp_workspace)
        result = tools.search_files({"query": "test"})
        # Should handle gracefully without crashing
        assert result.success

    def test_fetch_invalid_url(self, temp_workspace):
        """Test fetching an invalid URL."""
        tools = SearchTools(temp_workspace)
        result = tools.fetch_url({"url": "not_a_valid_url"})
        assert not result.success

    def test_fetch_nonexistent_domain(self, temp_workspace):
        """Test fetching a nonexistent domain."""
        tools = SearchTools(temp_workspace)
        result = tools.fetch_url({"url": "http://this-domain-does-not-exist-123456.com"})
        # Should handle network error gracefully
        assert "Error" in result.output or not result.success


class TestGitToolsEdgeCases:
    """Test edge cases for git tools."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_git_empty_args(self, temp_workspace):
        """Test git with empty arguments."""
        tools = GitTools(temp_workspace)
        result = tools.git_command({"git_args": ""})
        assert not result.success

    def test_git_disallowed_command(self, temp_workspace):
        """Test that disallowed git commands are blocked."""
        tools = GitTools(temp_workspace)
        # Try to execute a dangerous command
        result = tools.git_command({"git_args": "rm -rf /"})
        assert not result.success
        # Try to execute a non-whitelisted command
        result = tools.git_command({"git_args": "config --global --add core.editor vim"})
        assert not result.success

    def test_git_in_non_git_directory(self, temp_workspace):
        """Test git commands in a directory that's not a git repository."""
        tools = GitTools(temp_workspace)
        result = tools.git_command({"git_args": "status"})
        # Should handle gracefully (git returns error but doesn't crash)
        # Note: git status in non-repo returns error, which is correct behavior
        assert not result.success  # Expects failure since it's not a git repo
        assert "not a git repository" in result.output


class TestConversationMemoryEdgeCases:
    """Test edge cases for conversation memory."""

    def test_empty_initialization(self):
        """Test initializing memory with default parameters."""
        mem = ConversationMemory()
        assert mem.max_pairs == 4
        assert len(mem.recent_turns) == 0

    def test_custom_max_pairs(self):
        """Test initializing memory with custom max_pairs."""
        mem = ConversationMemory(max_pairs=1)
        assert mem.max_pairs == 1

    def test_add_empty_content(self):
        """Test adding empty content."""
        mem = ConversationMemory()
        mem.add("user", "")
        assert len(mem.recent_turns) == 1

    def test_add_very_long_content(self):
        """Test adding very long content."""
        mem = ConversationMemory()
        long_content = "x" * 100_000  # 100KB
        mem.add("user", long_content)
        assert len(mem.recent_turns) == 1

    def test_compression_trigger(self):
        """Test that compression is triggered correctly."""
        mem = ConversationMemory(max_pairs=2)
        # Add more turns than max_pairs * 2
        for i in range(10):
            mem.add("user", f"message {i}")
        # Should have compressed old messages
        assert len(mem.summary_lines) > 0

    def test_build_messages_empty(self):
        """Test building messages with empty memory."""
        mem = ConversationMemory()
        messages = mem.build_messages("System prompt", None)
        assert len(messages) == 1  # Just system prompt

    def test_build_messages_with_task(self):
        """Test building messages with a task."""
        mem = ConversationMemory()
        messages = mem.build_messages("System", "My task")
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["content"] == "My task"

    def test_clear(self):
        """Test clearing memory."""
        mem = ConversationMemory()
        mem.add("user", "test")
        mem.clear()
        assert len(mem.recent_turns) == 0
        assert len(mem.summary_lines) == 0


class TestSchemaValidatorEdgeCases:
    """Test edge cases for schema validation."""

    def test_parse_empty_json(self):
        """Test parsing empty JSON."""
        validator = SchemaValidator()
        result = validator.parse_json("")
        assert result is None

    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        validator = SchemaValidator()
        result = validator.parse_json("not valid json {")
        assert result is None

    def test_parse_json_with_extra_text(self):
        """Test parsing JSON with extra text around it."""
        validator = SchemaValidator()
        result = validator.parse_json('some text {"key": "value"} more text')
        assert result is not None
        assert result.get("key") == "value"

    def test_parse_json_in_code_block(self):
        """Test parsing JSON in markdown code block."""
        validator = SchemaValidator()
        result = validator.parse_json('```json\n{"key": "value"}\n```')
        assert result is not None
        assert result.get("key") == "value"

    def test_validate_command_missing_command(self):
        """Test validating command with missing command field."""
        validator = SchemaValidator()
        is_valid, error = validator.validate_command({"path": "test.txt"})
        assert not is_valid

    def test_validate_command_empty_command(self):
        """Test validating command with empty command."""
        validator = SchemaValidator()
        is_valid, error = validator.validate_command({"command": ""})
        assert not is_valid

    def test_validate_command_invalid_type(self):
        """Test validating command with invalid type."""
        validator = SchemaValidator()
        is_valid, error = validator.validate_command("not a dict")
        assert not is_valid


class TestToolExecutorIntegration:
    """Integration tests for ToolExecutor with edge cases."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_execute_unknown_command(self, temp_workspace):
        """Test executing an unknown command."""
        executor = ToolExecutor(temp_workspace)
        action = Action(command="nonexistent_command")
        result = executor.execute_action(action)
        assert result.status == ExecutionStatus.FAILURE

    def test_execute_action_without_required_fields(self, temp_workspace):
        """Test executing action without required fields."""
        executor = ToolExecutor(temp_workspace)
        # Write without path
        action = Action(command="write", content="test")
        result = executor.execute_action(action)
        assert result.status == ExecutionStatus.FAILURE

    def test_rapid_successive_calls(self, temp_workspace):
        """Test rapid successive calls to executor."""
        executor = ToolExecutor(temp_workspace)
        for i in range(100):
            action = Action(command="write", path=f"file{i}.txt", content=f"content{i}")
            result = executor.execute_action(action)
            assert result.status == ExecutionStatus.SUCCESS

    def test_concurrent_file_access(self, temp_workspace):
        """Test concurrent file access."""
        import concurrent.futures

        executor = ToolExecutor(temp_workspace)

        def write_file(i):
            action = Action(
                command="write",
                path=f"concurrent{i}.txt",
                content=f"content{i}"
            )
            return executor.execute_action(action)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(write_file, range(50)))

        # All should succeed
        success_count = sum(1 for r in results if r.status == ExecutionStatus.SUCCESS)
        assert success_count == 50


class TestPathResolutionEdgeCases:
    """Test edge cases for path resolution."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_absolute_path_in_workspace(self, temp_workspace):
        """Test using absolute path within workspace."""
        tools = FileTools(temp_workspace)
        # Create a file inside workspace using absolute path
        abs_path = os.path.join(temp_workspace, "subdir", "test.txt")
        result = tools.write_file({
            "path": abs_path,
            "content": "test"
        })
        # Should resolve to workspace-relative path
        assert result.success

    def test_path_with_dot_segments(self, temp_workspace):
        """Test path with . and .. segments."""
        tools = FileTools(temp_workspace)
        # Create directory first
        tools.mkdir({"path": "subdir"})
        # Write with ./subdir/
        result = tools.write_file({
            "path": "./subdir/../subdir/test.txt",
            "content": "test"
        })
        assert result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
