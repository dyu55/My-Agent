"""Integration tests for AgentEngine — progress callbacks and model-aware prompts."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from agent.engine import AgentConfig, AgentEngine, LLMClient, AgentState
from agent.executor import Action, ExecutionResult, ExecutionStatus
from agent.planner import TaskStatus


class TestAgentConfig:
    """Test AgentConfig defaults."""

    def test_default_config(self):
        config = AgentConfig(workspace=Path("/tmp/test"))
        assert config.model == "qwen3.5:9b"
        assert config.provider == "ollama"
        assert config.max_task_retries == 3
        assert config.progress_callback is None

    def test_custom_config(self):
        cb = MagicMock()
        config = AgentConfig(
            workspace=Path("/tmp/test"),
            model="llama3:70b",
            provider="openai",
            progress_callback=cb,
        )
        assert config.model == "llama3:70b"
        assert config.progress_callback is cb


class TestAgentState:
    """Test AgentState dataclass."""

    def test_default_state(self):
        state = AgentState()
        assert state.current_plan is None
        assert state.is_complete is False
        assert state.force_write_command is False
        assert state.execution_history == []

    def test_force_write_command_flag(self):
        state = AgentState()
        state.force_write_command = True
        assert state.force_write_command is True


class TestLLMClient:
    """Test LLMClient wrapper."""

    @patch("agent.engine.ModelManager")
    def test_chat_delegates_to_model_manager(self, mock_mm_cls):
        mock_mm = MagicMock()
        mock_mm.chat.return_value = "response"
        mock_mm_cls.return_value = mock_mm

        config = AgentConfig(workspace=Path("/tmp/test"))
        client = LLMClient(config)
        result = client.chat("hello")

        assert result == "response"

    @patch("agent.engine.ModelManager")
    def test_current_model(self, mock_mm_cls):
        mock_mm = MagicMock()
        mock_mm.get_status.return_value = "qwen3:8b (ollama)"
        mock_mm_cls.return_value = mock_mm

        config = AgentConfig(workspace=Path("/tmp/test"))
        client = LLMClient(config)
        assert "qwen3" in client.current_model


class TestEngineModelProfile:
    """Test that AgentEngine creates and uses ModelProfile."""

    @patch("agent.engine.get_cross_session_memory")
    @patch("agent.engine.TraceLogger")
    @patch("agent.engine.PersistentMemory")
    @patch("agent.engine.ToolExecutor")
    @patch("agent.engine.ResultReflector")
    @patch("agent.engine.TaskPlanner")
    @patch("agent.engine.LLMClient")
    def test_small_model_profile_loaded(self, mock_llm, mock_planner, mock_reflector,
                                         mock_executor, mock_persistent, mock_logger,
                                         mock_cross_mem):
        config = AgentConfig(workspace=Path("/tmp/test"), model="qwen3:8b")
        engine = AgentEngine(config)

        assert engine.model_profile.size_category == "small"
        assert engine.model_profile.prefer_short_prompts is True

    @patch("agent.engine.get_cross_session_memory")
    @patch("agent.engine.TraceLogger")
    @patch("agent.engine.PersistentMemory")
    @patch("agent.engine.ToolExecutor")
    @patch("agent.engine.ResultReflector")
    @patch("agent.engine.TaskPlanner")
    @patch("agent.engine.LLMClient")
    def test_large_model_profile_loaded(self, mock_llm, mock_planner, mock_reflector,
                                         mock_executor, mock_persistent, mock_logger,
                                         mock_cross_mem):
        config = AgentConfig(workspace=Path("/tmp/test"), model="llama3:70b")
        engine = AgentEngine(config)

        assert engine.model_profile.size_category == "large"
        assert engine.model_profile.prefer_short_prompts is False


class TestBuildActionPrompt:
    """Test _build_action_prompt with different model profiles."""

    def _make_engine(self, model_name: str) -> AgentEngine:
        """Create a minimal engine for testing prompts."""
        with patch("agent.engine.LLMClient"), \
             patch("agent.engine.TaskPlanner"), \
             patch("agent.engine.ToolExecutor"), \
             patch("agent.engine.ResultReflector"), \
             patch("agent.engine.PersistentMemory"), \
             patch("agent.engine.TraceLogger"), \
             patch("agent.engine.get_cross_session_memory"):
            config = AgentConfig(workspace=Path("/tmp/test"), model=model_name)
            return AgentEngine(config)

    def test_small_model_uses_short_prompt(self):
        engine = self._make_engine("qwen3:8b")
        task = MagicMock()
        task.description = "Create a hello world script"

        prompt = engine._build_action_prompt(task, "", False)

        assert len(prompt) < 500  # Short prompt
        assert "JSON" in prompt
        assert "hello world" in prompt.lower()

    def test_small_model_force_write(self):
        engine = self._make_engine("qwen3:8b")
        task = MagicMock()
        task.description = "Fix the bug"

        prompt = engine._build_action_prompt(task, "", True)

        assert "write" in prompt.lower()
        assert len(prompt) < 500

    def test_large_model_uses_full_prompt(self):
        engine = self._make_engine("llama3:70b")
        task = MagicMock()
        task.description = "Create a complex application"

        prompt = engine._build_action_prompt(task, "", False)

        assert len(prompt) > 500  # Full prompt
        assert "programming assistant" in prompt
        assert "write" in prompt

    def test_small_model_truncates_execution_summary(self):
        engine = self._make_engine("qwen3:8b")
        task = MagicMock()
        task.description = "Do something"

        long_summary = "x" * 500
        prompt = engine._build_action_prompt(task, long_summary, False)

        # The summary should be truncated to 200 chars in short prompt
        assert "x" * 201 not in prompt


class TestProgressCallback:
    """Test progress callback integration in engine."""

    def _make_engine_with_callback(self, callback):
        with patch("agent.engine.LLMClient"), \
             patch("agent.engine.TaskPlanner"), \
             patch("agent.engine.ToolExecutor"), \
             patch("agent.engine.ResultReflector"), \
             patch("agent.engine.PersistentMemory"), \
             patch("agent.engine.TraceLogger"), \
             patch("agent.engine.get_cross_session_memory"):
            config = AgentConfig(
                workspace=Path("/tmp/test"),
                model="qwen3:8b",
                progress_callback=callback,
            )
            return AgentEngine(config)

    def test_callback_called_during_run(self):
        callback = MagicMock()
        engine = self._make_engine_with_callback(callback)

        # Mock the planner to return a simple plan
        from agent.planner import ExecutionPlan, SubTask
        plan = ExecutionPlan(
            main_goal="test",
            subtasks=[SubTask(id="task_1", description="do stuff")],
        )
        engine.planner.create_plan.return_value = plan

        # Mock the executor
        result = ExecutionResult(
            command="write",
            status=ExecutionStatus.SUCCESS,
            output="done",
        )
        engine.executor.execute_action.return_value = result

        # Mock the LLM to return a valid action JSON
        engine.llm.chat.return_value = '{"command": "write", "path": "test.py", "content": "x"}'

        # Mock reflector
        from agent.reflector import Reflection
        engine.reflector.reflect.return_value = Reflection(
            is_successful=True,
            error_category=None,
            error_message=None,
            suggestion=None,
            should_retry=False,
            should_abandon=False,
        )

        engine.run("test task")

        # Callback should have been called at least for plan and act phases
        assert callback.call_count >= 2
        phases = [c[0][0] for c in callback.call_args_list]
        assert "plan" in phases


class TestGetProjectContext:
    """Test _get_project_context respects model profile limits."""

    def test_small_model_limits_files(self, tmp_path):
        # Create 20 files
        for i in range(20):
            (tmp_path / f"file_{i}.py").write_text("x")

        with patch("agent.engine.LLMClient"), \
             patch("agent.engine.TaskPlanner"), \
             patch("agent.engine.ToolExecutor"), \
             patch("agent.engine.ResultReflector"), \
             patch("agent.engine.PersistentMemory"), \
             patch("agent.engine.TraceLogger"), \
             patch("agent.engine.get_cross_session_memory"):
            config = AgentConfig(workspace=tmp_path, model="qwen3:8b")
            engine = AgentEngine(config)

        context = engine._get_project_context()
        lines = [l for l in context.split("\n") if l.startswith("[FILE]")]

        # Small model should limit to 10 files
        assert len(lines) <= 10

    def test_large_model_allows_more_files(self, tmp_path):
        # Create 40 files
        for i in range(40):
            (tmp_path / f"file_{i}.py").write_text("x")

        with patch("agent.engine.LLMClient"), \
             patch("agent.engine.TaskPlanner"), \
             patch("agent.engine.ToolExecutor"), \
             patch("agent.engine.ResultReflector"), \
             patch("agent.engine.PersistentMemory"), \
             patch("agent.engine.TraceLogger"), \
             patch("agent.engine.get_cross_session_memory"):
            config = AgentConfig(workspace=tmp_path, model="llama3:70b")
            engine = AgentEngine(config)

        context = engine._get_project_context()
        lines = [l for l in context.split("\n") if l.startswith("[FILE]")]

        # Large model should show up to 50 files
        assert len(lines) == 40  # All 40 fit within 50 limit
