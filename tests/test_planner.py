"""Tests for agent/planner.py task planning."""
import pytest
from agent.planner import (
    ExecutionPlan,
    SubTask,
    TaskPlanner,
    TaskStatus,
)


class TestSubTask:
    """Tests for SubTask dataclass."""

    def test_create_subtask(self):
        """Test creating a subtask with basic fields."""
        task = SubTask(id="task_1", description="Test task")
        assert task.id == "task_1"
        assert task.description == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.dependencies == []
        assert task.result is None
        assert task.error is None
        assert task.retry_count == 0

    def test_subtask_with_dependencies(self):
        """Test creating a subtask with dependencies."""
        task = SubTask(
            id="task_2",
            description="Second task",
            dependencies=["task_1"],
        )
        assert task.dependencies == ["task_1"]

    def test_subtask_to_dict(self):
        """Test converting subtask to dictionary."""
        task = SubTask(
            id="task_1",
            description="Test",
            status=TaskStatus.COMPLETED,
            result="success",
        )
        result = task.to_dict()
        assert result["id"] == "task_1"
        assert result["description"] == "Test"
        assert result["status"] == "completed"
        assert result["result"] == "success"


class TestExecutionPlan:
    """Tests for ExecutionPlan class."""

    def test_create_empty_plan(self):
        """Test creating an empty execution plan."""
        plan = ExecutionPlan(main_goal="Build a calculator")
        assert plan.main_goal == "Build a calculator"
        assert plan.subtasks == []
        assert plan.current_task_index == 0
        assert plan.total_attempts == 0
        assert plan.max_attempts == 3

    def test_get_next_task_empty(self):
        """Test getting next task from empty plan."""
        plan = ExecutionPlan(main_goal="Test")
        task = plan.get_next_task()
        assert task is None

    def test_get_next_task(self):
        """Test getting next pending task."""
        plan = ExecutionPlan(main_goal="Test")
        plan.subtasks = [
            SubTask(id="task_1", description="First"),
            SubTask(id="task_2", description="Second"),
        ]
        task = plan.get_next_task()
        assert task is not None
        assert task.id == "task_1"

    def test_get_next_task_with_dependencies(self):
        """Test getting next task respects dependencies."""
        plan = ExecutionPlan(main_goal="Test")
        plan.subtasks = [
            SubTask(id="task_1", description="First"),
            SubTask(id="task_2", description="Second", dependencies=["task_1"]),
        ]
        # First call should get task_1
        task = plan.get_next_task()
        assert task.id == "task_1"

        # Complete task_1
        task.status = TaskStatus.COMPLETED

        # Second call should get task_2
        task = plan.get_next_task()
        assert task.id == "task_2"

    def test_all_completed(self):
        """Test checking if all tasks are completed."""
        plan = ExecutionPlan(main_goal="Test")
        plan.subtasks = [
            SubTask(id="task_1", description="First", status=TaskStatus.COMPLETED),
            SubTask(id="task_2", description="Second", status=TaskStatus.COMPLETED),
        ]
        assert plan.all_completed() is True

    def test_all_completed_with_pending(self):
        """Test all_completed returns False when tasks are pending."""
        plan = ExecutionPlan(main_goal="Test")
        plan.subtasks = [
            SubTask(id="task_1", description="First", status=TaskStatus.COMPLETED),
            SubTask(id="task_2", description="Second", status=TaskStatus.PENDING),
        ]
        assert plan.all_completed() is False

    def test_has_failures(self):
        """Test checking for failed tasks."""
        plan = ExecutionPlan(main_goal="Test")
        plan.subtasks = [
            SubTask(id="task_1", description="First", status=TaskStatus.FAILED),
            SubTask(id="task_2", description="Second", status=TaskStatus.COMPLETED),
        ]
        assert plan.has_failures() is True

    def test_get_task_by_id(self):
        """Test finding a task by ID."""
        plan = ExecutionPlan(main_goal="Test")
        plan.subtasks = [
            SubTask(id="task_1", description="First"),
            SubTask(id="task_2", description="Second"),
        ]
        task = plan.get_task_by_id("task_2")
        assert task is not None
        assert task.description == "Second"

    def test_get_task_by_id_not_found(self):
        """Test finding non-existent task returns None."""
        plan = ExecutionPlan(main_goal="Test")
        task = plan.get_task_by_id("nonexistent")
        assert task is None

    def test_plan_to_dict(self):
        """Test converting plan to dictionary."""
        plan = ExecutionPlan(main_goal="Build app")
        plan.subtasks = [SubTask(id="task_1", description="Test")]
        result = plan.to_dict()
        assert result["main_goal"] == "Build app"
        assert len(result["subtasks"]) == 1
