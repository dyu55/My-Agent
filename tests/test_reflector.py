"""Tests for agent/reflector.py result reflection."""
import pytest
from agent.reflector import (
    ErrorCategory,
    Reflection,
    ResultReflector,
)


class TestReflection:
    """Tests for Reflection dataclass."""

    def test_successful_reflection(self):
        """Test creating a successful reflection."""
        reflection = Reflection(
            is_successful=True,
            error_category=None,
            error_message=None,
            suggestion=None,
            should_retry=False,
            should_abandon=False,
        )
        assert reflection.is_successful is True
        assert reflection.error_category is None
        assert reflection.should_retry is False

    def test_failed_reflection(self):
        """Test creating a failed reflection."""
        reflection = Reflection(
            is_successful=False,
            error_category=ErrorCategory.SYNTAX_ERROR,
            error_message="IndentationError",
            suggestion="Fix indentation",
            should_retry=True,
            should_abandon=False,
        )
        assert reflection.is_successful is False
        assert reflection.error_category == ErrorCategory.SYNTAX_ERROR
        assert "IndentationError" in reflection.error_message

    def test_reflection_to_dict(self):
        """Test converting reflection to dictionary."""
        reflection = Reflection(
            is_successful=False,
            error_category=ErrorCategory.LOGIC_ERROR,
            error_message="TypeError",
            suggestion="Check types",
            should_retry=True,
            should_abandon=False,
        )
        result = reflection.to_dict()
        assert result["is_successful"] is False
        assert result["error_category"] == "logic_error"
        assert result["should_retry"] is True


class TestResultReflector:
    """Tests for ResultReflector class."""

    def test_successful_execution(self):
        """Test reflecting on successful execution."""
        reflector = ResultReflector()
        result = reflector.reflect(
            action_command="write",
            execution_output="Success: File written",
            is_error=False,
        )
        assert result.is_successful is True
        assert result.error_category is None
        assert result.should_retry is False

    def test_syntax_error_classification(self):
        """Test automatic classification of syntax errors."""
        reflector = ResultReflector()
        result = reflector.reflect(
            action_command="execute",
            execution_output="SyntaxError: invalid syntax",
            is_error=True,
        )
        assert result.is_successful is False
        assert result.error_category == ErrorCategory.SYNTAX_ERROR
        assert result.should_retry is True

    def test_logic_error_classification(self):
        """Test automatic classification of logic errors."""
        reflector = ResultReflector()
        result = reflector.reflect(
            action_command="execute",
            execution_output="AttributeError: 'NoneType' object has no attribute 'foo'",
            is_error=True,
        )
        assert result.error_category == ErrorCategory.LOGIC_ERROR
        assert result.should_retry is True

    def test_tool_error_classification(self):
        """Test automatic classification of tool errors."""
        reflector = ResultReflector()
        result = reflector.reflect(
            action_command="write",
            execution_output="Permission denied",
            is_error=True,
        )
        assert result.error_category == ErrorCategory.TOOL_ERROR
        assert result.should_retry is False

    def test_dependency_error_classification(self):
        """Test automatic classification of dependency errors."""
        reflector = ResultReflector()
        result = reflector.reflect(
            action_command="execute",
            execution_output="ModuleNotFoundError: No module named 'numpy'",
            is_error=True,
        )
        assert result.error_category == ErrorCategory.DEPENDENCY_ERROR
        assert result.should_retry is True
        assert "pip_install" in result.suggestion.lower()

    def test_unknown_error(self):
        """Test handling of unknown errors."""
        reflector = ResultReflector()
        result = reflector.reflect(
            action_command="execute",
            execution_output="Something unexpected happened",
            is_error=True,
        )
        assert result.error_category == ErrorCategory.UNKNOWN
        assert result.should_retry is True

    def test_reflection_history(self):
        """Test that reflections are recorded in history."""
        reflector = ResultReflector()
        reflector.reflect("write", "Success", False)
        reflector.reflect("execute", "SyntaxError", True)
        assert len(reflector.reflection_history) == 2

    def test_extract_error_message(self):
        """Test extracting clean error message."""
        reflector = ResultReflector()
        output = """
Some context lines
Error: KeyError at line 42
More context
Exception: ValueError: invalid value
"""
        message = reflector._extract_error_message(output)
        assert "KeyError" in message
        assert "ValueError" in message

    def test_reflection_summary(self):
        """Test getting reflection summary."""
        reflector = ResultReflector()
        reflector.reflect("write", "Success", False)
        reflector.reflect("execute", "Error", True)
        summary = reflector.get_reflection_summary()
        assert "2" in summary
        assert "1" in summary  # 1 successful


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_error_categories(self):
        """Test all error categories exist."""
        assert ErrorCategory.SYNTAX_ERROR.value == "syntax_error"
        assert ErrorCategory.LOGIC_ERROR.value == "logic_error"
        assert ErrorCategory.TOOL_ERROR.value == "tool_error"
        assert ErrorCategory.MODEL_HALLUCINATION.value == "model_hallucination"
        assert ErrorCategory.DEPENDENCY_ERROR.value == "dependency_error"
        assert ErrorCategory.UNKNOWN.value == "unknown"
