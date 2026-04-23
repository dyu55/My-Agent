"""Agent Engine - Core agent loop integrating Plan/Act/Reflect."""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .planner import ExecutionPlan, TaskPlanner, TaskStatus
from .executor import Action, ExecutionResult, ExecutionStatus, ToolExecutor
from .reflector import ErrorCategory, Reflection, ResultReflector
from utils.model_provider import ModelManager
from utils.conversation import ConversationMemory
from utils.persistent_memory import PersistentMemory, SessionMemory
from utils.logger import TraceLogger

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for the agent."""

    workspace: Path
    model: str = "gemma4:latest"
    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    api_key: str | None = None
    max_task_retries: int = 3
    max_plan_retries: int = 2
    enable_llm_reflection: bool = True
    trace_enabled: bool = True


@dataclass
class AgentState:
    """Current state of the agent."""

    current_plan: ExecutionPlan | None = None
    current_task_id: str | None = None
    task_attempts: int = 0
    total_llm_calls: int = 0
    execution_history: list[dict[str, Any]] = field(default_factory=list)
    is_complete: bool = False
    final_result: str | None = None
    force_write_command: bool = False  # 强制使用 write 命令替代 edit


class LLMClient:
    """
    Wrapper for LLM API calls.

    Uses ModelManager for unified model access.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self._model_manager: ModelManager | None = None

    def _get_model_manager(self) -> ModelManager:
        """Get or create the model manager."""
        if self._model_manager is None:
            self._model_manager = ModelManager(
                default_provider=self.config.provider,
                default_model=self.config.model,
                base_url=self.config.base_url,
            )
        return self._model_manager

    def chat(self, prompt: str, schema: dict[str, Any] | None = None) -> str:
        """Send a chat request to the LLM."""
        return self._get_model_manager().chat(prompt)

    def switch_model(self, provider: str, model: str | None = None) -> bool:
        """
        Switch to a different model.

        Args:
            provider: Provider name (ollama, openai, anthropic)
            model: Model name (optional)

        Returns:
            True if successful
        """
        return self._get_model_manager().set_model(provider, model)

    @property
    def current_model(self) -> str:
        """Get current model info."""
        return self._get_model_manager().get_status()


