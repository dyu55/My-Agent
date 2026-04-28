"""Test Layer 1 Integration: StateManager + EmbeddingStore

测试 StateManager 与 EmbeddingStore 的集成：
- capture_session_metadata 自动捕获
- search_memories 搜索功能
- auto_capture_on_task_complete 钩子
"""

import json
import tempfile
from pathlib import Path

import pytest

from memory.state_manager import StateManager
from memory.embedding_store import EmbeddingStore


class TestStateManagerEmbeddingIntegration:
    """StateManager 与 EmbeddingStore 集成测试"""

    @pytest.fixture
    def temp_state_manager(self):
        """临时状态管理器"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = StateManager(
                state_dir=tmpdir,
                session_logs_dir=f"{tmpdir}/sessions",
            )
            yield sm

    def test_embedding_store_lazy_loaded(self, temp_state_manager):
        """EmbeddingStore 延迟加载"""
        # 初始状态下应该没有 embedding_store
        assert temp_state_manager._embedding_store is None

        # 访问时加载
        store = temp_state_manager.embedding_store

        assert store is not None
        assert isinstance(store, EmbeddingStore)

    def test_capture_session_metadata(self, temp_state_manager):
        """capture_session_metadata 正确存储"""
        memory_id = temp_state_manager.capture_session_metadata(
            session_id="session_test_001",
            task_name="Implement user authentication",
            files_changed=["auth/login.py", "auth/models.py"],
            commit_message="feat: add user auth",
            summary="Basic login/logout functionality"
        )

        assert memory_id.startswith("mem_")

        # 验证存储到 embedding store
        results = temp_state_manager.search_memories("authentication")
        assert len(results) == 1
        assert results[0]["id"] == memory_id

    def test_capture_extracts_file_tags(self, temp_state_manager):
        """capture_session_metadata 提取文件标签"""
        memory_id = temp_state_manager.capture_session_metadata(
            session_id="session_test_002",
            task_name="Python refactoring",
            files_changed=["core/utils.py", "models/user.py"],
        )

        results = temp_state_manager.search_memories("python refactoring")

        assert len(results) == 1
        # 应该包含 py 标签（从 .py 文件扩展名）
        assert "py" in results[0]["tags"]

    def test_search_memories(self, temp_state_manager):
        """search_memories 返回结果"""
        # 存储多个记忆
        temp_state_manager.capture_session_metadata(
            session_id="session_test_003",
            task_name="Fix authentication bug",
            files_changed=["auth/login.py"],
        )
        temp_state_manager.capture_session_metadata(
            session_id="session_test_003",
            task_name="Add password reset feature",
            files_changed=["auth/reset.py"],
        )

        # 搜索
        results = temp_state_manager.search_memories("authentication")

        assert len(results) >= 1
        assert any("authentication" in r["content"] for r in results)

    def test_search_with_tag_filter(self, temp_state_manager):
        """search_memories 按标签过滤"""
        temp_state_manager.capture_session_metadata(
            session_id="session_test_004",
            task_name="Fix login bug",
            files_changed=["auth/login.py"],
        )
        temp_state_manager.capture_session_metadata(
            session_id="session_test_004",
            task_name="Add social login",
            files_changed=["auth/social.py"],
        )

        # 只搜索包含 "login" 的记忆
        results = temp_state_manager.search_memories("login")

        assert len(results) >= 1
        assert all("login" in r["content"].lower() for r in results)

    def test_get_session_memories(self, temp_state_manager):
        """get_session_memories 获取指定会话记忆"""
        session_id = "session_test_005"

        temp_state_manager.capture_session_metadata(
            session_id=session_id,
            task_name="Task 1",
            files_changed=["file1.py"]
        )
        temp_state_manager.capture_session_metadata(
            session_id=session_id,
            task_name="Task 2",
            files_changed=["file2.py"]
        )
        temp_state_manager.capture_session_metadata(
            session_id="other_session",
            task_name="Task 3",
            files_changed=["file3.py"]
        )

        memories = temp_state_manager.get_session_memories(session_id)

        assert len(memories) == 2
        assert all(m["session_id"] == session_id for m in memories)

    def test_get_memory_stats(self, temp_state_manager):
        """get_memory_stats 返回统计"""
        temp_state_manager.capture_session_metadata(
            session_id="session_test_006",
            task_name="Task 1",
            files_changed=["file1.py", "file2.py"]
        )

        stats = temp_state_manager.get_memory_stats()

        assert stats["total_memories"] == 1
        assert stats["sessions"] >= 1

    def test_auto_capture_with_no_session(self, temp_state_manager):
        """auto_capture_on_task_complete 无会话时返回 None"""
        result = temp_state_manager.auto_capture_on_task_complete(
            task_name="Test task"
        )

        assert result is None

    def test_auto_capture_with_current_session(self, temp_state_manager):
        """auto_capture_on_task_complete 有会话时正常工作"""
        # 设置当前会话
        temp_state_manager.start_session("Test task")
        session_id = temp_state_manager.get_current_session()

        result = temp_state_manager.auto_capture_on_task_complete(
            task_name="Complete task",
            files_changed=["completed.py"],
            commit_message="feat: complete task"
        )

        assert result is not None
        assert result.startswith("mem_")

        # 验证记忆存在
        memories = temp_state_manager.get_session_memories(session_id)
        assert len(memories) >= 1


class TestWorkflowIntegration:
    """工作流程集成测试"""

    @pytest.fixture
    def temp_workflow(self):
        """临时工作流环境"""
        with tempfile.TemporaryDirectory() as tmpdir:
            from memory.external_memory import create_external_memory_mode
            workflow = create_external_memory_mode(tmpdir)
            yield workflow

    def test_workflow_with_memory_capture(self, temp_workflow):
        """工作流完成后自动捕获记忆"""
        # 开始工作流
        session_id = temp_workflow.start_workflow(
            task_name="Test workflow task",
            context={"description": "Integration test"}
        )

        # 模拟任务完成
        temp_workflow.state_manager.auto_capture_on_task_complete(
            task_name="Test workflow task",
            files_changed=["test_file.py"],
            commit_message="test: integration test"
        )

        # 验证记忆已存储
        memories = temp_workflow.state_manager.get_session_memories(session_id)

        assert len(memories) >= 1
        assert any("test_file.py" in m.get("metadata", {}).get("files_changed", [])
                   for m in memories)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
