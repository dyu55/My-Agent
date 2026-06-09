"""Targeted tests to close coverage gaps in engine, planner, reflector, and small_model."""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agent.engine import _extract_json_from_response, AgentConfig, AgentEngine, AgentState
from agent.executor import Action, ExecutionResult, ExecutionStatus
from agent.planner import ExecutionPlan, SubTask, TaskPlanner, TaskStatus
from agent.reflector import ErrorCategory, Reflection, ResultReflector
from utils.small_model import (
    ChainOfThoughtPrompts,
    FallbackResult,
    FallbackStrategy,
    ModelProfile,
    OutputValidator,
    SmallModelOptimizer,
)


# ── _extract_json_from_response ─────────────────────────


class TestExtractJsonFromResponse:
    """Test JSON extraction from various response formats."""

    def test_direct_json(self):
        result = _extract_json_from_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_code_block(self):
        result = _extract_json_from_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_json_in_plain_code_block(self):
        result = _extract_json_from_response('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_no_json_returns_none(self):
        result = _extract_json_from_response("no json here")
        assert result is None

    def test_non_string_input(self):
        result = _extract_json_from_response({"already": "dict"})
        assert result == {"already": "dict"}

    def test_json_array(self):
        result = _extract_json_from_response('[{"id": 1}]')
        assert result == [{"id": 1}]

    def test_json_with_surrounding_text(self):
        result = _extract_json_from_response('Here is the result:\n```json\n{"a": 1}\n```\nDone.')
        assert result == {"a": 1}


# ── ExecutionPlan ────────────────────────────────────────


class TestExecutionPlan:
    """Test ExecutionPlan methods."""

    def test_get_next_task_returns_first_pending(self):
        plan = ExecutionPlan(main_goal="test")
        plan.subtasks = [
            SubTask(id="t1", description="first", status=TaskStatus.COMPLETED),
            SubTask(id="t2", description="second", status=TaskStatus.PENDING),
        ]
        task = plan.get_next_task()
        assert task.id == "t2"

    def test_get_next_task_respects_dependencies(self):
        plan = ExecutionPlan(main_goal="test")
        plan.subtasks = [
            SubTask(id="t1", description="first", status=TaskStatus.PENDING),
            SubTask(id="t2", description="second", status=TaskStatus.PENDING, dependencies=["t1"]),
        ]
        task = plan.get_next_task()
        assert task.id == "t1"  # t2 is blocked by t1

    def test_get_next_task_returns_none_when_all_done(self):
        plan = ExecutionPlan(main_goal="test")
        plan.subtasks = [
            SubTask(id="t1", description="done", status=TaskStatus.COMPLETED),
        ]
        assert plan.get_next_task() is None

    def test_get_task_by_id(self):
        plan = ExecutionPlan(main_goal="test")
        plan.subtasks = [SubTask(id="t1", description="x")]
        assert plan.get_task_by_id("t1").description == "x"
        assert plan.get_task_by_id("nonexistent") is None

    def test_all_completed(self):
        plan = ExecutionPlan(main_goal="test")
        plan.subtasks = [
            SubTask(id="t1", description="x", status=TaskStatus.COMPLETED),
            SubTask(id="t2", description="y", status=TaskStatus.COMPLETED),
        ]
        assert plan.all_completed() is True

    def test_all_completed_false(self):
        plan = ExecutionPlan(main_goal="test")
        plan.subtasks = [
            SubTask(id="t1", description="x", status=TaskStatus.COMPLETED),
            SubTask(id="t2", description="y", status=TaskStatus.PENDING),
        ]
        assert plan.all_completed() is False

    def test_has_failures(self):
        plan = ExecutionPlan(main_goal="test")
        plan.subtasks = [
            SubTask(id="t1", description="x", status=TaskStatus.FAILED),
        ]
        assert plan.has_failures() is True

    def test_to_dict(self):
        plan = ExecutionPlan(main_goal="test")
        plan.subtasks = [SubTask(id="t1", description="x")]
        d = plan.to_dict()
        assert d["main_goal"] == "test"
        assert len(d["subtasks"]) == 1


class TestSubTask:
    """Test SubTask dataclass."""

    def test_to_dict(self):
        task = SubTask(id="t1", description="test", dependencies=["t0"])
        d = task.to_dict()
        assert d["id"] == "t1"
        assert d["dependencies"] == ["t0"]
        assert d["status"] == "pending"


# ── ResultReflector ──────────────────────────────────────


class TestReflectorCoverage:
    """Test uncovered reflector paths."""

    def test_reflect_success(self):
        reflector = ResultReflector()
        r = reflector.reflect("write", "File created successfully", False)
        assert r.is_successful is True
        assert r.error_category is None

    def test_reflect_read_only_on_write_task(self):
        reflector = ResultReflector()
        r = reflector.reflect("read", "file content", False, context="implement user login")
        # Read-only actions are no longer treated as failures — they succeed and move on
        assert r.is_successful is True
        assert r.should_retry is False

    def test_reflect_failed_tests(self):
        reflector = ResultReflector()
        r = reflector.reflect("run_tests", "2 failed, 3 passed\nexit code: 1", False)
        assert r.is_successful is False
        assert r.should_retry is True

    def test_classify_syntax_error(self):
        reflector = ResultReflector()
        cat = reflector._classify_error("SyntaxError: invalid syntax")
        assert cat == ErrorCategory.SYNTAX_ERROR

    def test_classify_logic_error(self):
        reflector = ResultReflector()
        cat = reflector._classify_error("AttributeError: 'NoneType' has no attribute 'x'")
        assert cat == ErrorCategory.LOGIC_ERROR

    def test_classify_tool_error(self):
        reflector = ResultReflector()
        cat = reflector._classify_error("Permission denied")
        assert cat == ErrorCategory.TOOL_ERROR

    def test_classify_dependency_error(self):
        reflector = ResultReflector()
        cat = reflector._classify_error("ModuleNotFoundError: No module named 'requests'")
        assert cat == ErrorCategory.DEPENDENCY_ERROR

    def test_classify_json_error(self):
        reflector = ResultReflector()
        cat = reflector._classify_error("json parse error in response")
        assert cat == ErrorCategory.MODEL_HALLUCINATION

    def test_classify_unknown(self):
        reflector = ResultReflector()
        cat = reflector._classify_error("Something completely unexpected happened")
        assert cat == ErrorCategory.UNKNOWN

    def test_extract_error_message(self):
        reflector = ResultReflector()
        msg = reflector._extract_error_message("line 1\nTypeError: bad type\nline 3")
        assert "TypeError" in msg

    def test_determine_retry_for_each_category(self):
        reflector = ResultReflector()
        for cat in ErrorCategory:
            should_retry, suggestion = reflector._determine_retry_strategy(
                cat, "test error", "execute", "test context"
            )
            assert isinstance(should_retry, bool)
            assert isinstance(suggestion, str)

    def test_reflection_history(self):
        reflector = ResultReflector()
        reflector.reflect("write", "ok", False)
        reflector.reflect("execute", "Error", True)
        assert len(reflector.reflection_history) == 2

    def test_get_reflection_summary(self):
        reflector = ResultReflector()
        reflector.reflect("write", "ok", False)
        reflector.reflect("execute", "Error", True)
        summary = reflector.get_reflection_summary()
        assert "2" in summary

    def test_get_reflection_summary_empty(self):
        reflector = ResultReflector()
        summary = reflector.get_reflection_summary()
        assert "No reflections" in summary

    def test_reflect_with_llm_json_error(self):
        llm = MagicMock()
        llm.chat.return_value = "not json"
        reflector = ResultReflector(llm)
        r = reflector.reflect_with_llm("execute", "error", "task", [])
        # Should fall back to pattern matching
        assert r is not None


# ── OutputValidator ──────────────────────────────────────


class TestOutputValidatorExtended:
    """Test OutputValidator edge cases."""

    def test_validate_json_direct(self):
        v = OutputValidator()
        valid, data, err = v.validate_json('{"a": 1}')
        assert valid is True
        assert data == {"a": 1}

    def test_validate_json_code_block(self):
        v = OutputValidator()
        valid, data, err = v.validate_json('```json\n{"a": 1}\n```')
        assert valid is True
        assert data == {"a": 1}

    def test_validate_json_plain_code_block(self):
        v = OutputValidator()
        valid, data, err = v.validate_json('```\n{"a": 1}\n```')
        assert valid is True

    def test_validate_json_embedded_object(self):
        v = OutputValidator()
        valid, data, err = v.validate_json('Here is the result: {"a": 1} done.')
        assert valid is True
        assert data == {"a": 1}

    def test_validate_json_embedded_array(self):
        v = OutputValidator()
        valid, data, err = v.validate_json('Result: [{"id": 1}] done.')
        assert valid is True

    def test_validate_json_failure(self):
        v = OutputValidator()
        valid, data, err = v.validate_json("no json at all")
        assert valid is False
        assert data is None

    def test_validation_history(self):
        v = OutputValidator()
        v.validate_json('{"a": 1}')
        v.validate_json("bad")
        assert len(v.validation_history) == 2


# ── FallbackStrategy ─────────────────────────────────────


class TestFallbackStrategyExtended:
    """Test FallbackStrategy edge cases."""

    def test_direct_call_success(self):
        llm = MagicMock(return_value='{"result": "ok"}')
        strategy = FallbackStrategy(llm)
        result = strategy.execute_with_fallback("test prompt")
        assert result.success is True
        assert result.data == {"result": "ok"}
        assert result.strategy_used == "direct"

    def test_direct_call_failure_falls_to_simplified(self):
        llm = MagicMock(return_value='```json\n{"result": "ok"}\n```')
        strategy = FallbackStrategy(llm)
        result = strategy.execute_with_fallback("test prompt")
        assert result.success is True

    def test_regex_extraction(self):
        llm = MagicMock(return_value="analysis: this is the analysis\nid: task_1")
        strategy = FallbackStrategy(llm)
        # Force regex path by making all JSON parsing fail
        llm.return_value = "analysis: found an issue\nsuggestion: fix it"
        result = strategy._try_regex_extraction("prompt", None)
        assert result.success is True
        assert "analysis" in result.data

    def test_safe_default(self):
        llm = MagicMock()
        strategy = FallbackStrategy(llm)
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "number"},
                "items": {"type": "array"},
                "config": {"type": "object"},
                "active": {"type": "boolean"},
            }
        }
        result = strategy._get_safe_default(schema)
        assert result.success is True
        assert result.data["name"] == ""
        assert result.data["count"] == 0
        assert result.data["items"] == []
        assert result.data["config"] == {}
        assert result.data["active"] is False

    def test_strategy_history(self):
        llm = MagicMock(return_value="no json")
        strategy = FallbackStrategy(llm)
        strategy.execute_with_fallback("test")
        assert len(strategy.strategy_history) > 0