class AgentEngine:
    """
    Main Agent Engine implementing Plan → Act → Reflect loop.

    This is the core of the coding agent that:
    1. Plans: Decomposes tasks into subtasks
    2. Acts: Executes actions using tools
    3. Reflects: Analyzes results and determines next steps
    4. Revises: Adjusts plan based on failures
    """

    SYSTEM_PROMPT_TEMPLATE = """你是一个具备项目规划能力的 Coding Agent。

## 你的角色
你通过工具来完成任务。每次响应必须是一个有效的 JSON 对象。

## 可用工具
- write: 写入新文件 (参数: path, content)
- edit: 编辑文件 (参数: path, old_text, content)
- read: 读取文件 (参数: path, start, end)
- execute: 执行命令 (参数: script)
- search: 搜索文件 (参数: query, path)
- search_web: 网络搜索 (参数: query)
- web_fetch: 获取网页 (参数: url)
- list_dir: 列出目录 (参数: path)
- check_dependencies: 检查依赖 (参数: modules)
- run_tests: 运行测试
- git: Git 操作 (参数: git_args)
- mkdir: 创建目录 (参数: path)
- pip_install: 安装包 (参数: packages)
- create_file: 批量创建文件 (参数: files)
- debug: 调试输出 (参数: content)
- finish: 完成任务

## 工作流程
1. 理解任务 → 2. 规划步骤 → 3. 执行操作 → 4. 检查结果 → 5. 迭代改进

## 重要规则
- 每次只执行一个操作
- 总是检查上一步的结果
- 如果失败，分析原因并尝试替代方案
- 完成每个子任务后报告结果
- 最终使用 finish 标记任务完成

## 当前上下文
工作目录: {workspace}
模型: {model_info}
"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm = LLMClient(config)
        self.planner = TaskPlanner(self.llm)
        self.executor = ToolExecutor(str(config.workspace))
        self.reflector = ResultReflector(self.llm if config.enable_llm_reflection else None)
        self.memory = ConversationMemory()
        self.persistent_memory = PersistentMemory(
            memory_dir=str(config.workspace / "memory"),
            wiki_dir=str(config.workspace / "wiki")
        )
        self.session_memory = SessionMemory()
        self.state = AgentState()
        self.logger = TraceLogger(Path("logs")) if config.trace_enabled else None

        print(f"   🌐 Base URL: {config.base_url}")

    def run(self, task: str) -> str:
        """
        Run the agent on a task.

        Args:
            task: The task description

        Returns:
            Final result or error message
        """
        print(f"\n{'='*60}")
        print(f"🎯 开始执行任务: {task}")
        print(f"{'='*60}\n")

        self._log("agent_start", {"task": task})

        # Phase 1: Plan - Create execution plan
        plan = self._create_plan(task)
        self.state.current_plan = plan

        print(f"\n📋 执行计划已创建，共 {len(plan.subtasks)} 个子任务\n")

        # Phase 2: Act & Reflect loop
        while not self.state.is_complete:
            result = self._execute_next_task()
            if result is None:
                break  # All tasks completed

            should_continue = self._process_result(result)
            if not should_continue:
                break

        # Phase 3: Final verification
        self._finalize()

        return self.state.final_result or "Task completed"

    def _create_plan(self, task: str) -> ExecutionPlan:
        """Create an execution plan from the task."""
        # Get current project context
        context = self._get_project_context()

        print("🔄 正在分析任务并创建执行计划...")

        plan = self.planner.create_plan(task, context)
        self._log("plan_created", plan.to_dict())

        return plan

    def _get_project_context(self) -> str:
        """Get current project context for planning."""
        try:
            files = list(self.config.workspace.rglob("*"))
            file_list = "\n".join(
                f"{'[DIR]' if f.is_dir() else '[FILE]'} {f.relative_to(self.config.workspace)}"
                for f in files[:50]
            )
            return f"当前项目文件:\n{file_list}" if file_list else "项目为空"
        except Exception:
            return "无法获取项目上下文"

    def _execute_next_task(self) -> tuple[str, str, ExecutionResult] | None:
        """Execute the next pending task in the plan."""
        plan = self.state.current_plan
        if not plan:
            return None

        task = plan.get_next_task()
        if not task:
            return None

        self.state.current_task_id = task.id
        task.status = TaskStatus.IN_PROGRESS

        print(f"\n📌 开始执行: {task.description}")

        # Generate action for this task
        action = self._generate_action(task)

        # Execute the action
        result = self.executor.execute_action(action)

        return task.id, task.description, result

    def _generate_action(self, task) -> Action:
        """Generate an action for a task using LLM."""
        execution_summary = self._get_execution_summary()

                # 检查是否需要强制使用 write 命令
        force_write = getattr(self.state, 'force_write_command', False)
        if force_write:
            self.state.force_write_command = False  # 重置标志

        prompt = f"""你是一个编程助手。你需要为以下任务生成合适的操作。

## 当前任务
{task.description}

## 工作目录
{self.config.workspace}

## 已完成的任务
{execution_summary if execution_summary else "无"}
""" + ("""
## 重要提示
上次 edit 命令失败（old_text 在文件中未找到），请使用 write 命令重新生成完整文件内容。
""" if force_write else """
## 重要规则
1. 根据任务类型选择合适的命令：创建新文件用 write，修改现有文件用 edit，读取文件用 read，运行脚本用 execute
2. 禁止使用 finish 或 debug 命令
3. 必须包含具体的文件内容或操作参数
""") + """
## 常用命令格式
write: {{"command": "write", "path": "文件名", "content": "文件内容"}}
edit: {{"command": "edit", "path": "文件名", "old_text": "要替换的文本", "content": "新文本"}}
read: {{"command": "read", "path": "文件名", "start": 1, "end": 50}}
execute: {{"command": "execute", "script": "python 文件名.py", "path": "工作目录"}}

