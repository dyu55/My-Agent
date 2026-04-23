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

    PLANNING_PROMPT = """你是一个项目规划专家。你的任务是将用户的需求分解成可执行的子任务。

## Few-shot 示例（帮助你理解任务分解）

示例 1: 简单任务
输入: "运行测试"
输出:
{
  "analysis": "这是一个简单的单步任务",
  "subtasks": [
    {"id": "task_1", "description": "运行 pytest 测试", "dependencies": []}
  ]
}

示例 2: 复杂任务
输入: "创建一个待办事项应用"
输出:
{
  "analysis": "需要创建前后端完整应用",
  "subtasks": [
    {"id": "task_1", "description": "设计数据模型"},
    {"id": "task_2", "description": "创建后端 API", "dependencies": ["task_1"]},
    {"id": "task_3", "description": "创建前端界面"},
    {"id": "task_4", "description": "测试验证", "dependencies": ["task_2", "task_3"]}
  ]
}

## 输出格式
你必须返回一个 JSON 对象，包含以下字段：
- "analysis": 对任务的分析理解
- "subtasks": 子任务列表，每个包含：
  - "id": 唯一标识符（如 "task_1"）
  - "description": 清晰的子任务描述
  - "dependencies": 依赖的其他任务ID列表（可选，默认为空）

## 规则
1. 子任务应该是原子的、独立的
2. 考虑任务之间的依赖关系
3. 初始任务应该包括了解项目现状
4. 最后任务应该包括验证和测试

现在分析以下任务：
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
        prompt = f"""任务执行失败，需要重新规划。

失败的任务: {failed_task.description}
错误信息: {error_message}

请将这个失败的任务分解成更简单的步骤，或提供替代方案。

输出格式:
{{
  "analysis": "失败原因分析和替代方案",
  "new_subtasks": [
    {{"id": "替代任务ID", "description": "更简单的任务描述"}}
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
