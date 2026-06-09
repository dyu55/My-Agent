"""Agent Engine - Core agent loop integrating Plan/Act/Reflect."""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .planner import ExecutionPlan, TaskPlanner, TaskStatus
from .executor import Action, ExecutionResult, ExecutionStatus, ToolExecutor
from .reflector import ErrorCategory, Reflection, ResultReflector
from utils.model_provider import ModelManager
from utils.conversation import ConversationMemory
from utils.persistent_memory import PersistentMemory, SessionMemory
from utils.logger import TraceLogger
from utils.streaming_progress import StreamingProgress
from utils.small_model import ModelProfile, get_model_profile
from memory.cross_session_memory import CrossSessionMemory, get_cross_session_memory

logger = logging.getLogger(__name__)


def _extract_json_from_response(response: str) -> dict[str, Any] | list | None:
    """
    Extract JSON from model response, handling markdown code blocks.

    Models often return JSON wrapped in ```json ... ``` blocks.
    This function extracts the JSON content.

    Returns:
        Parsed JSON data (dict or list), or None if extraction fails.
    """
    if not isinstance(response, str):
        return response

    # Try direct parse first
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to extract from code blocks
    patterns = [
        r"```json\s*([\s\S]*?)\s*```",  # ```json ... ```
        r"```\s*([\s\S]*?)\s*```",      # ``` ... ```
    ]

    for pattern in patterns:
        match = re.search(pattern, response)
        if match:
            content = match.group(1).strip()
            if content.startswith("{") or content.startswith("["):
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    pass

    return None


def _normalize_action_data(data: dict[str, Any] | list) -> dict[str, Any]:
    """Normalize action JSON from various model output formats.

    Handles common variations:
    - "action" vs "command" vs "cmd" key names
    - Nested "args" dict (qwen3.5 sometimes does this)
    - List responses (take first item)
    """
    if isinstance(data, list):
        data = data[0] if data else {}

    if not isinstance(data, dict):
        return {}

    # Normalize command key: "action" → "command", "cmd" → "command"
    if "command" not in data:
        for alt in ("action", "cmd", "type"):
            if alt in data:
                data["command"] = data.pop(alt)
                break

    # Normalize nested args: some models put path/content inside "args"
    args = data.get("args")
    if isinstance(args, dict):
        for key in ("path", "content", "script", "old_text"):
            if key not in data and key in args:
                data[key] = args[key]

    return data


@dataclass
class AgentConfig:
    """Configuration for the agent."""

    workspace: Path
    model: str = "qwen3.5:9b"
    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    api_key: str | None = None
    max_task_retries: int = 3
    max_plan_retries: int = 2
    enable_llm_reflection: bool = True
    trace_enabled: bool = True
    # Callback for live progress updates (phase, task_desc, elapsed_seconds)
    progress_callback: Callable | None = None
    # Dual-model: separate models for thinking and executing
    think_model: str | None = None
    think_provider: str | None = None
    execute_model: str | None = None
    execute_provider: str | None = None
    # Resume and dry-run
    resume: bool = False
    dry_run: bool = False
    # Limits (learned from mini-swe-agent)
    max_llm_calls: int = 0      # 0 = no limit
    max_cost: float = 0.0       # 0 = no limit (estimated USD)
    wall_time_limit: int = 0    # seconds, 0 = no limit


@dataclass
class AgentState:
    """Current state of the agent."""

    current_plan: ExecutionPlan | None = None
    current_task_id: str | None = None
    task_attempts: int = 0
    total_llm_calls: int = 0
    estimated_cost: float = 0.0
    start_time: float = 0.0
    execution_history: list[dict[str, Any]] = field(default_factory=list)
    is_complete: bool = False
    final_result: str | None = None
    force_write_command: bool = False  # Force write command instead of edit
    written_files: list[dict[str, str]] = field(default_factory=list)  # {path, preview}


