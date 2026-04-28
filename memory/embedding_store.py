"""Embedding Store - 模拟嵌入存储 (Layer 1 MVP)

基于 Codex 审查反馈，Layer 1 采用战略捷径：
- 使用模拟嵌入（hash-based）用于 MVP
- 真实 Ollama embeddings 延后至 Layer 3
- 文本关键词搜索作为回退方案
"""

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None  # Layer 1: 模拟嵌入
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = field(default_factory=list)
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "created_at": self.created_at,
            "tags": self.tags,
            "session_id": self.session_id
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        return cls(
            id=data["id"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            tags=data.get("tags", []),
            session_id=data.get("session_id")
        )


class EmbeddingStore:
    """
    嵌入存储 (Layer 1 MVP)

    Layer 1 实现：
    - 模拟嵌入：基于内容 hash 生成伪向量
    - 追加存储：JSON 文件，无索引
    - 文本回退：关键词匹配作为搜索回退

    Layer 3 (延后):
    - 真实 Ollama embeddings 生成
    - ChromaDB 向量数据库
    - 语义相似度搜索
    """

    def __init__(self, store_dir: str = "memory/sessions"):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.store_dir / "embeddings_index.json"
        self._init_index()

    def _init_index(self) -> None:
        """初始化索引文件"""
        if not self.index_file.exists():
            self._save_index({"version": "1.0", "entries": [], "updated_at": ""})

    def _load_index(self) -> dict[str, Any]:
        """加载索引"""
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"version": "1.0", "entries": [], "updated_at": ""}

    def _save_index(self, data: dict[str, Any]) -> None:
        """保存索引"""
        data["updated_at"] = datetime.now().isoformat()
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _generate_mock_embedding(self, content: str) -> list[float]:
        """
        生成模拟嵌入向量 (Layer 1)

        使用 hash 生成伪向量，用于测试和 MVP
        Layer 3 将使用真实的 Ollama embeddings
        """
        # 使用 SHA256 hash 生成固定长度的字节
        hash_bytes = hashlib.sha256(content.encode()).digest()

        # 转换为 128 维向量（简化版本）
        embedding = []
        for i in range(128):
            # 从 hash 中提取值，范围 [-1, 1]
            byte_val = hash_bytes[i % len(hash_bytes)]
            embedding.append((byte_val / 128.0) - 1.0)

        return embedding

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _text_match_score(self, query: str, content: str) -> float:
        """
        文本关键词匹配分数

        作为嵌入搜索失败时的回退方案
        """
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())

        if not query_words:
            return 0.0

        matches = len(query_words & content_words)
        return matches / len(query_words)

    # ==================== 公共接口 ====================

    def remember(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
        session_id: str | None = None
    ) -> str:
        """
        存储新记忆

        Args:
            content: 记忆内容
            metadata: 元数据 (files, task_name, etc.)
            tags: 标签列表
            session_id: 关联的会话 ID

        Returns:
            记忆 ID
        """
        index_data = self._load_index()

        # 生成记忆 ID
        memory_id = f"mem_{len(index_data['entries']) + 1:05d}"

        # 生成模拟嵌入
        embedding = self._generate_mock_embedding(content)

        # 创建记忆条目
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            metadata=metadata or {},
            embedding=embedding,
            tags=tags or [],
            session_id=session_id
        )

        # 追加到索引
        index_data["entries"].append(entry.to_dict())
        self._save_index(index_data)

        return memory_id

    def recall(
        self,
        query: str,
        limit: int = 5,
        tags: list[str] | None = None,
        session_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        检索记忆

        Args:
            query: 查询文本
            limit: 返回数量限制
            tags: 可选，按标签过滤
            session_id: 可选，按会话过滤

        Returns:
            匹配的記憶列表（按相关性排序）
        """
        index_data = self._load_index()
        results = []

        # 生成查询嵌入
        query_embedding = self._generate_mock_embedding(query)

        for entry_data in index_data.get("entries", []):
            entry = MemoryEntry.from_dict(entry_data)

            # 过滤器
            if tags and not any(tag in entry.tags for tag in tags):
                continue
            if session_id and entry.session_id != session_id:
                continue

            # 计算相似度 - 结合嵌入相似度和文本匹配
            if entry.embedding:
                embedding_similarity = self._cosine_similarity(query_embedding, entry.embedding)
            else:
                embedding_similarity = 0.0

            text_similarity = self._text_match_score(query, entry.content)

            # 综合分数：优先文本匹配，其次嵌入相似度
            # 当文本匹配 > 0 时，文本匹配权重更高
            if text_similarity > 0:
                similarity = text_similarity * 0.7 + embedding_similarity * 0.3
            else:
                similarity = embedding_similarity

            if similarity > 0.1:  # 阈值
                results.append({
                    "id": entry.id,
                    "content": entry.content,
                    "metadata": entry.metadata,
                    "tags": entry.tags,
                    "similarity": round(similarity, 4),
                    "created_at": entry.created_at,
                    "session_id": entry.session_id
                })

        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:limit]

    def get_all(self, limit: int = 50) -> list[dict[str, Any]]:
        """获取所有记忆（按时间倒序）"""
        index_data = self._load_index()
        entries = index_data.get("entries", [])[-limit:]
        return [MemoryEntry.from_dict(e).to_dict() for e in entries]

    def get_by_session(self, session_id: str) -> list[dict[str, Any]]:
        """获取指定会话的所有记忆"""
        index_data = self._load_index()
        return [
            MemoryEntry.from_dict(e).to_dict()
            for e in index_data.get("entries", [])
            if e.get("session_id") == session_id
        ]

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        index_data = self._load_index()
        entries = index_data.get("entries", [])

        all_tags = set()
        for e in entries:
            all_tags.update(e.get("tags", []))

        return {
            "total_memories": len(entries),
            "total_tags": len(all_tags),
            "tags": list(all_tags),
            "sessions": len(set(e.get("session_id") for e in entries if e.get("session_id"))),
            "last_updated": index_data.get("updated_at", "")
        }


def create_embedding_store(store_dir: str = "memory/sessions") -> EmbeddingStore:
    """工厂函数"""
    return EmbeddingStore(store_dir=store_dir)