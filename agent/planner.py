"""Task Planner - Plans and decomposes tasks for the agent."""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# 小模型优化
from utils.small_model import ChainOfThoughtPrompts, FallbackStrategy, OutputValidator


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass
class SubTask:
    """Represents a single subtask in the plan."""

    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    result: str | None = None
    error: str | None = None
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
        }


@dataclass
class ExecutionPlan:
    """Represents a complete execution plan with subtasks."""

    main_goal: str
    subtasks: list[SubTask] = field(default_factory=list)
    current_task_index: int = 0
    total_attempts: int = 0
    max_attempts: int = 3

    def get_next_task(self) -> SubTask | None:
        """Get the next task that's ready to execute (dependencies met)."""
        for task in self.subtasks:
            if task.status == TaskStatus.PENDING:
                deps_met = all(
                    self.get_task_by_id(dep).status == TaskStatus.COMPLETED
                    for dep in task.dependencies
                )
                if deps_met:
                    return task
        return None

    def get_task_by_id(self, task_id: str) -> SubTask | None:
        for task in self.subtasks:
            if task.id == task_id:
                return task
        return None

    def all_completed(self) -> bool:
        return all(t.status == TaskStatus.COMPLETED for t in self.subtasks)

    def has_failures(self) -> bool:
        return any(t.status == TaskStatus.FAILED for t in self.subtasks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "main_goal": self.main_goal,
            "subtasks": [t.to_dict() for t in self.subtasks],
            "current_task_index": self.current_task_index,
            "total_attempts": self.total_attempts,
        }


class TaskPlanner:
    """
    Responsible for breaking down complex tasks into actionable subtasks.

    Phase: Plan

    Uses Chain-of-Thought prompts for better performance with small models.
    """

    PLANNING_PROMPT = """You are a project planning expert. Your task is to decompose user requirements into executable subtasks.

## Few-shot Examples

Example 1: Simple Task
Input: "Run tests"
Output:
{
  "analysis": "This is a simple single-step task",
  "subtasks": [
    {"id": "task_1", "description": "Run pytest tests", "dependencies": []}
  ]
}

Example 2: Complex Task
Input: "Create a todo app"
Output:
{
  "analysis": "Need to create a complete frontend and backend application",
  "subtasks": [
    {"id": "task_1", "description": "Design data models"},
    {"id": "task_2", "description": "Create backend API", "dependencies": ["task_1"]},
    {"id": "task_3", "description": "Create frontend UI"},
    {"id": "task_4", "description": "Test and verify", "dependencies": ["task_2", "task_3"]}
  ]
}

## Output Format
You must return a JSON object with these fields:
- "analysis": Your understanding of the task
- "subtasks": List of subtasks, each containing:
  - "id": Unique identifier (e.g., "task_1")
  - "description": Clear subtask description
  - "dependencies": List of task IDs this depends on (default: empty)

## Rules
1. Subtasks should be atomic and independent
2. Consider dependencies between tasks
3. Initial tasks should include understanding project state
4. Final tasks should include verification and testing

Now analyze this task:
"""

    def __init__(self, llm_client: Any):
        self.llm = llm_client
        self.cot = ChainOfThoughtPrompts()
        self.validator = OutputValidator()

        # 创建降级策略（用于 JSON 解析失败时）
        self.fallback = FallbackStrategy(self._llm_call)

    def _llm_call(self, prompt: str) -> str:
        """LLM 调用包装器。"""
        return self.llm.chat(prompt)

    def create_plan(self, task: str, context: str = "") -> ExecutionPlan:
        """
        Create an execution plan from a user task.

        Uses FallbackStrategy for better JSON parsing with small models.

        Args:
            task: The user's task description
            context: Additional context about the project state

        Returns:
            ExecutionPlan with decomposed subtasks
        """
        prompt = self.PLANNING_PROMPT
        if context:
            prompt += f"\n\n## 当前项目状态\n{context}"
        prompt += f"\n\n## 任务\n{task}"

        # 使用降级策略解析 JSON
        result = self.fallback.execute_with_fallback(
            prompt,
            schema={
                "type": "object",
                "properties": {
                    "analysis": {"type": "string"},
                    "subtasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "description": {"type": "string"},
                                "dependencies": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["id", "description"]
                        }
                    }
                },
                "required": ["subtasks"]
            }
        )

        plan = ExecutionPlan(main_goal=task)

        # 如果降级策略成功，解析数据
        if result.success and result.data:
            for task_data in result.data.get("subtasks", []):
                plan.subtasks.append(
                    SubTask(
                        id=task_data["id"],
                        description=task_data["description"],
                        dependencies=task_data.get("dependencies", []),
                    )
                )
            return plan

        # 如果所有策略都失败，返回默认计划
        return ExecutionPlan(
            main_goal=task,
            subtasks=[SubTask(id="task_1", description=task)],
        )

    def revise_plan(
        self,
        plan: ExecutionPlan,
        failed_task_id: str,
        error_message: str,
        llm_context: str = "",
    ) -> ExecutionPlan:
        """
        Revise the plan when a task fails.

        Args:
            plan: The current execution plan
            failed_task_id: ID of the failed task
            error_message: The error that occurred
            llm_context: Additional context for revision

        Returns:
            Revised ExecutionPlan
        """
        failed_task = plan.get_task_by_id(failed_task_id)
        if not failed_task:
            return plan

        # Simple retry logic with exponential backoff
        if failed_task.retry_count < plan.max_attempts:
            failed_task.retry_count += 1
            failed_task.status = TaskStatus.PENDING
            failed_task.error = None
            return plan

        # If max retries exceeded, mark as failed and try alternative approach
        failed_task.status = TaskStatus.FAILED
        failed_task.error = error_message

        # Try to decompose the failed task into simpler steps
        prompt = f"""Task execution failed, need to re-plan.

Failed task: {failed_task.description}
Error message: {error_message}

Please decompose this failed task into simpler steps, or provide an alternative approach.

Output format:
{{
  "analysis": "Failure cause analysis and alternative approach",
  "new_subtasks": [
    {{"id": "alternative_task_id", "description": "Simpler task description"}}
  ]
}}
"""

        if llm_context:
            prompt += f"\n\n上下文:\n{llm_context}"

        try:
            response = self.llm.chat(prompt)
            if isinstance(response, str):
                data = json.loads(response)
            else:
                data = response

            # Add new subtasks
            for i, task_data in enumerate(data.get("new_subtasks", [])):
                new_id = f"{failed_task_id}_retry_{i + 1}"
                plan.subtasks.append(
                    SubTask(
                        id=new_id,
                        description=task_data["description"],
                        dependencies=[failed_task_id],
                    )
                )

        except Exception:
            pass  # Keep the failed task as-is

        return plan

    def get_task_summary(self, plan: ExecutionPlan) -> str:
        """Get a human-readable summary of the plan."""
        lines = [f"## 执行计划: {plan.main_goal}\n"]
        lines.append(f"共 {len(plan.subtasks)} 个子任务:\n")

        for i, task in enumerate(plan.subtasks, 1):
            status_icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.BLOCKED: "🚫",
            }.get(task.status, "❓")

            deps = f" (依赖: {', '.join(task.dependencies)})" if task.dependencies else ""
            lines.append(f"{i}. {status_icon} {task.description}{deps}")

        return "\n".join(lines)