class LLMClient:
    """
    Wrapper for LLM API calls.

    Uses ModelManager for unified model access.
    Supports dual-model: separate managers for thinking and executing.
    """

    def __init__(self, config: AgentConfig):
        self.config = config
        self._model_manager: ModelManager | None = None
        self._think_manager: ModelManager | None = None
        self._execute_manager: ModelManager | None = None

    def _ensure_api_key(self) -> None:
        if self.config.api_key:
            os.environ["OLLAMA_API_KEY"] = self.config.api_key

    def _get_model_manager(self) -> ModelManager:
        """Get or create the default model manager."""
        if self._model_manager is None:
            self._ensure_api_key()
            self._model_manager = ModelManager(
                default_provider=self.config.provider,
                default_model=self.config.model,
                base_url=self.config.base_url,
            )
        return self._model_manager

    def _get_think_manager(self) -> ModelManager:
        """Get or create the think model manager."""
        if self._think_manager is None:
            self._ensure_api_key()
            self._think_manager = ModelManager(
                default_provider=self.config.think_provider or self.config.provider,
                default_model=self.config.think_model or self.config.model,
                base_url=self.config.base_url,
            )
        return self._think_manager

    def _get_execute_manager(self) -> ModelManager:
        """Get or create the execute model manager."""
        if self._execute_manager is None:
            self._ensure_api_key()
            self._execute_manager = ModelManager(
                default_provider=self.config.execute_provider or self.config.provider,
                default_model=self.config.execute_model or self.config.model,
                base_url=self.config.base_url,
            )
        return self._execute_manager

    def chat(self, prompt: str, schema: dict[str, Any] | None = None, **kwargs) -> str:
        """Send a chat request to the default LLM."""
        if schema:
            kwargs["schema"] = schema
        return self._get_model_manager().chat(prompt, **kwargs)

    def chat_think(self, prompt: str, schema: dict[str, Any] | None = None, **kwargs) -> str:
        """Send a chat request to the think model (planning, reflection)."""
        if schema:
            kwargs["schema"] = schema
        if self.config.think_model:
            return self._get_think_manager().chat(prompt, **kwargs)
        return self._get_model_manager().chat(prompt, **kwargs)

    def chat_execute(self, prompt: str, schema: dict[str, Any] | None = None, **kwargs) -> str:
        """Send a chat request to the execute model (action generation)."""
        if schema:
            kwargs["schema"] = schema
        if self.config.execute_model:
            return self._get_execute_manager().chat(prompt, **kwargs)
        return self._get_model_manager().chat(prompt, **kwargs)

    def switch_model(self, provider: str, model: str | None = None) -> bool:
        """Switch the default model."""
        return self._get_model_manager().set_model(provider, model)

    def switch_think_model(self, provider: str, model: str | None = None) -> bool:
        """Switch the think model."""
        self.config.think_provider = provider
        if model:
            self.config.think_model = model
        self._think_manager = None  # force re-create
        return True

    def switch_execute_model(self, provider: str, model: str | None = None) -> bool:
        """Switch the execute model."""
        self.config.execute_provider = provider
        if model:
            self.config.execute_model = model
        self._execute_manager = None  # force re-create
        return True

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

    SYSTEM_PROMPT_TEMPLATE = """You are a Coding Agent with project planning capabilities.

## Your Role
You complete tasks through tools. Every response must be a valid JSON object.

## Available Tools
- write: Write a new file (params: path, content)
- edit: Edit a file (params: path, old_text, content)
- read: Read a file (params: path, start, end)
- execute: Run a command (params: script)
- search: Search files (params: query, path)
- search_web: Web search (params: query)
- web_fetch: Fetch webpage (params: url)
- list_dir: List directory (params: path)
- check_dependencies: Check dependencies (params: modules)
- run_tests: Run tests
- git: Git operations (params: git_args)
- mkdir: Create directory (params: path)
- pip_install: Install packages (params: packages)
- create_file: Batch create files (params: files)
- debug: Debug output (params: content)
- finish: Complete task

## Workflow
1. Understand task → 2. Plan steps → 3. Execute actions → 4. Check results → 5. Iterate

## Rules
- Execute one action at a time
- Always check the previous step's result
- If failed, analyze the cause and try alternatives
- Report result after each subtask
- Use finish to mark task completion

## Context
Workspace: {workspace}
Model: {model_info}
"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.llm = LLMClient(config)
        self.model_profile = get_model_profile(config.model)
        self.planner = TaskPlanner(self.llm, model_profile=self.model_profile)
        self.executor = ToolExecutor(str(config.workspace))
        self.reflector = ResultReflector(
            self.llm if config.enable_llm_reflection else None,
            model_profile=self.model_profile,
        )
        # max_history_messages is total turns; max_pairs is conversation pairs (2 turns each)
        max_pairs = max(1, self.model_profile.max_history_messages // 2)
        self.memory = ConversationMemory(max_pairs=max_pairs)
        self.persistent_memory = PersistentMemory(
            memory_dir=str(config.workspace / "memory"),
            wiki_dir=str(config.workspace / "wiki")
        )
        self.session_memory = SessionMemory()
        self.state = AgentState()
        self.logger = TraceLogger(Path("logs")) if config.trace_enabled else None
        self.progress = StreamingProgress(enabled=True)
        self.cross_session_memory = get_cross_session_memory()

        # Project context cache (avoids repeated rglob on every plan)
        self._project_context_cache: str | None = None
        self._project_context_time: float = 0.0
        self._project_context_ttl: float = 60.0  # seconds

        print(f"   🌐 Base URL: {config.base_url}")
        print(f"   📐 Model profile: {self.model_profile.size_category} ({self.model_profile.param_billions}B)")
        if config.think_model:
            print(f"   🧠 Think model: {config.think_provider or config.provider}/{config.think_model}")
        if config.execute_model:
            print(f"   ⚡ Execute model: {config.execute_provider or config.provider}/{config.execute_model}")

    def run(self, task: str) -> str:
        """
        Run the agent on a task.

        Args:
            task: The task description

        Returns:
            Final result or error message
        """
        import time as _time
        self.state.start_time = _time.time()

        self.progress.start(task)
        self.progress.set_phase("plan")

        self._log("agent_start", {"task": task})

        # Report progress to callback
        if self.config.progress_callback:
            self.config.progress_callback("plan", "Analyzing task...", 0)

        # Try to resume from checkpoint
        plan = None
        if self.config.resume:
            plan = self._try_resume(task)

        # Phase 1: Plan - Create execution plan (if not resumed)
        if plan is None:
            plan = self._create_plan(task)
        self.state.current_plan = plan

        self.progress.set_total_tasks(len(plan.subtasks))
        completed = sum(1 for t in plan.subtasks if t.status == TaskStatus.COMPLETED)
        self.progress.log("📋", f"Plan created: {len(plan.subtasks)} subtasks ({completed} done)", "success")

        # Dry-run mode: preview actions without executing
        if self.config.dry_run:
            return self._dry_run_plan(plan)

        # Fast-path: single-subtask plans skip the reflect loop
        if len(plan.subtasks) == 1 and plan.subtasks[0].status == TaskStatus.PENDING:
            return self._run_single_task_fast(plan.subtasks[0])

        # Phase 2: Act & Reflect loop
        while not self.state.is_complete:
            # Check limits (learned from mini-swe-agent)
            limit_msg = self._check_limits()
            if limit_msg:
                self.state.final_result = limit_msg
                self.progress.log("⛔", limit_msg, "error")
                break

            result = self._execute_next_task()
            if result is None:
                break  # All tasks completed

            should_continue = self._process_result(result)
            if not should_continue:
                break

            # Save checkpoint after each subtask
            self._save_checkpoint(task, plan)

        # Phase 3: Final verification
        self._finalize()

        return self.state.final_result or "Task completed"

    def _run_single_task_fast(self, task) -> str:
        """Fast-path for single-subtask plans: generate action, execute, done."""
        task.status = TaskStatus.IN_PROGRESS

        if self.config.progress_callback:
            self.config.progress_callback("act", task.description[:80], 0)

        action = self._generate_action(task)
        self.state.total_llm_calls += 1

        if self.config.progress_callback:
            action_detail = f"{action.command}"
            if action.path:
                action_detail += f" → {action.path}"
            self.config.progress_callback("action", action_detail, 0)

        result = self.executor.execute_action(action)

        if self.config.progress_callback:
            status = "OK" if result.status == ExecutionStatus.SUCCESS else "FAIL"
            output_preview = (result.output or result.error or "")[:200]
            self.config.progress_callback("result", f"[{status}] {output_preview}", 0)

        if result.status == ExecutionStatus.SUCCESS:
            task.status = TaskStatus.COMPLETED
            task.result = result.output
            return result.output or "Task completed"
        else:
            # Use reflector to analyze error (learned from mini-swe-agent pattern)
            reflection = self.reflector.reflect(
                action_command=result.command,
                execution_output=result.output or result.error or "",
                is_error=True,
                context=task.description,
            )
            task.error = reflection.error_message

            # Retry with force write and error context
            self.state.force_write_command = True
            action = self._generate_action(task)
            self.state.total_llm_calls += 1
            result = self.executor.execute_action(action)
            if result.status == ExecutionStatus.SUCCESS:
                task.status = TaskStatus.COMPLETED
                return result.output or "Task completed"
            task.status = TaskStatus.FAILED
            task.error = result.error
            return f"Task failed: {result.error}"

    def _create_plan(self, task: str) -> ExecutionPlan:
        """Create an execution plan from the task."""
        # Get current project context
        context = self._get_project_context()

        self.progress.update_task("Analyzing task and creating plan...")
        self.progress.log("🧠", "Analyzing task...", "info")

        plan = self.planner.create_plan(task, context)
        self._log("plan_created", plan.to_dict())

        # Report plan completion to callback
        if self.config.progress_callback:
            self.config.progress_callback("act", f"Executing {len(plan.subtasks)} subtasks", 0)

        return plan

    def _get_project_context(self) -> str:
        """Get current project context for planning, limited by model profile."""
        import time as _time
        now = _time.time()
        if (
            self._project_context_cache is not None
            and now - self._project_context_time < self._project_context_ttl
        ):
            return self._project_context_cache

        try:
            max_files = self.model_profile.max_file_context_files
            files = list(self.config.workspace.rglob("*"))
            file_list = "\n".join(
                f"{'[DIR]' if f.is_dir() else '[FILE]'} {f.relative_to(self.config.workspace)}"
                for f in files[:max_files]
            )
            result = f"Project files:\n{file_list}" if file_list else "Empty project"
        except Exception:
            result = "Unable to get project context"

        self._project_context_cache = result
        self._project_context_time = now
        return result

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

        self.progress.set_phase("act")
        self.progress.update_task(task.description)

        # Report progress to callback
        if self.config.progress_callback:
            self.config.progress_callback("act", task.description[:80], 0)

        # Generate action for this task
        action = self._generate_action(task)
        self.progress.increment_llm_calls()
        self.state.total_llm_calls += 1

        # Report action detail
        if self.config.progress_callback:
            action_detail = f"{action.command}"
            if action.path:
                action_detail += f" → {action.path}"
            elif action.script:
                action_detail += f" → {action.script[:60]}"
            self.config.progress_callback("action", action_detail, 0)

        # Execute the action
        result = self.executor.execute_action(action)
        self.progress.increment_tool_execution()

        # Track written files for context
        if result.status == ExecutionStatus.SUCCESS and action.command == "write" and action.path and action.content:
            preview = action.content[:300].replace("\n", " ")
            self.state.written_files.append({"path": action.path, "preview": preview})
            # Keep only last 10 files
            if len(self.state.written_files) > 10:
                self.state.written_files = self.state.written_files[-10:]

        # Report result
        if self.config.progress_callback:
            status = "OK" if result.status == ExecutionStatus.SUCCESS else "FAIL"
            output_preview = (result.output or result.error or "")[:200]
            self.config.progress_callback("result", f"[{status}] {output_preview}", 0)

        return task.id, task.description, result

    def _get_written_files_context(self) -> str:
        """Build context string from recently written files."""
        if not self.state.written_files:
            return ""
        lines = ["## Files created in this session"]
        for f in self.state.written_files:
            path = f["path"]
            preview = f["preview"][:150]
            lines.append(f"- {path}: {preview}...")
        return "\n".join(lines)

    def _get_conventions_context(self) -> str:
        """Load project conventions from CONVENTIONS.md if present."""
        for name in ("CONVENTIONS.md", "CONVENTIONS", ".conventions.md"):
            path = self.config.workspace / name
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8")[:1000]
                    return f"## Project Conventions\n{content}"
                except Exception:
                    pass
        return ""

    def _build_action_prompt(self, task, execution_summary: str, force_write: bool) -> str:
        """Build action generation prompt, adapted to model size."""
        profile = self.model_profile

        if profile.prefer_short_prompts:
            # Compressed prompt for 8B/9B models
            if force_write:
                return f"""Generate JSON action for this task. Use "write" command (last edit failed).

