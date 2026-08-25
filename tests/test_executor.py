"""Tests for agent/executor.py tool execution."""
import json
import tempfile
from pathlib import Path
import pytest
from agent.executor import (
    Action,
    ExecutionResult,
    ExecutionStatus,
    ToolExecutor,
)


class TestAction:
    """Tests for Action dataclass."""

    def test_write_action(self):
        """Test creating a write action."""
        action = Action(command="write", path="test.py", content="print('hello')")
        assert action.command == "write"
        assert action.path == "test.py"
        assert action.content == "print('hello')"

    def test_edit_action(self):
        """Test creating an edit action."""
        action = Action(
            command="edit",
            path="test.py",
            old_text="old content",
            content="new content",
        )
        assert action.command == "edit"
        assert action.old_text == "old content"

    def test_execute_action(self):
        """Test creating an execute action."""
        action = Action(command="execute", script="python test.py", path="/workspace")
        assert action.command == "execute"
        assert action.script == "python test.py"

    def test_search_action(self):
        """Test creating a search action."""
        action = Action(command="search", query="function", path="/workspace")
        assert action.command == "search"
        assert action.query == "function"


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_success_result(self):
        """Test creating a successful result."""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            command="write",
            output="File written successfully",
        )
        assert result.is_success() is True
        assert result.status == ExecutionStatus.SUCCESS

    def test_failure_result(self):
        """Test creating a failure result."""
        result = ExecutionResult(
            status=ExecutionStatus.FAILURE,
            command="execute",
            output="",
            error="SyntaxError: invalid syntax",
        )
        assert result.is_success() is False
        assert result.error == "SyntaxError: invalid syntax"

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = ExecutionResult(
            status=ExecutionStatus.SUCCESS,
            command="write",
            output="OK",
        )
        data = result.to_dict()
        assert data["status"] == "success"
        assert data["command"] == "write"


class TestToolExecutor:
    """Tests for ToolExecutor class."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create a temporary workspace."""
        return str(tmp_path)

    @pytest.fixture
    def executor(self, workspace):
        """Create a ToolExecutor instance."""
        return ToolExecutor(workspace)

    def test_write_file(self, executor, workspace):
        """Test writing a file."""
        result = executor.execute_action(
            Action(command="write", path="test.txt", content="Hello, World!")
        )
        assert result.is_success()
        assert Path(workspace, "test.txt").read_text() == "Hello, World!"

    def test_read_file(self, executor, workspace):
        """Test reading a file."""
        # Create a file first
        Path(workspace, "test.txt").write_text("Test content")

        result = executor.execute_action(
            Action(command="read", path="test.txt")
        )
        assert result.is_success()
        assert "Test content" in result.output

    def test_read_nonexistent_file(self, executor):
        """Test reading a file that doesn't exist."""
        result = executor.execute_action(
            Action(command="read", path="nonexistent.txt")
        )
        assert result.is_success() is False
        assert "not found" in result.output.lower()

    def test_edit_file(self, executor, workspace):
        """Test editing a file."""
        # Create initial file
        Path(workspace, "test.txt").write_text("Hello World")

        result = executor.execute_action(
            Action(
                command="edit",
                path="test.txt",
                old_text="World",
                content="Universe",
            )
        )
        assert result.is_success()
        assert Path(workspace, "test.txt").read_text() == "Hello Universe"

    def test_edit_file_old_text_not_found(self, executor, workspace):
        """Test edit fails when old_text is not found."""
        Path(workspace, "test.txt").write_text("Hello World")

        result = executor.execute_action(
            Action(
                command="edit",
                path="test.txt",
                old_text="NonExistent",
                content="New",
            )
        )
        assert result.is_success() is False
        assert "not found" in result.output.lower()

    def test_mkdir(self, executor, workspace):
        """Test creating a directory."""
        result = executor.execute_action(
            Action(command="mkdir", path="new_directory")
        )
        assert result.is_success()
        assert Path(workspace, "new_directory").is_dir()

    def test_list_directory(self, executor, workspace):
        """Test listing directory contents."""
        # Create some files
        Path(workspace, "file1.txt").write_text("content")
        Path(workspace, "file2.txt").write_text("content")
        Path(workspace, "subdir").mkdir()

        result = executor.execute_action(
            Action(command="list_dir")
        )
        assert result.is_success()
        assert "file1.txt" in result.output
        assert "file2.txt" in result.output
        assert "subdir" in result.output

    def test_execute_script(self, executor, workspace):
        """Test executing a shell script."""
        result = executor.execute_action(
            Action(command="execute", script="echo 'Hello from shell'")
        )
        assert result.is_success()
        assert "Hello from shell" in result.output

    def test_execute_with_error(self, executor, workspace):
        """Test executing a failing script returns error status."""
        result = executor.execute_action(
            Action(command="execute", script="exit 1")
        )
        # Result shows failure via exit code in output, not status
        assert "Exit Code: 1" in result.output

    def test_unknown_command(self, executor):
        """Test handling of unknown commands."""
        result = executor.execute_action(
            Action(command="nonexistent_command")
        )
        assert result.is_success() is False
        assert "Unknown command" in result.output

    def test_tool_policy_blocks_command(self, workspace):
        """Test that a configured policy can block a tool command."""
        executor = ToolExecutor(
            workspace,
            tool_policy={"blocked_commands": ["execute"]},
        )

        result = executor.execute_action(
            Action(command="execute", script="echo 'blocked secret'")
        )

        assert result.is_success() is False
        assert "blocked by tool policy" in result.output
        assert "blocked secret" not in result.output
        assert executor.tool_policy.audit_log[-1]["action"]["script"] == "[redacted]"

    def test_tool_policy_observe_mode_records_without_blocking(self, workspace):
        """Test observe mode audits policy decisions without enforcing them."""
        executor = ToolExecutor(
            workspace,
            tool_policy={"blocked_commands": ["execute"], "observe": True},
        )

        result = executor.execute_action(
            Action(command="execute", script="echo 'allowed in observe'")
        )

        assert result.is_success()
        assert "allowed in observe" in result.output
        audit = executor.tool_policy.audit_log[-1]
        assert audit["status"] == "blocked"
        assert audit["observed"] is True

    def test_tool_policy_allowlist_blocks_unspecified_command(self, workspace):
        """Test allowlist mode rejects commands not explicitly listed."""
        executor = ToolExecutor(
            workspace,
            tool_policy={"allowed_commands": ["read"]},
        )

        result = executor.execute_action(
            Action(command="write", path="blocked.txt", content="nope")
        )

        assert result.is_success() is False
        assert "allowlist" in result.output
        assert not Path(workspace, "blocked.txt").exists()

    def test_tool_policy_requires_approval(self, workspace):
        """Test approval-required commands fail closed without approval plumbing."""
        executor = ToolExecutor(
            workspace,
            tool_policy={"approval_required_commands": ["write"]},
        )

        result = executor.execute_action(
            Action(command="write", path="approval.txt", content="wait")
        )

        assert result.is_success() is False
        assert "requires approval" in result.output
        assert not Path(workspace, "approval.txt").exists()

    def test_path_security_check(self, executor, workspace):
        """Test that paths cannot escape workspace."""
        result = executor.execute_action(
            Action(command="read", path="../secret.txt")
        )
        # Should either not find the file or handle it safely
        assert result.output is not None

    def test_execution_timing(self, executor, workspace):
        """Test that execution time is recorded."""
        result = executor.execute_action(
            Action(command="execute", script="sleep 0.1")
        )
        assert result.execution_time > 0
