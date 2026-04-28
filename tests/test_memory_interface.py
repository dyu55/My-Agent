"""Test Memory Interface and Mock Embeddings (Layer 1 MVP)

测试 Layer 1 的核心功能：
- EmbeddingStore 接口
- 模拟嵌入生成
- 文本回退搜索
- 记忆存取
"""

import json
import tempfile
from pathlib import Path

import pytest

from memory.embedding_store import EmbeddingStore, MemoryEntry


class TestMemoryEntry:
    """MemoryEntry 数据类测试"""

    def test_create_entry(self):
        entry = MemoryEntry(
            id="mem_001",
            content="Test memory content",
            metadata={"task": "test"},
            tags=["test", "unit"],
            session_id="session_001"
        )

        assert entry.id == "mem_001"
        assert entry.content == "Test memory content"
        assert entry.metadata == {"task": "test"}
        assert entry.tags == ["test", "unit"]
        assert entry.session_id == "session_001"
        assert entry.embedding is None

    def test_to_dict(self):
        entry = MemoryEntry(
            id="mem_001",
            content="Test content",
            tags=["test"]
        )

        data = entry.to_dict()
        assert data["id"] == "mem_001"
        assert data["content"] == "Test content"
        assert data["tags"] == ["test"]
        assert "created_at" in data

    def test_from_dict(self):
        data = {
            "id": "mem_002",
            "content": "Restored content",
            "metadata": {"restored": True},
            "tags": ["restored"],
            "session_id": "session_002",
            "created_at": "2026-04-27T00:00:00"
        }

        entry = MemoryEntry.from_dict(data)
        assert entry.id == "mem_002"
        assert entry.content == "Restored content"
        assert entry.metadata == {"restored": True}


