"""External Memory Mode - 基于持久化日志、Git版本控制、功能清单的工作模式。

第二阶段：流程搭设
- 读取状态 → 编写代码 → 运行测试 → Git提交 → 清空上下文

这个模块提供完整的工作流程，用于在上下文接近上限时，
将工作状态持久化到外部存储，恢复时可以从上次中断的地方继续。
"""

import json
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from memory.state_manager import StateManager


class Phase(Enum):
    """工作流程阶段"""
    READ_STATE = "read_state"
    WRITE_CODE = "write_code"
    RUN_TESTS = "run_tests"
    GIT_COMMIT = "git_commit"
    CLEAR_CONTEXT = "clear_context"


@dataclass
class PhaseResult:
    """阶段执行结果"""
    phase: Phase
    status: str  # "started", "success", "failed", "skipped"
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0


@dataclass
class ExternalMemoryWorkflow:
    """
    外部记忆工作流程。

    整合 StateManager 和 Git，提供完整的工作流程：
    1. 读取状态 - 从 progress.json 加载待办任务
    2. 编写代码 - Agent 执行具体任务
    3. 运行测试 - 验证代码正确性
    4. Git提交 - 自动保存变更
    5. 清空上下文 - 释放 token
    """

    workspace: Path
    state_manager: StateManager | None = None
    auto_commit: bool = True
    commit_message_template: str = "feat: {task_name} - {timestamp}"

    _current_session_id: str | None = None
    _current_feature_id: str | None = None
    _current_task_id: str | None = None
    _phase_results: list[PhaseResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.state_manager is None:
            self.state_manager = StateManager(
                state_dir=str(self.workspace / "memory"),
                session_logs_dir=str(self.workspace / "memory" / "session_logs")
            )

    # ==================== 核心流程 ====================

    def start_workflow(
        self,
        task_name: str,
        feature_id: str | None = None,
        context: dict[str, Any] | None = None
    ) -> str:
        """
        开始一个新的工作流程。

        Args:
            task_name: 任务名称
            feature_id: 可选，关联的功能 ID
            context: 可选的上下文信息

        Returns:
            Session ID
        """
        self._phase_results = []

        # 开始会话
        self._current_session_id = self.state_manager.start_session(
            task_name=task_name,
            context={
                "feature_id": feature_id,
                **(context or {})
            }
        )

        # 如果有 feature_id，记录当前任务
        if feature_id:
            self._current_feature_id = feature_id
            # 获取或创建任务
            task_id = self._get_or_create_task(feature_id, task_name)
            self._current_task_id = task_id

        # 阶段 1: 读取状态
        self._execute_phase(Phase.READ_STATE)

        return self._current_session_id or ""

    def execute_code_phase(
        self,
        agent_callback,  # Agent 执行回调
        max_iterations: int = 10
    ) -> PhaseResult:
        """
        执行代码编写阶段。

        Args:
            agent_callback: Agent 执行回调函数，接收任务描述，返回结果
            max_iterations: 最大迭代次数

        Returns:
            阶段结果
        """
        result = self._execute_phase(Phase.WRITE_CODE, {
            "max_iterations": max_iterations,
            "agent_callback": str(agent_callback),  # 记录回调信息
        })

        # 执行 agent 回调
        if callable(agent_callback):
            iterations = 0
            task_desc = self._get_current_task_description()

            while iterations < max_iterations:
                iterations += 1
                iteration_result = agent_callback(task_desc, iterations)

                # 检查是否完成
                if iteration_result.get("complete"):
                    self.state_manager.add_checkpoint(
                        self._current_session_id or "",
                        Phase.WRITE_CODE.value,
                        "success",
                        f"任务完成于第 {iterations} 次迭代",
                        {"iterations": iterations, "result": iteration_result.get("summary", "")}
                    )
                    break
            else:
                # 达到最大迭代
                self.state_manager.add_checkpoint(
                    self._current_session_id or "",
                    Phase.WRITE_CODE.value,
                    "max_iterations",
                    f"达到最大迭代次数 {max_iterations}",
                    {"iterations": iterations}
                )

        return result

    def run_tests_phase(self, test_paths: list[str] | None = None) -> PhaseResult:
        """
        执行测试阶段。

        Args:
            test_paths: 可选，指定测试文件路径

        Returns:
            阶段结果
        """
        start_time = time.time()

        test_paths = test_paths or ["tests/"]
        all_passed = True
        results = []

        for test_path in test_paths:
            result = self._run_pytest(test_path)
            results.append(result)
            if result["returncode"] != 0:
                all_passed = False

        duration = time.time() - start_time

        phase_result = PhaseResult(
            phase=Phase.RUN_TESTS,
            status="success" if all_passed else "failed",
            summary=f"测试 {'全部通过' if all_passed else '有失败'}",
            details={
                "test_paths": test_paths,
                "results": results,
                "all_passed": all_passed
            },
            duration=duration
        )

        # 记录检查点
        if self._current_session_id:
            self.state_manager.add_checkpoint(
                self._current_session_id,
                Phase.RUN_TESTS.value,
                phase_result.status,
                phase_result.summary,
                phase_result.details
            )

        return phase_result

    def git_commit_phase(
        self,
        message: str | None = None,
        auto_stage: bool = True
    ) -> PhaseResult:
        """
        执行 Git 提交阶段。

        Args:
            message: 可选，提交消息
            auto_stage: 是否自动暂存所有更改

        Returns:
            阶段结果
        """
        start_time = time.time()

        try:
            # 自动暂存
            if auto_stage:
                self._git_add_all()

            # 获取变更统计
            status = self._git_status()
            has_changes = bool(status.get("staged") or status.get("modified"))

            if not has_changes:
                return PhaseResult(
                    phase=Phase.GIT_COMMIT,
                    status="skipped",
                    summary="没有需要提交的更改",
                    duration=time.time() - start_time
                )

            # 生成提交消息
            if message is None:
                task_desc = self._get_current_task_description()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                message = self.commit_message_template.format(
                    task_name=task_desc,
                    timestamp=timestamp
                )

            # 执行提交
            commit_result = self._git_commit(message)

            phase_result = PhaseResult(
                phase=Phase.GIT_COMMIT,
                status="success" if commit_result["success"] else "failed",
                summary=f"已提交: {message[:50]}..." if len(message) > 50 else f"已提交: {message}",
                details=commit_result,
                duration=time.time() - start_time
            )

            # 记录检查点
            if self._current_session_id:
                self.state_manager.add_checkpoint(
                    self._current_session_id,
                    Phase.GIT_COMMIT.value,
                    phase_result.status,
                    phase_result.summary,
                    phase_result.details
                )

            return phase_result

        except Exception as e:
            return PhaseResult(
                phase=Phase.GIT_COMMIT,
                status="failed",
                summary=f"Git 提交失败: {str(e)}",
                details={"error": str(e)},
                duration=time.time() - start_time
            )

    def clear_context_phase(self) -> PhaseResult:
        """
        执行清空上下文阶段。

        Returns:
            阶段结果
        """
        start_time = time.time()

        # 更新任务状态
        if self._current_feature_id and self._current_task_id:
            self.state_manager.update_task_status(
                self._current_feature_id,
                self._current_task_id,
                status="completed",
                result=self._get_task_summary()
            )

        # 结束会话
        if self._current_session_id:
            self.state_manager.end_session(
                self._current_session_id,
                final_result=self._get_task_summary()
            )

        phase_result = PhaseResult(
            phase=Phase.CLEAR_CONTEXT,
            status="success",
            summary="上下文已清空，工作状态已保存",
            details={
                "session_id": self._current_session_id,
                "task_id": self._current_task_id,
                "feature_id": self._current_feature_id
            },
            duration=time.time() - start_time
        )

        return phase_result

    def complete_workflow(self, final_message: str = "") -> dict[str, Any]:
        """
        完成整个工作流程。

        Args:
            final_message: 最终消息

        Returns:
            工作流程总结
        """
        # 执行所有剩余阶段
        if self._current_session_id:
            # 确保完成所有阶段
            self.git_commit_phase()
            self.clear_context_phase()

        return {
            "session_id": self._current_session_id,
            "feature_id": self._current_feature_id,
            "task_id": self._current_task_id,
            "phases_completed": [p.phase.value for p in self._phase_results],
            "summary": final_message or self._get_task_summary()
        }

    # ==================== 便捷方法 ====================

    def is_context_near_limit(self, estimated_tokens: int, limit: int = 15000) -> bool:
        """
        检查上下文是否接近限制。

        Args:
            estimated_tokens: 估算的 token 数
            limit: 限制值

        Returns:
            是否接近限制
        """
        return estimated_tokens > limit * 0.7  # 70% 时提示

    def should_activate(self, context_size: int) -> tuple[bool, str]:
        """
        判断是否应该激活外部记忆模式。

        Args:
            context_size: 当前上下文估算

        Returns:
            (是否激活, 建议消息)
        """
        return self.state_manager.should_prompt_user(context_size)

    def get_progress(self) -> dict[str, Any]:
        """获取当前进度"""
        return {
            "session_id": self._current_session_id,
            "feature_id": self._current_feature_id,
            "task_id": self._current_task_id,
            "phases": [p.phase.value for p in self._phase_results],
            "phase_count": len(self._phase_results)
        }

    # ==================== 私有方法 ====================

    def _execute_phase(self, phase: Phase, details: dict[str, Any] | None = None) -> PhaseResult:
        """执行单个阶段"""
        start_time = time.time()

        result = PhaseResult(
            phase=phase,
            status="started",
            summary=f"开始执行: {phase.value}",
            details=details or {}
        )

        # 记录检查点
        if self._current_session_id:
            self.state_manager.add_checkpoint(
                self._current_session_id,
                phase.value,
                "started",
                f"开始 {phase.value}",
                details
            )

        self._phase_results.append(result)
        result.duration = time.time() - start_time

        return result

    def _get_or_create_task(self, feature_id: str, task_name: str) -> str:
        """获取或创建任务"""
        task_id = self.state_manager.add_task_to_feature(
            feature_id,
            task_name,
            description="",
            status="in_progress"
        )
        return task_id or f"task_{int(time.time())}"

    def _get_current_task_description(self) -> str:
        """获取当前任务描述"""
        if self._current_task_id and self._current_feature_id:
            progress = self.state_manager._load_progress()
            for feature in progress.get("features", []):
                if feature["id"] == self._current_feature_id:
                    for task in feature.get("tasks", []):
                        if task["id"] == self._current_task_id:
                            return task.get("name", "Unknown task")
        return "未命名任务"

    def _get_task_summary(self) -> str:
        """获取任务总结"""
        return f"完成了 {len(self._phase_results)} 个阶段: " + \
               ", ".join([p.phase.value for p in self._phase_results])

    def _run_pytest(self, path: str) -> dict[str, Any]:
        """运行 pytest"""
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "-v", "--tb=short", path],
                capture_output=True,
                text=True,
                cwd=str(self.workspace),
                timeout=60
            )
            return {
                "path": path,
                "returncode": result.returncode,
                "stdout": result.stdout[:1000],
                "stderr": result.stderr[:500]
            }
        except Exception as e:
            return {
                "path": path,
                "returncode": -1,
                "error": str(e)
            }

    def _git_status(self) -> dict[str, Any]:
        """获取 Git 状态"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=str(self.workspace),
                timeout=10
            )

            staged = []
            modified = []
            untracked = []

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                status = line[:2]
                path = line[3:]

                if status[0] != " ":
                    staged.append(path)
                if status[1] == "M":
                    modified.append(path)
                if status == "??":
                    untracked.append(path)

            return {
                "staged": staged,
                "modified": modified,
                "untracked": untracked
            }
        except Exception:
            return {"staged": [], "modified": [], "untracked": []}

    def _git_add_all(self) -> None:
        """暂存所有更改"""
        try:
            subprocess.run(
                ["git", "add", "-A"],
                capture_output=True,
                cwd=str(self.workspace),
                timeout=10
            )
        except Exception:
            pass

    def _git_commit(self, message: str) -> dict[str, Any]:
        """执行 Git 提交"""
        try:
            result = subprocess.run(
                ["git", "commit", "-m", message],
                capture_output=True,
                text=True,
                cwd=str(self.workspace),
                timeout=30
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout + result.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


def create_external_memory_mode(workspace: Path | str) -> ExternalMemoryWorkflow:
    """
    创建外部记忆工作流程。

    Args:
        workspace: 工作目录路径

    Returns:
        ExternalMemoryWorkflow 实例
    """
    if isinstance(workspace, str):
        workspace = Path(workspace)

    return ExternalMemoryWorkflow(workspace=workspace)