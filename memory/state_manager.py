"""State Manager - 管理外部记忆状态和进度表。

外部记忆模式核心组件，负责：
1. 读取/写入进度表 (progress.json)
2. 持久化会话日志
3. 状态检查点管理
"""

import json
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class StateManager:
    """
    外部记忆状态管理器。

    管理功能清单、进度表、会话日志的生命周期。
    """

    def __init__(
        self,
        state_dir: str = "memory",
        session_logs_dir: str = "memory/session_logs"
    ):
        self.state_dir = Path(state_dir)
        self.session_logs_dir = Path(session_logs_dir)
        self.progress_file = self.state_dir / "progress.json"

        # 确保目录存在
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.session_logs_dir.mkdir(parents=True, exist_ok=True)

        self._init_progress_file()

    def _init_progress_file(self) -> None:
        """初始化进度表文件"""
        if not self.progress_file.exists():
            default_progress = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "metadata": {
                    "project_name": "MyAgent",
                    "description": "本地 Coding Agent",
                    "current_phase": "phase_1_scaffolding"
                },
                "features": [],
                "tasks": []
            }
            self._save_progress(default_progress)

    def _load_progress(self) -> dict[str, Any]:
        """加载进度表"""
        if self.progress_file.exists():
            with open(self.progress_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_progress(self, data: dict[str, Any]) -> None:
        """保存进度表"""
        data["updated_at"] = datetime.now().isoformat()
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ==================== 功能清单管理 ====================

    def add_feature(self, name: str, description: str = "", priority: int = 0) -> str:
        """
        添加新功能到清单。

        Args:
            name: 功能名称
            description: 功能描述
            priority: 优先级 (0=低, 1=中, 2=高)

        Returns:
            功能 ID
        """
        progress = self._load_progress()
        feature_id = f"feat_{len(progress.get('features', [])) + 1:03d}"

        feature = {
            "id": feature_id,
            "name": name,
            "description": description,
            "priority": priority,
            "status": "pending",
            "tasks": [],
            "created_at": datetime.now().isoformat()
        }

        if "features" not in progress:
            progress["features"] = []
        progress["features"].append(feature)
        self._save_progress(progress)

        return feature_id

    def update_feature_status(self, feature_id: str, status: str) -> bool:
        """更新功能状态"""
        progress = self._load_progress()
        for feature in progress.get("features", []):
            if feature["id"] == feature_id:
                feature["status"] = status
                feature["updated_at"] = datetime.now().isoformat()
                self._save_progress(progress)
                return True
        return False

    def get_features(self, status: str | None = None) -> list[dict[str, Any]]:
        """
        获取功能列表。

        Args:
            status: 可选，按状态过滤

        Returns:
            功能列表
        """
        progress = self._load_progress()
        features = progress.get("features", [])

        if status:
            return [f for f in features if f.get("status") == status]
        return features

    def add_task_to_feature(
        self,
        feature_id: str,
        task_name: str,
        description: str = "",
        status: str = "pending"
    ) -> str | None:
        """
        为功能添加任务。

        Returns:
            任务 ID，失败返回 None
        """
        progress = self._load_progress()
        for feature in progress.get("features", []):
            if feature["id"] == feature_id:
                task_id = f"{feature_id}_task_{len(feature.get('tasks', [])) + 1:02d}"
                task = {
                    "id": task_id,
                    "name": task_name,
                    "description": description,
                    "status": status,
                    "created_at": datetime.now().isoformat()
                }

                if "tasks" not in feature:
                    feature["tasks"] = []
                feature["tasks"].append(task)
                self._save_progress(progress)
                return task_id
        return None

    def update_task_status(
        self,
        feature_id: str,
        task_id: str,
        status: str,
        result: str = ""
    ) -> bool:
        """更新任务状态"""
        progress = self._load_progress()
        for feature in progress.get("features", []):
            if feature["id"] == feature_id:
                for task in feature.get("tasks", []):
                    if task["id"] == task_id:
                        task["status"] = status
                        task["updated_at"] = datetime.now().isoformat()
                        if result:
                            task["result"] = result
                        self._save_progress(progress)
                        return True
        return False

    def get_feature_progress(self, feature_id: str) -> dict[str, Any]:
        """
        获取功能的进度统计。

        Returns:
            {"total": N, "completed": N, "percentage": float}
        """
        progress = self._load_progress()
        for feature in progress.get("features", []):
            if feature["id"] == feature_id:
                tasks = feature.get("tasks", [])
                total = len(tasks)
                completed = len([t for t in tasks if t.get("status") == "completed"])
                return {
                    "total": total,
                    "completed": completed,
                    "percentage": (completed / total * 100) if total > 0 else 0
                }
        return {"total": 0, "completed": 0, "percentage": 0}

    # ==================== 会话日志管理 ====================

    def start_session(self, task_name: str, context: dict[str, Any] | None = None) -> str:
        """
        开始新会话，记录到日志。

        Args:
            task_name: 当前任务名称
            context: 可选的上下文信息

        Returns:
            会话 ID
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session_data = {
            "id": session_id,
            "task_name": task_name,
            "started_at": datetime.now().isoformat(),
            "context": context or {},
            "checkpoints": [],
            "events": []
        }

        # 保存会话初始状态
        session_file = self.session_logs_dir / f"{session_id}.json"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

        # 更新当前会话引用
        self._save_session_ref(session_id)

        return session_id

    def add_checkpoint(
        self,
        session_id: str,
        phase: str,
        status: str,
        summary: str,
        details: dict[str, Any] | None = None
    ) -> None:
        """
        添加检查点。

        Args:
            session_id: 会话 ID
            phase: 阶段名称 (read_state/write_code/run_tests/git_commit/clear_context)
            status: 状态 (started/success/failed)
            summary: 简要总结
            details: 详细信息
        """
        session_file = self.session_logs_dir / f"{session_id}.json"
        if not session_file.exists():
            return

        with open(session_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)

        checkpoint = {
            "phase": phase,
            "status": status,
            "summary": summary,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        session_data["checkpoints"].append(checkpoint)

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

    def end_session(self, session_id: str, final_result: str) -> None:
        """结束会话"""
        session_file = self.session_logs_dir / f"{session_id}.json"
        if not session_file.exists():
            return

        with open(session_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)

        session_data["ended_at"] = datetime.now().isoformat()
        session_data["final_result"] = final_result

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

    def get_recent_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取最近的会话"""
        sessions = []
        for session_file in sorted(
            self.session_logs_dir.glob("session_*.json"),
            reverse=True
        )[:limit]:
            with open(session_file, "r", encoding="utf-8") as f:
                sessions.append(json.load(f))
        return sessions

    def _save_session_ref(self, session_id: str) -> None:
        """保存当前会话引用"""
        ref_file = self.state_dir / "current_session.json"
        with open(ref_file, "w", encoding="utf-8") as f:
            json.dump({"current_session": session_id}, f)

    def get_current_session(self) -> str | None:
        """获取当前会话 ID"""
        ref_file = self.state_dir / "current_session.json"
        if ref_file.exists():
            with open(ref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("current_session")
        return None

    # ==================== 状态检查 ====================

    def needs_external_memory(self, context_size: int, threshold: int = 8000) -> bool:
        """
        检查是否需要开启外部记忆模式。

        Args:
            context_size: 当前上下文 token 数（估算）
            threshold: 阈值

        Returns:
            是否需要外部记忆
        """
        return context_size > threshold

    def should_prompt_user(self, context_size: int) -> tuple[bool, str]:
        """
        判断是否应该询问用户开启外部记忆。

        Args:
            context_size: 当前上下文估算

        Returns:
            (是否询问, 建议消息)
        """
        if context_size > 12000:
            return True, "上下文接近上限，建议开启外部记忆模式以保存进度"
        elif context_size > 8000:
            return True, "上下文已占用 60%，是否开启外部记忆模式？"
        return False, ""

    # ==================== 便捷方法 ====================

    def get_summary(self) -> str:
        """获取项目状态摘要"""
        progress = self._load_progress()
        features = progress.get("features", [])

        total_tasks = sum(len(f.get("tasks", [])) for f in features)
        completed_tasks = sum(
            len([t for t in f.get("tasks", []) if t.get("status") == "completed"])
            for f in features
        )

        return (
            f"项目: {progress.get('metadata', {}).get('project_name', 'Unknown')}\n"
            f"阶段: {progress.get('metadata', {}).get('current_phase', 'N/A')}\n"
            f"功能: {len(features)} 个\n"
            f"任务: {completed_tasks}/{total_tasks} 完成"
        )
