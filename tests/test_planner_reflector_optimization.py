"""Tests for planner and reflector small-model prompt optimization."""

import pytest
from unittest.mock import MagicMock

from agent.planner import TaskPlanner, ExecutionPlan, SubTask, TaskStatus
from agent.reflector import ResultReflector, Reflection, ErrorCategory
from utils.small_model import ModelProfile


class TestPlannerShortPrompt:
    """Test TaskPlanner uses short prompts for small models."""

    def test_small_model_uses_short_planning_prompt(self):
        profile = ModelProfile._small_profile(8)
        llm = MagicMock()
        planner = TaskPlanner(llm, model_profile=profile)

        prompt = planner._build_short_planning_prompt("Create a todo app", "")

        assert len(prompt) < 500
        assert "JSON" in prompt
        assert "Create a todo app" in prompt

    def test_short_prompt_truncates_context(self):
        profile = ModelProfile._small_profile(8)
        llm = MagicMock()
        planner = TaskPlanner(llm, model_profile=profile)

        long_context = "file.py\n" * 200
        prompt = planner._build_short_planning_prompt("task", long_context)

        # Context should be truncated to 500 chars
        assert len(prompt) < 1000

    def test_create_plan_uses_short_prompt_for_small_model(self):
        profile = ModelProfile._small_profile(8)
        llm = MagicMock()
        llm.chat_think.return_value = '{"subtasks": [{"id": "task_1", "description": "do it"}]}'
        planner = TaskPlanner(llm, model_profile=profile)

        plan = planner.create_plan("Create a script")

        assert len(plan.subtasks) == 1
        assert plan.subtasks[0].id == "task_1"

    def test_create_plan_uses_full_prompt_for_large_model(self):
        profile = ModelProfile._large_profile(70)
        llm = MagicMock()
        llm.chat_think.return_value = '{"subtasks": [{"id": "task_1", "description": "do it"}]}'
        planner = TaskPlanner(llm, model_profile=profile)

        plan = planner.create_plan("Create a script")

        # Should have called llm with the full PLANNING_PROMPT
        call_args = llm.chat_think.call_args[0][0]
        assert "Few-shot" in call_args or "few-shot" in call_args.lower() or "project planning" in call_args.lower()

    def test_create_plan_without_profile(self):
        llm = MagicMock()
        llm.chat_think.return_value = '{"subtasks": [{"id": "task_1", "description": "do it"}]}'
        planner = TaskPlanner(llm)

        plan = planner.create_plan("test task")
        assert len(plan.subtasks) == 1


class TestReflectorShortPrompt:
    """Test ResultReflector uses short prompts for small models."""

    def test_small_model_uses_short_reflect_prompt(self):
        profile = ModelProfile._small_profile(8)
        llm = MagicMock()
        llm.chat_think.return_value = '{"analysis": "syntax error", "error_type": "syntax", "suggestion": "fix it", "should_retry": true}'
        reflector = ResultReflector(llm, model_profile=profile)

        reflection = reflector.reflect_with_llm(
            action_command="execute",
            execution_output="SyntaxError: invalid syntax",
            task_description="Create a script",
            execution_history=[],
        )

        # Verify the prompt was short
        call_args = llm.chat_think.call_args[0][0]
        assert len(call_args) < 500
        assert "Debug" in call_args or "JSON" in call_args

    def test_large_model_uses_full_reflect_prompt(self):
        profile = ModelProfile._large_profile(70)
        llm = MagicMock()
        llm.chat_think.return_value = '{"analysis": "syntax error", "error_type": "syntax", "suggestion": "fix it", "should_retry": true}'
        reflector = ResultReflector(llm, model_profile=profile)

        reflection = reflector.reflect_with_llm(
            action_command="execute",
            execution_output="SyntaxError: invalid syntax",
            task_description="Create a script",
            execution_history=["prev action 1", "prev action 2"],
        )

        call_args = llm.chat_think.call_args[0][0]
        assert "code debugging expert" in call_args.lower() or "debugging" in call_args.lower()

    def test_reflect_without_profile_uses_full_prompt(self):
        llm = MagicMock()
        llm.chat_think.return_value = '{"analysis": "err", "error_type": "syntax", "suggestion": "fix", "should_retry": true}'
        reflector = ResultReflector(llm)

        reflector.reflect_with_llm("execute", "error", "task", [])
        call_args = llm.chat_think.call_args[0][0]
        assert "code debugging expert" in call_args.lower() or "debugging" in call_args.lower()

    def test_reflect_without_llm_falls_back(self):
        profile = ModelProfile._small_profile(8)
        reflector = ResultReflector(None, model_profile=profile)

        reflection = reflector.reflect_with_llm("execute", "error", "task", [])
        # Should fall back to pattern-based reflection
        assert reflection is not None
        assert isinstance(reflection, Reflection)

    def test_reflection_result_parsed_correctly(self):
        profile = ModelProfile._small_profile(8)
        llm = MagicMock()
        llm.chat_think.return_value = '{"analysis": "bad syntax", "error_type": "syntax", "suggestion": "check colons", "should_retry": true}'
        reflector = ResultReflector(llm, model_profile=profile)

        reflection = reflector.reflect_with_llm("execute", "SyntaxError", "task", [])

        assert reflection.is_successful is False
        assert reflection.error_category == ErrorCategory.SYNTAX_ERROR
        assert reflection.should_retry is True
        assert "check colons" in reflection.suggestion


class TestPlannerDefaultBehavior:
    """Test that planner defaults work without model profile."""

    def test_default_create_plan(self):
        llm = MagicMock()
        llm.chat_think.return_value = '{"subtasks": [{"id": "t1", "description": "step 1"}, {"id": "t2", "description": "step 2", "dependencies": ["t1"]}]}'
        planner = TaskPlanner(llm)

        plan = planner.create_plan("Build an app")

        assert len(plan.subtasks) == 2
        assert plan.subtasks[1].dependencies == ["t1"]

    def test_plan_with_context(self):
        llm = MagicMock()
        llm.chat_think.return_value = '{"subtasks": [{"id": "t1", "description": "read code"}]}'
        planner = TaskPlanner(llm)

        plan = planner.create_plan("Refactor", context="main.py exists")

        call_args = llm.chat_think.call_args[0][0]
        assert "main.py exists" in call_args

    def test_plan_fallback_on_bad_json(self):
        llm = MagicMock()
        llm.chat_think.return_value = "not json at all"
        planner = TaskPlanner(llm)

        plan = planner.create_plan("test")

        # FallbackStrategy safe default returns empty subtasks;
        # the planner should still return a valid ExecutionPlan
        assert isinstance(plan, ExecutionPlan)
        assert plan.main_goal == "test"