返回 JSON：
"""

        try:
            response = self.llm.chat(prompt, schema={"type": "json_object"})
            if isinstance(response, str):
                data = json.loads(response)
            else:
                data = response

            # 调试日志
            logger.debug(f"LLM 响应: {json.dumps(data, ensure_ascii=False)[:500]}")

            command = data.get("command", "write")  # 默认 write
            if command in ["finish", "debug"]:
                command = "write"  # 强制改成 write
            # 如果是 edit 命令但没有 old_text，改成 write
            if command == "edit" and not data.get("old_text"):
                command = "write"
            # 如果 force_write_command 被设置，强制使用 write
            if getattr(self.state, 'force_write_command', False):
                self.state.force_write_command = False
                command = "write"

            return Action(
                command=command,
                path=data.get("path"),
                content=data.get("content"),
                script=data.get("script"),
                query=data.get("query"),
                url=data.get("url"),
                modules=data.get("modules", []),
                packages=data.get("packages", []),
                files=data.get("files", []),
                old_text=data.get("old_text"),
                git_args=data.get("git_args"),
            )

        except json.JSONDecodeError:
            return Action(command="debug", content=f"无法解析任务: {task.description}")
        except Exception as e:
            return Action(command="debug", content=f"错误: {str(e)}")

    def _process_result(self, result: tuple[str, str, ExecutionResult]) -> bool:
        """Process execution result and determine next steps."""
        task_id, task_desc, exec_result = result
        plan = self.state.current_plan

        self._log("execution_result", {
            "task_id": task_id,
            "status": exec_result.status.value,
            "output": exec_result.output[:500],
        })

        is_error = exec_result.status == ExecutionStatus.FAILURE

        # Reflect on the result
        reflection = self.reflector.reflect(
            action_command=exec_result.command,
            execution_output=exec_result.output,
            is_error=is_error,
            context=task_desc,
        )

        print(f"\n📊 执行结果: {exec_result.status.value}")
        if is_error:
            print(f"   错误分析: {reflection.error_category.value if reflection.error_category else 'unknown'}")
            print(f"   建议: {reflection.suggestion or 'N/A'}")

        # Record in memory
        self.memory.add("assistant", f"Task: {task_desc}\nAction: {exec_result.command}")
        self.memory.add(
            "user",
            f"Result: {exec_result.output[:500]}\nReflection: {reflection.suggestion or 'Success'}",
        )

        task = plan.get_task_by_id(task_id)

        if reflection.is_successful:
            task.status = TaskStatus.COMPLETED
            task.result = exec_result.output
            print("   ✅ 任务完成")
        elif reflection.should_retry and task.retry_count < plan.max_attempts:
            # 如果是 edit 命令失败且 old_text not found，改为使用 write 命令
            if exec_result.command == "edit" and "old_text not found" in (exec_result.output or ""):
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                print(f"   🔄 edit 失败，改为使用 write 命令重试 ({task.retry_count}/{plan.max_attempts})")
                # 强制生成 write 命令而不是 edit
                self.state.force_write_command = True
            else:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                print(f"   🔄 准备重试 ({task.retry_count}/{plan.max_attempts})")
        else:
            task.status = TaskStatus.FAILED
            task.error = reflection.error_message
            print("   ❌ 任务失败")

        # Check if all tasks are done
        if plan.all_completed():
            self.state.is_complete = True
            self.state.final_result = "All tasks completed successfully"
            return False

        if plan.has_failures():
            self.state.is_complete = True
            self.state.final_result = "Plan completed with some failures"
            return False

        return True

    def _get_execution_summary(self) -> str:
        """Get a summary of execution history."""
        plan = self.state.current_plan
        if not plan:
            return "No plan yet"

        lines = []
        for task in plan.subtasks:
            status_icon = {
                TaskStatus.PENDING: "⏳",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
            }.get(task.status, "?")

            lines.append(f"- {status_icon} {task.description}")

        return "\n".join(lines)

    def _finalize(self) -> None:
        """Finalize the agent run."""
        plan = self.state.current_plan

        print(f"\n{'='*60}")
        print("📊 执行总结")
        print(f"{'='*60}")

        if plan:
            completed = sum(1 for t in plan.subtasks if t.status == TaskStatus.COMPLETED)
            failed = sum(1 for t in plan.subtasks if t.status == TaskStatus.FAILED)
            pending = sum(1 for t in plan.subtasks if t.status == TaskStatus.PENDING)

            print(f"完成: {completed} | 失败: {failed} | 待处理: {pending}")
            print(f"\n{self.planner.get_task_summary(plan)}")

        print(f"\n🎉 最终结果: {self.state.final_result}")

        self._log("agent_complete", {
            "final_result": self.state.final_result,
            "plan_summary": plan.to_dict() if plan else None,
        })

    def _log(self, event: str, payload: dict[str, Any]) -> None:
        """Log an event."""
        if self.logger:
            self.logger.log(event, payload)


def create_agent_from_env() -> AgentEngine:
    """Create an agent from environment variables."""
    from pathlib import Path

    workspace = Path(os.environ.get("WORKSPACE", "workspace"))
    workspace.mkdir(parents=True, exist_ok=True)

    config = AgentConfig(
        workspace=workspace,
        model=os.environ.get("MODEL_NAME", "gemma4:latest"),
        provider=os.environ.get("ACTIVE_PROVIDER", "ollama"),
        base_url=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        max_task_retries=int(os.environ.get("MAX_RETRIES", "3")),
        enable_llm_reflection=os.environ.get("ENABLE_LLM_REFLECTION", "true").lower() == "true",
    )

    return AgentEngine(config)
