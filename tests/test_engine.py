"""Tests for agent/engine.py core functionality."""
import json
import pytest
from agent.engine import (
    _extract_json_from_response,
    AgentConfig,
    AgentState,
)


class TestExtractJsonFromResponse:
    """Tests for JSON extraction from LLM responses."""

    def test_direct_json_parse(self):
        """Test parsing valid JSON directly."""
        data = {"command": "write", "path": "test.py", "content": "print('hello')"}
        response = json.dumps(data)
        result = _extract_json_from_response(response)
        assert result == data

    def test_json_in_markdown_block(self):
        """Test extracting JSON from markdown code block."""
        response = '''
Here is the JSON:

```json
{"command": "write", "path": "test.py"}
```

That's the output.
'''
        result = _extract_json_from_response(response)
        assert result == {"command": "write", "path": "test.py"}

    def test_json_in_plain_backticks(self):
        """Test extracting JSON from plain backticks."""
        response = '''
The result is:
```
{"command": "read", "path": "main.py"}
```
'''
        result = _extract_json_from_response(response)
        assert result == {"command": "read", "path": "main.py"}

    def test_json_array_in_markdown(self):
        """Test extracting JSON array from response."""
        response = '''
```json
[
  {"id": "task_1", "description": "First task"},
  {"id": "task_2", "description": "Second task"}
]
```
'''
        result = _extract_json_from_response(response)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_invalid_json_returns_none(self):
        """Test that invalid JSON returns None."""
        response = "This is not JSON at all"
        result = _extract_json_from_response(response)
        assert result is None

    def test_non_string_input(self):
        """Test handling of non-string input."""
        result = _extract_json_from_response({"key": "value"})
        assert result == {"key": "value"}

    def test_json_with_whitespace(self):
        """Test JSON with extra whitespace."""
        response = '   {"command": "test"}   '
        result = _extract_json_from_response(response)
        assert result == {"command": "test"}


class TestAgentConfig:
    """Tests for AgentConfig dataclass."""

    def test_default_values(self, tmp_path):
        """Test default configuration values."""
        config = AgentConfig(workspace=tmp_path)
        assert config.model == "qwen3.5:9b"
        assert config.provider == "ollama"
        assert config.base_url == "http://localhost:11434"
        assert config.api_key is None
        assert config.max_task_retries == 3
        assert config.max_plan_retries == 2
        assert config.enable_llm_reflection is True
        assert config.trace_enabled is True
        assert config.progress_callback is None

    def test_custom_values(self, tmp_path):
        """Test custom configuration values."""
        callback = lambda p, t, e: None
        config = AgentConfig(
            workspace=tmp_path,
            model="qwen3.5:9b",
            provider="ollama",
            base_url="http://192.168.0.100:11434",
            api_key="test-key",
            max_task_retries=5,
            max_plan_retries=3,
            enable_llm_reflection=False,
            trace_enabled=False,
            progress_callback=callback,
        )
        assert config.model == "qwen3.5:9b"
        assert config.provider == "ollama"
        assert config.base_url == "http://192.168.0.100:11434"
        assert config.api_key == "test-key"
        assert config.max_task_retries == 5
        assert config.max_plan_retries == 3
        assert config.enable_llm_reflection is False
        assert config.trace_enabled is False
        assert config.progress_callback is callback


class TestAgentState:
    """Tests for AgentState dataclass."""

    def test_default_values(self):
        """Test default state values."""
        state = AgentState()
        assert state.current_plan is None
        assert state.current_task_id is None
        assert state.task_attempts == 0
        assert state.total_llm_calls == 0
        assert state.execution_history == []
        assert state.is_complete is False
        assert state.final_result is None
        assert state.force_write_command is False

    def test_force_write_command_flag(self):
        """Test force_write_command flag can be toggled."""
        state = AgentState()
        assert state.force_write_command is False
        state.force_write_command = True
        assert state.force_write_command is True