# ── SmallModelOptimizer ──────────────────────────────────


class TestSmallModelOptimizerExtended:
    """Test SmallModelOptimizer methods."""

    def test_create_task_plan_success(self):
        llm = MagicMock(return_value='{"analysis": "ok", "subtasks": [{"id": "t1", "description": "do it"}]}')
        optimizer = SmallModelOptimizer(llm)
        result = optimizer.create_task_plan("build something")
        assert "subtasks" in result
        assert len(result["subtasks"]) == 1

    def test_create_task_plan_fallback(self):
        llm = MagicMock(return_value="not json")
        optimizer = SmallModelOptimizer(llm)
        result = optimizer.create_task_plan("build something")
        assert "subtasks" in result
        # Safe default may return empty subtasks or a default task
        assert isinstance(result["subtasks"], list)

    def test_generate_action_success(self):
        llm = MagicMock(return_value='{"command": "write", "path": "test.py", "content": "x=1"}')
        optimizer = SmallModelOptimizer(llm)
        result = optimizer.generate_action("create a file")
        assert result["command"] == "write"

    def test_generate_action_fallback(self):
        llm = MagicMock(return_value="not json")
        optimizer = SmallModelOptimizer(llm)
        result = optimizer.generate_action("create a file")
        assert "command" in result

    def test_get_strategy_report(self):
        llm = MagicMock(return_value="not json")
        optimizer = SmallModelOptimizer(llm)
        optimizer.create_task_plan("test")
        report = optimizer.get_strategy_report()
        assert "策略" in report or "strategy" in report.lower()

    def test_get_strategy_report_empty(self):
        llm = MagicMock()
        optimizer = SmallModelOptimizer(llm)
        report = optimizer.get_strategy_report()
        assert "暂无" in report or "no" in report.lower()


