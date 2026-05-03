"""Multi-Agent Coordinator - Parallel task execution and agent collaboration."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ParallelTask:
    """A task that can run in parallel with others."""
    id: str
    description: str
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: float = 300.0  # 5 minutes default
    result: Any = None
    error: str | None = None
    start_time: float = 0.0
    end_time: float = 0.0
    status: str = "pending"  # pending, running, completed, failed, timeout

    @property
    def duration(self) -> float:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return 0.0


@dataclass
class CoordinationResult:
    """Result of coordinated task execution."""
    total_tasks: int
    completed: int
    failed: int
    parallel_time: float  # Time using parallel execution
    sequential_time: float  # Time if run sequentially
    speedup: float  # Ratio of sequential to parallel time
    results: dict[str, Any]


class MultiAgentCoordinator:
    """
    Coordinate multiple agents for parallel task execution.

    Enables:
    - Parallel task execution
    - Task dependency management
    - Result aggregation
    - Conflict resolution
    """

    def __init__(self):
        self.tasks: dict[str, ParallelTask] = {}
        self.results: dict[str, Any] = {}

    def add_task(
        self,
        task_id: str,
        description: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: float = 300.0,
    ) -> None:
        """Add a task to the coordinator."""
        self.tasks[task_id] = ParallelTask(
            id=task_id,
            description=description,
            priority=priority,
            timeout=timeout,
        )

    def execute_parallel(
        self,
        task_functions: dict[str, Callable],
        max_workers: int = 4,
    ) -> CoordinationResult:
        """
        Execute multiple tasks in parallel.

        Args:
            task_functions: Dict of task_id -> callable function
            max_workers: Maximum parallel workers

        Returns:
            CoordinationResult with execution statistics
        """
        start_time = time.time()

        # Initialize tasks
        for task_id, func in task_functions.items():
            if task_id not in self.tasks:
                self.add_task(task_id, f"Task {task_id}")

            task = self.tasks[task_id]
            task.status = "pending"

        # Sort by priority
        sorted_tasks = sorted(
            task_functions.items(),
            key=lambda x: self.tasks[x[0]].priority.value,
            reverse=True,
        )

        # Execute in batches
        results = {}
        batch_size = min(max_workers, len(sorted_tasks))

        for i in range(0, len(sorted_tasks), batch_size):
            batch = sorted_tasks[i:i + batch_size]
            batch_results = self._execute_batch(batch)
            results.update(batch_results)

        end_time = time.time()
        parallel_time = end_time - start_time

        # Calculate sequential time estimate
        sequential_time = sum(t.timeout for t in self.tasks.values())

        # Count results
        completed = sum(1 for t in self.tasks.values() if t.status == "completed")
        failed = sum(1 for t in self.tasks.values() if t.status in ["failed", "timeout"])

        return CoordinationResult(
            total_tasks=len(task_functions),
            completed=completed,
            failed=failed,
            parallel_time=parallel_time,
            sequential_time=sequential_time,
            speedup=sequential_time / parallel_time if parallel_time > 0 else 1.0,
            results=results,
        )

    def _execute_batch(
        self,
        batch: list[tuple[str, Callable]],
    ) -> dict[str, Any]:
        """Execute a batch of tasks in parallel using ThreadPoolExecutor."""
        results = {}

        with ThreadPoolExecutor(max_workers=len(batch)) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(self._execute_single, task_id, func): task_id
                for task_id, func in batch
            }

            # Collect results as they complete
            for future in as_completed(future_to_task):
                task_id = future_to_task[future]
                try:
                    result = future.result()
                    results[task_id] = result
                except Exception as e:
                    results[task_id] = {"error": str(e)}

        return results

    def _execute_single(self, task_id: str, func: Callable) -> Any:
        """Execute a single task and update task status."""
        task = self.tasks[task_id]
        task.status = "running"
        task.start_time = time.time()

        try:
            result = func()
            task.result = result
            task.status = "completed"
            return result

        except Exception as e:
            task.error = str(e)
            task.status = "failed"
            return {"error": str(e)}

        finally:
            task.end_time = time.time()

    def execute_sequential(
        self,
        task_functions: dict[str, Callable],
    ) -> dict[str, Any]:
        """
        Execute tasks sequentially with dependency checking.

        Args:
            task_functions: Dict of task_id -> callable function

        Returns:
            Dict of task_id -> result
        """
        results = {}

        for task_id, func in task_functions.items():
            if task_id not in self.tasks:
                self.add_task(task_id, f"Task {task_id}")

            task = self.tasks[task_id]
            task.status = "running"
            task.start_time = time.time()

            try:
                result = func()
                task.result = result
                task.status = "completed"
                results[task_id] = result

            except Exception as e:
                task.error = str(e)
                task.status = "failed"
                results[task_id] = {"error": str(e)}

            finally:
                task.end_time = time.time()

            # Stop on failure (optional)
            if task.status == "failed":
                break

        return results

    def execute_with_dependencies(
        self,
        task_functions: dict[str, Callable],
        dependencies: dict[str, list[str]],
    ) -> dict[str, Any]:
        """
        Execute tasks respecting dependencies.

        Args:
            task_functions: Dict of task_id -> callable function
            dependencies: Dict of task_id -> list of task_ids it depends on

        Returns:
            Dict of task_id -> result
        """
        results = {}
        pending = set(task_functions.keys())
        completed = set()

        # Initialize all tasks first (matching execute_parallel pattern)
        for task_id, func in task_functions.items():
            if task_id not in self.tasks:
                self.add_task(task_id, f"Task {task_id}")

        while pending:
            # Find tasks with all dependencies satisfied
            ready = []
            for task_id in pending:
                deps = dependencies.get(task_id, [])
                if all(dep in completed for dep in deps):
                    ready.append(task_id)

            if not ready:
                # Circular dependency or missing dependency
                break

            # Execute ready tasks in parallel
            batch_funcs = {tid: task_functions[tid] for tid in ready}
            batch_results = self._execute_batch(list(batch_funcs.items()))

            # Process results
            for task_id, result in batch_results.items():
                results[task_id] = result
                pending.discard(task_id)
                if self.tasks[task_id].status == "completed":
                    completed.add(task_id)

        return results

    def get_status(self) -> dict[str, Any]:
        """Get current status of all tasks."""
        status = {
            "total": len(self.tasks),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "tasks": {},
        }

        for task_id, task in self.tasks.items():
            status[f"total_{task.status}"] = status.get(f"total_{task.status}", 0) + 1

            status["tasks"][task_id] = {
                "description": task.description,
                "priority": task.priority.name,
                "status": task.status,
                "duration": task.duration,
                "error": task.error,
            }

        return status

    def aggregate_results(
        self,
        results: dict[str, Any],
        strategy: str = "merge",
    ) -> Any:
        """
        Aggregate results from multiple tasks.

        Args:
            results: Dict of task_id -> result
            strategy: Aggregation strategy (merge, concat, combine, first)

        Returns:
            Aggregated result
        """
        if not results:
            return None

        if strategy == "first":
            return next(iter(results.values()))

        elif strategy == "merge":
            merged = {}
            for result in results.values():
                if isinstance(result, dict):
                    merged.update(result)
            return merged

        elif strategy == "concat":
            items = []
            for result in results.values():
                if isinstance(result, list):
                    items.extend(result)
                else:
                    items.append(result)
            return items

        elif strategy == "combine":
            combined = {"tasks": {}, "errors": []}
            for task_id, result in results.items():
                if isinstance(result, dict) and "error" in result:
                    combined["errors"].append({task_id: result["error"]})
                else:
                    combined["tasks"][task_id] = result
            return combined

        return results

    def cancel_all(self) -> int:
        """Cancel all pending tasks."""
        count = 0
        for task in self.tasks.values():
            if task.status == "pending":
                task.status = "cancelled"
                count += 1
        return count

    def retry_failed(self) -> int:
        """Retry all failed tasks."""
        count = 0
        for task in self.tasks.values():
            if task.status == "failed":
                task.status = "pending"
                task.error = None
                count += 1
        return count


# Convenience functions for common patterns
def parallel_map(
    items: list[Any],
    func: Callable,
    max_workers: int = 4,
) -> list[Any]:
    """
    Map a function over items in parallel.

    Args:
        items: List of items to process
        func: Function to apply
        max_workers: Maximum parallel workers

    Returns:
        List of results (in original order)
    """
    coordinator = MultiAgentCoordinator()

    # Add tasks
    for i, item in enumerate(items):
        coordinator.add_task(
            f"item_{i}",
            f"Process item {i}",
            timeout=60.0,
        )

    # Create task functions
    task_functions = {f"item_{i}": lambda i=i, item=item: func(item) for i, item in enumerate(items)}

    # Execute
    result = coordinator.execute_parallel(task_functions, max_workers)

    # Return in original order
    ordered_results = []
    for i in range(len(items)):
        task_id = f"item_{i}"
        if task_id in result.results:
            ordered_results.append(result.results[task_id])
        else:
            ordered_results.append(None)

    return ordered_results


def parallel_filter(
    items: list[Any],
    predicate: Callable[[Any], bool],
    max_workers: int = 4,
) -> list[Any]:
    """Filter items in parallel."""
    results = parallel_map(items, predicate, max_workers)
    return [item for item, result in zip(items, results) if result]


def parallel_reduce(
    items: list[Any],
    reducer: Callable[[Any, Any], Any],
    max_workers: int = 4,
) -> Any:
    """Reduce items in parallel."""
    coordinator = MultiAgentCoordinator()

    # Create tree reduction tasks
    n = len(items)
    if n == 0:
        return None
    if n == 1:
        return items[0]

    current_level = [(f"leaf_{i}", item) for i, item in enumerate(items)]

    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            if i + 1 < len(current_level):
                id1, val1 = current_level[i]
                id2, val2 = current_level[i + 1]
                task_id = f"reduce_{len(next_level)}"

                def make_reducer(v1, v2):
                    return lambda: reducer(v1, v2)

                coordinator.add_task(task_id, f"Reduce {id1} + {id2}")
                next_level.append((task_id, make_reducer(val1, val2)))
            else:
                next_level.append(current_level[i])

        # Execute level
        funcs = {tid: func for tid, func in next_level}
        result = coordinator.execute_parallel(funcs, max_workers)

        current_level = [
            (tid, result.results.get(tid))
            for tid, _ in next_level
            if result.results.get(tid) is not None
        ]

    return current_level[0][1] if current_level else None