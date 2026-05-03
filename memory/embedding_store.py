"""Embedding Store - Layer 3 Vector Database Implementation

Layer 3 实现了以下功能:
- ChromaDB 向量数据库集成
- 真实 Ollama embeddings (nomic-embed-text)
- 内存清理和过期策略
- 语义相似度搜索
"""

import json
import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import ollama
import chromadb
from chromadb.config import Settings


@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: list[str] = field(default_factory=list)
    session_id: str | None = None
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "created_at": self.created_at,
            "tags": self.tags,
            "session_id": self.session_id,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count
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
            session_id=data.get("session_id"),
            last_accessed=data.get("last_accessed", datetime.now().isoformat()),
            access_count=data.get("access_count", 0)
        )


class OllamaEmbeddings:
    """Ollama embedding 生成器"""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str | None = None
    ):
        self.model = model
        # Default to localhost, fallback to env var
        self.base_url = base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.client = ollama.Client(host=self.base_url)
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        """检查 Ollama embeddings 是否可用"""
        try:
            self.client.embeddings(model=self.model, prompt="test")
            return True
        except Exception:
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    def embed(self, text: str) -> list[float]:
        """生成文本的嵌入向量"""
        if not self._available:
            raise RuntimeError("Ollama embeddings not available")
        response = self.client.embeddings(model=self.model, prompt=text)
        return response["embedding"]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成嵌入向量"""
        if not self._available:
            raise RuntimeError("Ollama embeddings not available")
        return [self.embed(text) for text in texts]


class ChromaVectorStore:
    """ChromaDB 向量存储"""

    COLLECTION_NAME = "memory_embeddings"
    EMBEDDING_DIM = 768  # nomic-embed-text 默认维度

    def __init__(self, persist_dir: str = "memory/chroma_db"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        self.collection = self.client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )

    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None
    ) -> None:
        """添加向量到存储"""
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas or [{"index": i} for i in range(len(ids))]
        )

    def search(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
        where_document: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """搜索相似向量"""
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document
        )

    def delete(self, ids: list[str]) -> None:
        """删除向量"""
        self.collection.delete(ids=ids)

    def count(self) -> int:
        """获取向量数量"""
        return self.collection.count()

    def get_by_id(self, ids: str | list[str]) -> dict[str, Any]:
        """根据 ID 获取向量"""
        return self.collection.get(ids=ids)


class MemoryCleanupPolicy:
    """内存清理策略"""

    def __init__(
        self,
        max_age_days: int = 30,
        min_access_count: int = 2,
        max_memories: int = 10000
    ):
        self.max_age_days = max_age_days
        self.min_access_count = min_access_count
        self.max_memories = max_memories

    def should_cleanup(self, entry: MemoryEntry) -> tuple[bool, str]:
        """
        判断记忆是否应该被清理

        Returns:
            (should_cleanup, reason)
        """
        now = datetime.now()
        created = datetime.fromisoformat(entry.created_at)
        last_access = datetime.fromisoformat(entry.last_accessed)

        # 策略 1: 超过最大天数且访问次数少
        age_days = (now - created).days
        if age_days > self.max_age_days and entry.access_count < self.min_access_count:
            return True, f"过期且很少访问 (创建 {age_days} 天前)"

        # 策略 2: 长期未访问
        inactive_days = (now - last_access).days
        if inactive_days > self.max_age_days * 2:
            return True, f"长期不活跃 ({inactive_days} 天未访问)"

        # 策略 3: 标记为低优先级的旧记忆
        if age_days > self.max_age_days * 3:
            return True, f"超过最大保留期 ({age_days} 天)"

        return False, ""

    def get_retention_priority(self, entry: MemoryEntry) -> int:
        """
        获取记忆保留优先级 (数字越大优先级越高)

        基于:
        - 访问次数 (越多越高)
        - 最近访问时间 (越近越高)
        - 创建时间 (越新越高)
        - 元数据重要性 (标记为核心决策的记忆优先)
        """
        now = datetime.now()
        last_access = datetime.fromisoformat(entry.last_accessed)
        created = datetime.fromisoformat(entry.created_at)

        priority = 0

        # 访问次数贡献 (最多 +30)
        priority += min(entry.access_count * 3, 30)

        # 最近访问贡献 (最多 +30)
        days_since_access = (now - last_access).days
        priority += max(0, 30 - days_since_access * 2)

        # 创建时间贡献 (最多 +20)
        days_since_created = (now - created).days
        priority += max(0, 20 - days_since_created)

        # 重要性标记
        if entry.metadata.get("is_critical", False):
            priority += 50
        if entry.metadata.get("is_decision", False):
            priority += 30

        return priority


class EmbeddingStore:
    """
    嵌入存储 Layer 3 实现

    功能:
    - ChromaDB 向量数据库存储
    - Ollama 真实 embeddings
    - 智能清理策略
    - 语义相似度搜索

    回退机制:
    - Ollama 不可用时使用 mock embeddings
    - ChromaDB 不可用时使用 JSON 文件存储
    """

    def __init__(
        self,
        store_dir: str = "memory/sessions",
        chroma_dir: str = "memory/chroma_db"
    ):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

        self.index_file = self.store_dir / "embeddings_index.json"
        self._init_index()

        # 初始化 Ollama embeddings
        self.ollama_embeddings = OllamaEmbeddings()

        # 初始化 ChromaDB
        self.chroma = ChromaVectorStore(persist_dir=chroma_dir)

        # 初始化清理策略
        self.cleanup_policy = MemoryCleanupPolicy()

        # 同步状态
        self._sync_to_chroma()

    def _init_index(self) -> None:
        """初始化索引文件"""
        if not self.index_file.exists():
            self._save_index({
                "version": "3.0",
                "entries": [],
                "updated_at": ""
            })

    def _load_index(self) -> dict[str, Any]:
        """加载索引"""
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"version": "3.0", "entries": [], "updated_at": ""}

    def _save_index(self, data: dict[str, Any]) -> None:
        """保存索引"""
        data["updated_at"] = datetime.now().isoformat()
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _generate_mock_embedding(self, content: str) -> list[float]:
        """生成模拟嵌入向量 (回退方案)"""
        hash_bytes = hashlib.sha256(content.encode()).digest()
        embedding = []
        for i in range(768):
            byte_val = hash_bytes[i % len(hash_bytes)]
            embedding.append((byte_val / 128.0) - 1.0)
        return embedding

    def _sync_to_chroma(self) -> None:
        """同步索引到 ChromaDB"""
        if self.chroma.count() == 0:
            index_data = self._load_index()
            if index_data.get("entries"):
                entries = index_data["entries"]
                ids = [e["id"] for e in entries]
                embeddings = []
                documents = []
                metadatas = []

                for e in entries:
                    if e.get("embedding"):
                        emb = e["embedding"]
                    elif self.ollama_embeddings.is_available:
                        try:
                            emb = self.ollama_embeddings.embed(e["content"])
                        except Exception:
                            emb = self._generate_mock_embedding(e["content"])
                    else:
                        emb = self._generate_mock_embedding(e["content"])

                    embeddings.append(emb)
                    documents.append(e["content"])
                    metadatas.append({
                        "tags": json.dumps(e.get("tags", [])),
                        "session_id": e.get("session_id", ""),
                        "created_at": e.get("created_at", ""),
                        "access_count": e.get("access_count", 0)
                    })

                # 添加到 ChromaDB
                try:
                    # ChromaDB requires simple metadata values
                    chroma_meta = {
                        "tags": ",".join(e.get("tags", [])) if e.get("tags") else "",
                        "session_id": e.get("session_id", "") or "",
                        "created_at": e.get("created_at", "") or "",
                        "access_count": int(e.get("access_count", 0))
                    }
                    self.chroma.add(
                        ids=[e["id"]],
                        embeddings=[emb],
                        documents=[e["content"]],
                        metadatas=[chroma_meta]
                    )
                except Exception as sync_err:
                    print(f"Warning: Failed to sync entry {e['id']} to ChromaDB: {sync_err}")

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _text_match_score(self, query: str, content: str) -> float:
        """文本关键词匹配分数"""
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
        session_id: str | None = None,
        priority: str = "normal"  # "normal", "high", "critical"
    ) -> str:
        """
        存储新记忆 (Layer 3)

        Args:
            content: 记忆内容
            metadata: 元数据 (files, task_name, etc.)
            tags: 标签列表
            session_id: 关联的会话 ID
            priority: 优先级 ("normal", "high", "critical")

        Returns:
            记忆 ID
        """
        index_data = self._load_index()

        # 生成记忆 ID
        memory_id = f"mem_{len(index_data['entries']) + 1:05d}"

        # 生成嵌入向量
        if self.ollama_embeddings.is_available:
            try:
                embedding = self.ollama_embeddings.embed(content)
            except Exception:
                embedding = self._generate_mock_embedding(content)
        else:
            embedding = self._generate_mock_embedding(content)

        # 设置优先级元数据
        meta = metadata or {}
        if priority == "critical":
            meta["is_critical"] = True
        elif priority == "high":
            meta["is_decision"] = True

        # 创建记忆条目
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            metadata=meta,
            embedding=embedding,
            tags=tags or [],
            session_id=session_id
        )

        # 保存到索引
        index_data["entries"].append(entry.to_dict())
        self._save_index(index_data)

        # 添加到 ChromaDB
        self.chroma.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                "tags": json.dumps(tags or []),
                "session_id": session_id or "",
                "created_at": entry.created_at,
                "access_count": 0
            }]
        )

        return memory_id

    def recall(
        self,
        query: str,
        limit: int = 5,
        tags: list[str] | None = None,
        session_id: str | None = None,
        use_semantic: bool = True
    ) -> list[dict[str, Any]]:
        """
        检索记忆 (Layer 3 - 语义搜索)

        Args:
            query: 查询文本
            limit: 返回数量限制
            tags: 可选，按标签过滤
            session_id: 可选，按会话过滤
            use_semantic: 是否使用语义搜索

        Returns:
            匹配的記憶列表（按相关性排序）
        """
        index_data = self._load_index()
        results = []

        # 生成查询嵌入
        if self.ollama_embeddings.is_available and use_semantic:
            try:
                query_embedding = self.ollama_embeddings.embed(query)
            except Exception:
                query_embedding = self._generate_mock_embedding(query)
        else:
            query_embedding = self._generate_mock_embedding(query)

        # ChromaDB 语义搜索
        if use_semantic and self.ollama_embeddings.is_available:
            try:
                chroma_results = self.chroma.search(
                    query_embedding=query_embedding,
                    n_results=limit * 2  # 多取一些以便过滤
                )

                # 处理 ChromaDB 结果
                if chroma_results and chroma_results.get("ids"):
                    chroma_ids = chroma_results["ids"][0]
                    chroma_distances = chroma_results.get("distances", [[]])[0]

                    # 构建 ID 到距离的映射
                    id_to_distance = dict(zip(chroma_ids, chroma_distances))

                    # 从索引中获取完整信息
                    id_to_entry = {e["id"]: e for e in index_data.get("entries", [])}

                    for chroma_id in chroma_ids:
                        if chroma_id in id_to_entry:
                            entry = id_to_entry[chroma_id]

                            # 过滤器
                            if tags and not any(tag in entry.get("tags", []) for tag in tags):
                                continue
                            if session_id and entry.get("session_id") != session_id:
                                continue

                            # 计算相似度 (ChromaDB 返回的是余弦距离)
                            # 距离 0 = 完全相似, 距离 2 = 完全不相似
                            distance = id_to_distance.get(chroma_id, 1.0)
                            similarity = 1.0 - (distance / 2.0)  # 转换为相似度

                            results.append({
                                "id": entry["id"],
                                "content": entry["content"],
                                "metadata": entry.get("metadata", {}),
                                "tags": entry.get("tags", []),
                                "similarity": round(similarity, 4),
                                "created_at": entry.get("created_at", ""),
                                "session_id": entry.get("session_id"),
                                "search_method": "semantic"
                            })
            except Exception:
                # ChromaDB 失败，回退到传统方式
                use_semantic = False

        # 传统方式 (结合嵌入相似度和文本匹配)
        if not use_semantic or not results:
            for entry_data in index_data.get("entries", []):
                entry = MemoryEntry.from_dict(entry_data)

                # 过滤器
                if tags and not any(tag in entry.tags for tag in tags):
                    continue
                if session_id and entry.session_id != session_id:
                    continue

                # 计算相似度
                if entry.embedding:
                    embedding_similarity = self._cosine_similarity(query_embedding, entry.embedding)
                else:
                    embedding_similarity = 0.0

                text_similarity = self._text_match_score(query, entry.content)

                # 综合分数
                if text_similarity > 0:
                    similarity = text_similarity * 0.7 + embedding_similarity * 0.3
                else:
                    similarity = embedding_similarity

                if similarity > 0.1:
                    results.append({
                        "id": entry.id,
                        "content": entry.content,
                        "metadata": entry.metadata,
                        "tags": entry.tags,
                        "similarity": round(similarity, 4),
                        "created_at": entry.created_at,
                        "session_id": entry.session_id,
                        "search_method": "hybrid"
                    })

        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)

        # 更新访问记录
        for result in results[:limit]:
            self._update_access(result["id"])

        return results[:limit]

    def _update_access(self, memory_id: str) -> None:
        """更新记忆访问记录"""
        index_data = self._load_index()

        for entry in index_data.get("entries", []):
            if entry["id"] == memory_id:
                entry["last_accessed"] = datetime.now().isoformat()
                entry["access_count"] = entry.get("access_count", 0) + 1
                break

        self._save_index(index_data)

    def forget(self, memory_id: str) -> bool:
        """
        删除特定记忆

        Args:
            memory_id: 记忆 ID

        Returns:
            True if deleted
        """
        index_data = self._load_index()

        # 从索引删除
        original_len = len(index_data["entries"])
        index_data["entries"] = [
            e for e in index_data["entries"]
            if e["id"] != memory_id
        ]

        if len(index_data["entries"]) == original_len:
            return False

        self._save_index(index_data)

        # 从 ChromaDB 删除
        try:
            self.chroma.delete([memory_id])
        except Exception:
            pass

        return True

    def cleanup(self, dry_run: bool = False) -> dict[str, Any]:
        """
        清理过期记忆

        Args:
            dry_run: True 则只返回统计，不实际删除

        Returns:
            清理结果统计
        """
        index_data = self._load_index()
        to_delete = []
        stats = {
            "total": len(index_data["entries"]),
            "to_delete": 0,
            "reasons": {}
        }

        for entry_data in index_data["entries"]:
            entry = MemoryEntry.from_dict(entry_data)
            should_cleanup, reason = self.cleanup_policy.should_cleanup(entry)

            if should_cleanup:
                to_delete.append(entry.id)
                stats["reasons"][entry.id] = reason

        stats["to_delete"] = len(to_delete)

        if not dry_run and to_delete:
            # 删除记忆
            for memory_id in to_delete:
                self.forget(memory_id)

            stats["deleted"] = len(to_delete)

        return stats

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
        total_access = 0
        oldest = None
        newest = None

        for e in entries:
            all_tags.update(e.get("tags", []))
            total_access += e.get("access_count", 0)

            created = e.get("created_at", "")
            if created:
                if oldest is None or created < oldest:
                    oldest = created
                if newest is None or created > newest:
                    newest = created

        return {
            "total_memories": len(entries),
            "total_tags": len(all_tags),
            "tags": list(all_tags),
            "sessions": len(set(e.get("session_id") for e in entries if e.get("session_id"))),
            "total_access_count": total_access,
            "oldest_memory": oldest,
            "newest_memory": newest,
            "last_updated": index_data.get("updated_at", ""),
            "chroma_count": self.chroma.count(),
            "ollama_available": self.ollama_embeddings.is_available
        }

    def rebuild_chroma(self) -> int:
        """重建 ChromaDB 索引"""
        # 清空现有 ChromaDB
        try:
            self.client.delete_collection(self.COLLECTION_NAME)
        except Exception:
            pass

        # 重新初始化
        self.chroma = ChromaVectorStore(persist_dir=str(self.persist_dir.parent / "chroma_db"))

        # 重新同步
        self._sync_to_chroma()

        return self.chroma.count()


def create_embedding_store(store_dir: str = "memory/sessions") -> EmbeddingStore:
    """工厂函数"""
    return EmbeddingStore(store_dir=store_dir)