# ── ChainOfThoughtPrompts ────────────────────────────────


class TestChainOfThoughtPromptsExtended:
    """Test CoT prompt access."""

    def test_task_decomposition_examples(self):
        cot = ChainOfThoughtPrompts()
        assert "Few-shot" in cot.TASK_DECOMPOSITION_EXAMPLES or "示例" in cot.TASK_DECOMPOSITION_EXAMPLES

    def test_tool_selection_examples(self):
        cot = ChainOfThoughtPrompts()
        assert "write" in cot.TOOL_SELECTION_EXAMPLES

    def test_error_recovery_examples(self):
        cot = ChainOfThoughtPrompts()
        assert "SyntaxError" in cot.ERROR_RECOVERY_EXAMPLES or "语法" in cot.ERROR_RECOVERY_EXAMPLES


# ── AgentState ───────────────────────────────────────────


class TestAgentStateExtended:
    """Test AgentState fields."""

    def test_execution_history_default(self):
        state = AgentState()
        assert state.execution_history == []

    def test_total_llm_calls(self):
        state = AgentState()
        state.total_llm_calls = 5
        assert state.total_llm_calls == 5


# ── TaskPlanner.revise_plan ─────────────────────────────


class TestPlannerRevisePlan:
    """Test plan revision logic."""

    def test_revise_plan_retries_failed_task(self):
        llm = MagicMock()
        planner = TaskPlanner(llm)
        plan = ExecutionPlan(main_goal="test")
        task = SubTask(id="t1", description="do it", status=TaskStatus.FAILED, retry_count=0)
        plan.subtasks = [task]

        revised = planner.revise_plan(plan, "t1", "error msg")
        assert revised.subtasks[0].status == TaskStatus.PENDING
        assert revised.subtasks[0].retry_count == 1

    def test_revise_plan_marks_failed_after_max_retries(self):
        llm = MagicMock()
        planner = TaskPlanner(llm)
        plan = ExecutionPlan(main_goal="test", max_attempts=2)
        task = SubTask(id="t1", description="do it", status=TaskStatus.FAILED, retry_count=2)
        plan.subtasks = [task]

        revised = planner.revise_plan(plan, "t1", "error msg")
        assert revised.subtasks[0].status == TaskStatus.FAILED

    def test_revise_plan_unknown_task(self):
        llm = MagicMock()
        planner = TaskPlanner(llm)
        plan = ExecutionPlan(main_goal="test")
        plan.subtasks = [SubTask(id="t1", description="x")]

        revised = planner.revise_plan(plan, "nonexistent", "error")
        assert revised is plan  # Returns unchanged

    def test_revise_plan_with_llm_alternative(self):
        llm = MagicMock()
        llm.chat.return_value = '{"new_subtasks": [{"description": "simpler approach"}]}'
        planner = TaskPlanner(llm)
        plan = ExecutionPlan(main_goal="test", max_attempts=1)
        task = SubTask(id="t1", description="complex task", status=TaskStatus.FAILED, retry_count=3)
        plan.subtasks = [task]

        revised = planner.revise_plan(plan, "t1", "too hard")
        # Should have added alternative subtask
        assert len(revised.subtasks) > 1

    def test_get_task_summary(self):
        llm = MagicMock()
        planner = TaskPlanner(llm)
        plan = ExecutionPlan(main_goal="build app")
        plan.subtasks = [
            SubTask(id="t1", description="step 1", status=TaskStatus.COMPLETED),
            SubTask(id="t2", description="step 2", status=TaskStatus.IN_PROGRESS),
            SubTask(id="t3", description="step 3", status=TaskStatus.PENDING, dependencies=["t2"]),
        ]
        summary = planner.get_task_summary(plan)
        assert "build app" in summary
        assert "3" in summary