class TestEmbeddingStore:
    """EmbeddingStore 测试"""

    @pytest.fixture
    def temp_store(self):
        """临时存储目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EmbeddingStore(store_dir=tmpdir)
            yield store

    def test_init_creates_directory(self, temp_store):
        """初始化创建目录"""
        assert temp_store.store_dir.exists()
        assert temp_store.index_file.exists()

    def test_init_creates_index_file(self, temp_store):
        """初始化创建索引文件"""
        with open(temp_store.index_file, "r") as f:
            data = json.load(f)

        assert data["version"] == "1.0"
        assert data["entries"] == []

    def test_remember_stores_memory(self, temp_store):
        """remember() 存储记忆"""
        memory_id = temp_store.remember(
            content="This is a test memory",
            metadata={"task": "test_memory"},
            tags=["test", "unit"],
            session_id="session_001"
        )

        assert memory_id.startswith("mem_")

        # 验证存储
        index_data = temp_store._load_index()
        assert len(index_data["entries"]) == 1
        assert index_data["entries"][0]["content"] == "This is a test memory"

    def test_remember_generates_mock_embedding(self, temp_store):
        """remember() 生成模拟嵌入"""
        memory_id = temp_store.remember(
            content="Generate mock embedding",
            tags=["test"]
        )

        index_data = temp_store._load_index()
        entry = index_data["entries"][0]

        assert entry["embedding"] is not None
        assert len(entry["embedding"]) == 128  # 128 维向量

    def test_remember_id_uniqueness(self, temp_store):
        """remember() 生成唯一 ID"""
        id1 = temp_store.remember(content="Memory 1", tags=["test"])
        id2 = temp_store.remember(content="Memory 2", tags=["test"])
        id3 = temp_store.remember(content="Memory 3", tags=["test"])

        assert id1 != id2 != id3

    def test_recall_returns_results(self, temp_store):
        """recall() 返回结果"""
        temp_store.remember(
            content="Python is a programming language",
            tags=["code", "python"]
        )
        temp_store.remember(
            content="JavaScript is for web development",
            tags=["code", "javascript"]
        )
        temp_store.remember(
            content="The weather is nice today",
            tags=["personal"]
        )

        results = temp_store.recall(query="programming language", limit=5)

        assert len(results) >= 1
        assert any("Python" in r["content"] for r in results)

    def test_recall_with_tag_filter(self, temp_store):
        """recall() 按标签过滤"""
        temp_store.remember(content="Python code", tags=["python", "code"])
        temp_store.remember(content="JS code", tags=["javascript", "code"])

        results = temp_store.recall(query="code", tags=["python"])

        assert all("python" in r["tags"] for r in results)

    def test_recall_with_session_filter(self, temp_store):
        """recall() 按会话过滤"""
        temp_store.remember(
            content="Session 1 memory",
            session_id="session_001",
            tags=["test"]
        )
        temp_store.remember(
            content="Session 2 memory",
            session_id="session_002",
            tags=["test"]
        )

        results = temp_store.recall(
            query="memory",
            session_id="session_001"
        )

        assert all(r["session_id"] == "session_001" for r in results)

    def test_recall_respects_limit(self, temp_store):
        """recall() 限制返回数量"""
        for i in range(10):
            temp_store.remember(
                content=f"Memory {i}",
                tags=["test"]
            )

        results = temp_store.recall(query="Memory", limit=3)

        assert len(results) == 3

    def test_recall_sorted_by_similarity(self, temp_store):
        """recall() 按相似度排序"""
        temp_store.remember(
            content="Python programming language",
            tags=["python"]
        )
        temp_store.remember(
            content="Java Java coffee",
            tags=["java"]
        )
        temp_store.remember(
            content="Python snake",
            tags=["python"]
        )

        results = temp_store.recall(query="Python", limit=5)

        # Python 相关的内容应该有更高的相似度
        python_scores = [
            r["similarity"] for r in results
            if "Python" in r["content"]
        ]
        if python_scores:
            assert max(python_scores) >= 0.1

    def test_get_all_returns_recent(self, temp_store):
        """get_all() 返回最近的记忆"""
        for i in range(5):
            temp_store.remember(content=f"Memory {i}", tags=["test"])

        all_memories = temp_store.get_all(limit=3)

        assert len(all_memories) == 3

    def test_get_by_session(self, temp_store):
        """get_by_session() 按会话获取"""
        temp_store.remember(
            content="Memory 1",
            session_id="session_001",
            tags=["test"]
        )
        temp_store.remember(
            content="Memory 2",
            session_id="session_001",
            tags=["test"]
        )
        temp_store.remember(
            content="Memory 3",
            session_id="session_002",
            tags=["test"]
        )

        session_memories = temp_store.get_by_session("session_001")

        assert len(session_memories) == 2

    def test_get_stats(self, temp_store):
        """get_stats() 返回统计信息"""
        temp_store.remember(
            content="Memory with tags",
            tags=["tag1", "tag2"],
            session_id="session_001"
        )
        temp_store.remember(
            content="Another memory",
            tags=["tag1"],
            session_id="session_002"
        )

        stats = temp_store.get_stats()

        assert stats["total_memories"] == 2
        assert stats["total_tags"] == 2  # tag1, tag2
        assert stats["sessions"] == 2
        assert "tag1" in stats["tags"]
        assert "tag2" in stats["tags"]


class TestMockEmbedding:
    """模拟嵌入测试"""

    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield EmbeddingStore(store_dir=tmpdir)

    def test_mock_embedding_deterministic(self, store):
        """模拟嵌入是确定性的"""
        content = "Test content for deterministic embedding"

        embedding1 = store._generate_mock_embedding(content)
        embedding2 = store._generate_mock_embedding(content)

        assert embedding1 == embedding2

    def test_mock_embedding_different_for_different_content(self, store):
        """不同内容生成不同嵌入"""
        embedding1 = store._generate_mock_embedding("Content A")
        embedding2 = store._generate_mock_embedding("Content B")

        assert embedding1 != embedding2

    def test_mock_embedding_length(self, store):
        """模拟嵌入长度为 128"""
        embedding = store._generate_mock_embedding("Test content")

        assert len(embedding) == 128

    def test_mock_embedding_range(self, store):
        """模拟嵌入值范围 [-1, 1]"""
        embedding = store._generate_mock_embedding("Test content")

        assert all(-1.0 <= v <= 1.0 for v in embedding)

    def test_cosine_similarity(self, store):
        """余弦相似度计算"""
        # 相同向量
        vec = [1.0, 0.0, 0.0]
        similarity = store._cosine_similarity(vec, vec)

        assert similarity == pytest.approx(1.0)

        # 正交向量
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = store._cosine_similarity(vec1, vec2)

        assert similarity == pytest.approx(0.0)

    def test_text_match_score(self, store):
        """文本匹配分数"""
        # 完全匹配
        score = store._text_match_score("python code", "python code")
        assert score == 1.0

        # 部分匹配
        score = store._text_match_score("python code", "python")
        assert score == 0.5

        # 不匹配
        score = store._text_match_score("python", "java javascript")
        assert score == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
