"""Tests for agent/coordinator.py parallel execution."""
import time
import pytest
from agent.coordinator import (
    MultiAgentCoordinator,
    TaskPriority,
    parallel_map,
    parallel_filter,
)


class TestMultiAgentCoordinator:
    """Tests for MultiAgentCoordinator class."""

    def test_add_task(self):
        """Test adding tasks to coordinator."""
        coordinator = MultiAgentCoordinator()
        coordinator.add_task("task_1", "Test task")
        assert "task_1" in coordinator.tasks
        assert coordinator.tasks["task_1"].description == "Test task"
        assert coordinator.tasks["task_1"].status == "pending"

    def test_execute_parallel_simple(self):
        """Test parallel execution of simple tasks."""
        coordinator = MultiAgentCoordinator()

        def task_1():
            return "result_1"

        def task_2():
            return "result_2"

        result = coordinator.execute_parallel({
            "task_1": task_1,
            "task_2": task_2,
        })

        assert result.total_tasks == 2
        assert result.completed == 2
        assert result.failed == 0
        assert result.results["task_1"] == "result_1"
        assert result.results["task_2"] == "result_2"

    def test_execute_parallel_with_delay(self):
        """Test that parallel execution is faster than sequential."""
        coordinator = MultiAgentCoordinator()

        def slow_task():
            time.sleep(0.1)
            return "done"

        # Create 4 tasks that each take 0.1s
        task_functions = {f"task_{i}": slow_task for i in range(4)}

        result = coordinator.execute_parallel(task_functions, max_workers=4)

        # Parallel should take ~0.1s, not 0.4s
        assert result.parallel_time < 0.3  # Should be much faster than 0.4s
        assert result.completed == 4

    def test_execute_parallel_with_error(self):
        """Test handling of errors in parallel execution."""
        coordinator = MultiAgentCoordinator()

        def good_task():
            return "success"

        def bad_task():
            raise ValueError("Task failed")

        result = coordinator.execute_parallel({
            "good": good_task,
            "bad": bad_task,
        })

        assert result.completed == 1
        assert result.failed == 1
        assert result.results["good"] == "success"
        assert "error" in result.results["bad"]

    def test_execute_sequential(self):
        """Test sequential execution."""
        coordinator = MultiAgentCoordinator()

        results = coordinator.execute_sequential({
            "task_1": lambda: "first",
            "task_2": lambda: "second",
        })

        assert results["task_1"] == "first"
        assert results["task_2"] == "second"

    def test_execute_with_dependencies(self):
        """Test execution with task dependencies."""
        execution_order = []

        def task_1():
            execution_order.append("task_1")
            return "result_1"

        def task_2():
            execution_order.append("task_2")
            return "result_2"

        def task_3():
            execution_order.append("task_3")
            return "result_3"

        coordinator = MultiAgentCoordinator()
        dependencies = {
            "task_2": ["task_1"],  # task_2 depends on task_1
            "task_3": ["task_1", "task_2"],  # task_3 depends on both
        }

        results = coordinator.execute_with_dependencies({
            "task_1": task_1,
            "task_2": task_2,
            "task_3": task_3,
        }, dependencies)

        assert results["task_1"] == "result_1"
        assert results["task_2"] == "result_2"
        assert results["task_3"] == "result_3"
        # task_1 should execute first
        assert execution_order[0] == "task_1"

    def test_aggregate_results_merge(self):
        """Test merging results."""
        coordinator = MultiAgentCoordinator()
        results = {
            "task_1": {"a": 1},
            "task_2": {"b": 2},
        }
        merged = coordinator.aggregate_results(results, strategy="merge")
        assert merged == {"a": 1, "b": 2}

    def test_aggregate_results_concat(self):
        """Test concatenating results."""
        coordinator = MultiAgentCoordinator()
        results = {
            "task_1": [1, 2],
            "task_2": [3, 4],
        }
        concatenated = coordinator.aggregate_results(results, strategy="concat")
        assert concatenated == [1, 2, 3, 4]

    def test_aggregate_results_first(self):
        """Test returning first result."""
        coordinator = MultiAgentCoordinator()
        results = {
            "task_1": "first",
            "task_2": "second",
        }
        first = coordinator.aggregate_results(results, strategy="first")
        assert first == "first"

    def test_get_status(self):
        """Test getting coordinator status."""
        coordinator = MultiAgentCoordinator()
        coordinator.add_task("task_1", "Test task 1")
        coordinator.add_task("task_2", "Test task 2")

        status = coordinator.get_status()
        assert status["total"] == 2
        assert "task_1" in status["tasks"]
        assert "task_2" in status["tasks"]


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_parallel_map(self):
        """Test parallel_map function."""
        items = [1, 2, 3, 4]
        result = parallel_map(items, lambda x: x * 2, max_workers=4)
        assert result == [2, 4, 6, 8]

    def test_parallel_filter(self):
        """Test parallel_filter function."""
        items = [1, 2, 3, 4, 5, 6]
        result = parallel_filter(items, lambda x: x % 2 == 0, max_workers=4)
        assert result == [2, 4, 6]

    def test_parallel_map_with_delay(self):
        """Test parallel_map is actually parallel."""
        start = time.time()
        items = [0.1] * 4  # 4 items taking 0.1s each
        result = parallel_map(items, lambda x: time.sleep(x) or x, max_workers=4)
        elapsed = time.time() - start

        # Should take ~0.1s parallel, not 0.4s sequential
        assert elapsed < 0.25
        assert result == [0.1, 0.1, 0.1, 0.1]