Task: {task.description}
Dir: {self.config.workspace}
Done: {execution_summary[:200] if execution_summary else "none"}

Commands: write({{"command":"write","path":"file","content":"..."}});
Return JSON only:"""

            return f"""Generate JSON action for this task.

Task: {task.description}
Dir: {self.config.workspace}
Done: {execution_summary[:200] if execution_summary else "none"}
{self._get_written_files_context()[:300]}
{self._get_conventions_context()[:300]}

Commands: write(path,content), edit(path,old_text,content), read(path), execute(script)
Rules: Use write/edit. No finish/debug. Include file content.
Return JSON only:"""

        # Full prompt for medium/large models
        if force_write:
            return f"""You are a programming assistant. Generate an action for the task.

## Current Task
{task.description}

## Workspace
{self.config.workspace}

## Completed Tasks
{execution_summary if execution_summary else "None"}

## Important
The previous edit command failed (old_text not found in file). Please use the write command to regenerate the full file content.

{self._get_conventions_context()}

Return JSON:
"""

        return f"""You are a programming assistant. Generate an action for the task.

## Current Task
{task.description}

## Workspace
{self.config.workspace}

## Completed Tasks
{execution_summary if execution_summary else "None"}

{self._get_written_files_context()}

{self._get_conventions_context()}

## Rules
1. Use write for new files, edit for modifying existing files, read for reading, execute for scripts
2. Do NOT use finish or debug commands
3. Must include concrete file content or operation parameters

## Command Formats
write: {{"command": "write", "path": "filename", "content": "file content"}}
edit: {{"command": "edit", "path": "filename", "old_text": "text to replace", "content": "new text"}}
read: {{"command": "read", "path": "filename", "start": 1, "end": 50}}
execute: {{"command": "execute", "script": "python filename.py", "path": "workspace"}}

Return JSON:
"""

    def _generate_action(self, task) -> Action:
        """Generate an action for a task using LLM."""
        execution_summary = self._get_execution_summary()

        # Check if force write command is needed
        force_write = getattr(self.state, 'force_write_command', False)
        if force_write:
            self.state.force_write_command = False  # Reset flag

        prompt = self._build_action_prompt(task, execution_summary, force_write)

        try:
            messages = self.memory.build_messages(system_prompt=prompt)
            # Pass empty prompt — system prompt is already in messages[0]
            response = self.llm.chat_execute("", messages=messages, schema={"type": "json_object"})

            # Extract JSON from markdown code blocks
            data = _extract_json_from_response(response)

            if data is None:
                # Include raw response snippet for debugging
                snippet = response[:200].replace("\n", " ") if response else "empty"
                return Action(command="debug", content=f"Unable to parse task: {task.description}. Raw response: {snippet}")

            # Normalize action data (handle "action" vs "command", nested "args", etc.)
            data = _normalize_action_data(data)

            if not isinstance(data, dict) or not data:
                return Action(command="debug", content=f"Invalid response type: {type(data)}")

            # Debug log
            logger.debug(f"LLM response: {json.dumps(data, ensure_ascii=False)[:500]}")

            command = data.get("command", "write")  # Default write
            if command in ["finish", "debug"]:
                command = "write"  # Force to write
            # If edit command but no old_text, change to write
            if command == "edit" and not data.get("old_text"):
                command = "write"
            # If force_write_command is set, force use write
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
            return Action(command="debug", content=f"Unable to parse task: {task.description}")
        except Exception as e:
            return Action(command="debug", content=f"Error: {str(e)}")

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
        self.progress.set_phase("reflect")
        reflection = self.reflector.reflect(
            action_command=exec_result.command,
            execution_output=exec_result.output,
            is_error=is_error,
            context=task_desc,
        )

        # Report reflect phase to callback
        if self.config.progress_callback:
            phase = "reflect"
            if is_error:
                phase = f"error"
            elif reflection.is_successful:
                phase = "done"
            self.config.progress_callback(phase, task_desc[:50], 0)

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
            self.progress.task_completed()
            self.progress.log("✅", f"Task completed: {task.description[:50]}", "success")

            # Learn from successful execution
            self._learn_from_task(task, exec_result)
        elif reflection.should_retry and task.retry_count < plan.max_attempts:
            # If edit command failed and old_text not found, switch to write command
            if exec_result.command == "edit" and "old_text not found" in (exec_result.output or ""):
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.error = reflection.error_message  # Preserve error for context
                self.progress.log("🔄", f"edit failed, using write retry ({task.retry_count}/{plan.max_attempts})", "warning")
                # Force generate write command instead of edit
                self.state.force_write_command = True
            else:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.error = reflection.error_message  # Preserve error for context
                self.progress.log("🔄", f"Retrying ({task.retry_count}/{plan.max_attempts})", "warning")
        else:
            task.status = TaskStatus.FAILED
            task.error = reflection.error_message
            self.progress.task_failed()
            self.progress.log("❌", f"Task failed: {task.description[:50]}", "error")
            if is_error:
                self.progress.log("💡", f"Suggestion: {reflection.suggestion or 'N/A'}", "info")

        # Check if all tasks are done (completed or failed)
        if plan.all_completed():
            self.state.is_complete = True
            self.state.final_result = "All tasks completed successfully"
            return False

        # Only stop early if all remaining tasks are blocked by failures
        # Otherwise, continue executing remaining tasks
        next_task = plan.get_next_task()
        if next_task is None:
            # No more tasks to execute — all are either done or permanently failed
            self.state.is_complete = True
            self.state.final_result = "Plan completed" + (" with some failures" if plan.has_failures() else "")
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

            line = f"- {status_icon} {task.description}"
            # Include error context for failed tasks (helps model learn from mistakes)
            if task.status == TaskStatus.FAILED and task.error:
                error_preview = task.error[:150].replace("\n", " ")
                line += f"\n  Error: {error_preview}"
            # Include result preview for completed tasks
            if task.status == TaskStatus.COMPLETED and task.result:
                result_preview = task.result[:100].replace("\n", " ")
                line += f"\n  Result: {result_preview}"

            lines.append(line)

        return "\n".join(lines)

    # ── Limits (learned from mini-swe-agent) ─────────────────────

    def _check_limits(self) -> str | None:
        """Check if any limits are exceeded. Returns error message or None."""
        import time as _time

        cfg = self.config

        if cfg.max_llm_calls > 0 and self.state.total_llm_calls >= cfg.max_llm_calls:
            return f"LLM call limit ({cfg.max_llm_calls}) reached"

        if cfg.wall_time_limit > 0:
            elapsed = _time.time() - self.state.start_time
            if elapsed >= cfg.wall_time_limit:
                return f"Wall time limit ({cfg.wall_time_limit}s) reached (elapsed {int(elapsed)}s)"

        if cfg.max_cost > 0 and self.state.estimated_cost >= cfg.max_cost:
            return f"Cost limit (${cfg.max_cost:.2f}) reached"

        return None

    # ── Checkpoint: save/resume ──────────────────────────────────

    def _checkpoint_path(self) -> Path:
        """Path to the checkpoint file."""
        return self.config.workspace / ".agent_checkpoint.json"

    def _save_checkpoint(self, task: str, plan: ExecutionPlan) -> None:
        """Save current plan state to disk for resumption."""
        try:
            data = {
                "task": task,
                "plan": plan.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "completed_count": sum(1 for t in plan.subtasks if t.status == TaskStatus.COMPLETED),
                "total_count": len(plan.subtasks),
            }
            self._checkpoint_path().write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass  # checkpoint save should never crash the agent

    def _try_resume(self, task: str) -> ExecutionPlan | None:
        """Try to resume from a checkpoint file. Returns plan or None."""
        path = self._checkpoint_path()
        if not path.exists():
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            saved_task = data.get("task", "")

            # Only resume if the task matches
            if saved_task.strip() != task.strip():
                return None

            plan_data = data.get("plan", {})
            plan = ExecutionPlan(main_goal=plan_data.get("main_goal", task))

            for st in plan_data.get("subtasks", []):
                subtask = SubTask(
                    id=st["id"],
                    description=st["description"],
                    status=TaskStatus(st.get("status", "pending")),
                    dependencies=st.get("dependencies", []),
                    result=st.get("result"),
                    error=st.get("error"),
                    retry_count=st.get("retry_count", 0),
                )
                plan.subtasks.append(subtask)

            completed = sum(1 for t in plan.subtasks if t.status == TaskStatus.COMPLETED)
            total = len(plan.subtasks)
            self.progress.log("🔄", f"Resumed from checkpoint: {completed}/{total} completed", "info")
            self._log("resume", {"completed": completed, "total": total})

            return plan

        except Exception:
            return None

    def _clear_checkpoint(self) -> None:
        """Remove checkpoint file after successful completion."""
        try:
            path = self._checkpoint_path()
            if path.exists():
                path.unlink()
        except Exception:
            pass

    # ── Trajectory: full message history ─────────────────────────

    def _save_trajectory(self) -> None:
        """Save full execution trajectory for debugging."""
        import time as _time
        try:
            plan = self.state.current_plan
            data = {
                "task": plan.main_goal if plan else "",
                "model": self.config.model,
                "provider": self.config.provider,
                "llm_calls": self.state.total_llm_calls,
                "estimated_cost": self.state.estimated_cost,
                "elapsed_seconds": int(_time.time() - self.state.start_time) if self.state.start_time else 0,
                "plan": plan.to_dict() if plan else None,
                "final_result": self.state.final_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            path = self.config.workspace / ".agent_trajectory.json"
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    # ── Dry-run: preview without executing ───────────────────────

    def _dry_run_plan(self, plan: ExecutionPlan) -> str:
        """Preview all actions without executing them."""
        lines = []
        lines.append(f"\n🔍 DRY RUN — Preview Mode")
        lines.append(f"{'='*60}")

        for i, subtask in enumerate(plan.subtasks, 1):
            status_icon = {
                TaskStatus.COMPLETED: "✅",
                TaskStatus.FAILED: "❌",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.PENDING: "⏳",
            }.get(subtask.status, "❓")

            lines.append(f"\n  [{i}] {status_icon} {subtask.description}")

            if subtask.status == TaskStatus.COMPLETED:
                lines.append(f"      Already completed, skipping")
                continue

            if subtask.status == TaskStatus.FAILED:
                lines.append(f"      Failed: {subtask.error or 'N/A'}")
                continue

            # Generate action preview
            try:
                action = self._generate_action(subtask)
                cmd = action.command
                path = action.path or ""
                content = action.content or ""

                lines.append(f"      Command: {cmd}")
                if path:
                    lines.append(f"      Path: {path}")
                if content:
                    preview = content[:200].replace("\n", "\n      ")
                    lines.append(f"      Content: {preview}...")
                    lines.append(f"      ({len(content)} chars)")
            except Exception as e:
                lines.append(f"      ⚠️ Failed to generate action: {e}")

        lines.append(f"\n{'='*60}")
        lines.append(f"🔍 Dry run complete. Remove --dry-run flag to execute.")
        lines.append(f"{'='*60}")

        result = "\n".join(lines)
        print(result)
        return result

    def _finalize(self) -> None:
        """Finalize the agent run."""
        plan = self.state.current_plan
        self.progress.set_phase("done")

        if plan:
            completed = sum(1 for t in plan.subtasks if t.status == TaskStatus.COMPLETED)
            failed = sum(1 for t in plan.subtasks if t.status == TaskStatus.FAILED)
            pending = sum(1 for t in plan.subtasks if t.status == TaskStatus.PENDING)

            summary = f"Completed: {completed} | Failed: {failed} | Pending: {pending}"
        else:
            summary = "No execution plan"

        self.progress.finish(f"{self.state.final_result or 'Done'}")

        if plan:
            print(f"\n📋 {self.planner.get_task_summary(plan)}")

        self._log("agent_complete", {
            "final_result": self.state.final_result,
            "plan_summary": plan.to_dict() if plan else None,
        })

        # Cleanup stale patterns
        self.cross_session_memory.cleanup_stale()

        # Clear checkpoint on completion
        self._clear_checkpoint()

        # Save trajectory for debugging
        self._save_trajectory()

    def _learn_from_task(self, task, exec_result: ExecutionResult) -> None:
        """Learn from successful task execution."""
        try:
            # Extract tags from task description
            tags = [t.lower() for t in task.description.split() if len(t) > 2]

            self.cross_session_memory.learn(
                name=f"Task: {task.description[:60]}",
                pattern_type=CrossSessionMemory.TYPE_TASK,
                content=f"Task: {task.description}\nResult: {exec_result.output[:500]}",
                description=f"Successfully executed: {task.description}",
                tags=tags,
            )
        except Exception:
            # Learning failures should not affect main flow
            pass

    def _recall_patterns(self, query: str, limit: int = 3) -> list:
        """Recall relevant patterns from cross-session memory."""
        try:
            patterns = self.cross_session_memory.recall(query, limit=limit)
            return patterns
        except Exception:
            return []

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
        think_model=os.environ.get("THINK_MODEL"),
        think_provider=os.environ.get("THINK_PROVIDER"),
        execute_model=os.environ.get("EXECUTE_MODEL"),
        execute_provider=os.environ.get("EXECUTE_PROVIDER"),
    )

    return AgentEngine(config)
