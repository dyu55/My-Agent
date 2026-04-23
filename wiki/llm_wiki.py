"""LLM Wiki - Knowledge management system using LLM for summarization and Q&A.

Unlike RAG (Retrieval Augmented Generation), this wiki uses LLM to:
1. Generate summaries of conversations/events
2. Answer questions about stored knowledge using LLM
3. Manage wiki entries with semantic understanding

No vector embeddings or similarity search - pure LLM-based approach.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class WikiEntry:
    """A single wiki entry."""
    title: str
    content: str
    id: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    created_by: str = "user"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WikiEntry":
        return cls(
            id=data.get("id", ""),
            title=data.get("title", ""),
            content=data.get("content", ""),
            tags=data.get("tags", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            created_by=data.get("created_by", "user"),
        )


class WikiStore:
    """Simple file-based wiki storage."""

    def __init__(self, wiki_dir: str = "wiki"):
        self.wiki_dir = Path(wiki_dir)
        self.wiki_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.wiki_dir / "index.json"
        self._load_index()

    def _load_index(self) -> None:
        """Load wiki index."""
        if self.index_file.exists():
            with open(self.index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.entries = {
                    e["id"]: WikiEntry.from_dict(e)
                    for e in data.get("entries", [])
                }
        else:
            self.entries = {}

    def _save_index(self) -> None:
        """Save wiki index."""
        data = {
            "updated_at": datetime.now().isoformat(),
            "entries": [e.to_dict() for e in self.entries.values()],
        }
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_entry(self, entry: WikiEntry) -> str:
        """Add a new wiki entry."""
        if not entry.id:
            entry.id = f"entry_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not entry.created_at:
            entry.created_at = datetime.now().isoformat()
        entry.updated_at = datetime.now().isoformat()

        self.entries[entry.id] = entry
        self._save_index()
        return entry.id

    def update_entry(self, entry_id: str, content: str = None, title: str = None, tags: list[str] = None) -> bool:
        """Update an existing entry."""
        if entry_id not in self.entries:
            return False

        entry = self.entries[entry_id]
        if content is not None:
            entry.content = content
        if title is not None:
            entry.title = title
        if tags is not None:
            entry.tags = tags
        entry.updated_at = datetime.now().isoformat()

        self._save_index()
        return True

    def get_entry(self, entry_id: str) -> WikiEntry | None:
        """Get an entry by ID."""
        return self.entries.get(entry_id)

    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry."""
        if entry_id in self.entries:
            del self.entries[entry_id]
            self._save_index()
            return True
        return False

    def search_by_tags(self, tags: list[str]) -> list[WikiEntry]:
        """Search entries by tags."""
        results = []
        for entry in self.entries.values():
            if any(tag in entry.tags for tag in tags):
                results.append(entry)
        return results

    def get_all_entries(self) -> list[WikiEntry]:
        """Get all entries."""
        return list(self.entries.values())

    def get_recent_entries(self, limit: int = 10) -> list[WikiEntry]:
        """Get most recent entries."""
        entries = sorted(
            self.entries.values(),
            key=lambda e: e.updated_at or e.created_at,
            reverse=True
        )
        return entries[:limit]


class LLMWiki:
    """
    LLM-powered wiki system.

    Uses LLM to:
    - Summarize conversations into wiki entries
    - Answer questions about stored knowledge
    - Generate tags and titles for entries
    """

    def __init__(self, wiki_dir: str = "wiki"):
        self.store = WikiStore(wiki_dir)

    def summarize_conversation(self, conversation_history: str, llm_client: Any = None) -> str:
        """
        Use LLM to summarize a conversation into a wiki entry.

        Args:
            conversation_history: Raw conversation text
            llm_client: Optional LLM client for better summarization

        Returns:
            Summary text suitable for wiki
        """
        if llm_client:
            prompt = f"""请将以下对话/操作历史总结成一个简洁的摘要，用于存储到知识库中。

要求：
1. 提取关键信息：完成了什么任务，有什么重要结论
2. 保留重要的技术细节：代码片段、配置、重要决策
3. 用中文简洁地表达
4. 摘要长度控制在200字以内

对话历史：
{conversation_history}

请直接输出摘要，不要额外解释："""
            try:
                return llm_client.chat(prompt)
            except Exception:
                pass

        # Fallback: simple regex-based extraction
        return self._simple_summarize(conversation_history)

    def _simple_summarize(self, text: str) -> str:
        """Simple summarization without LLM."""
        lines = text.strip().split("\n")

        # Extract key lines (lines with important keywords)
        important_keywords = ["创建", "修改", "完成", "修复", "添加", "删除", "更新", "成功", "失败", "错误"]
        key_lines = []

        for line in lines:
            if any(kw in line for kw in important_keywords):
                key_lines.append(line.strip())

        if key_lines:
            return " | ".join(key_lines[:5])
        return text[:200] if len(text) > 200 else text

    def answer_question(self, question: str, context_entries: list[WikiEntry], llm_client: Any = None) -> str:
        """
        Use LLM to answer a question based on wiki entries.

        Args:
            question: User's question
            context_entries: Wiki entries to use as context
            llm_client: Optional LLM client

        Returns:
            Answer based on wiki knowledge
        """
        if not context_entries:
            return "知识库中没有相关信息。"

        # Build context from entries
        context_text = "\n\n".join([
            f"## {e.title}\n{e.content}"
            for e in context_entries
        ])

        if llm_client:
            prompt = f"""基于以下知识库内容，回答用户的问题。

知识库内容：
{context_text}

用户问题：{question}

请用中文回答，如果知识库中没有相关信息，请明确说明。"""
            try:
                return llm_client.chat(prompt)
            except Exception:
                pass

        # Fallback: simple keyword matching
        return self._simple_answer(question, context_entries)

    def _simple_answer(self, question: str, entries: list[WikiEntry]) -> str:
        """Simple answer without LLM - keyword matching."""
        question_keywords = re.findall(r"[\w]+", question.lower())

        # Score entries by keyword matches
        scored = []
        for entry in entries:
            score = 0
            text = (entry.title + " " + entry.content).lower()
            for kw in question_keywords:
                if len(kw) > 2 and kw in text:
                    score += 1
            if score > 0:
                scored.append((score, entry))

        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            best = scored[0][1]
            return f"根据\"{best.title}\"的内容：\n\n{best.content[:300]}..."

        return "没有找到相关信息。"

    def generate_tags(self, content: str, llm_client: Any = None) -> list[str]:
        """
        Use LLM to generate tags for content.

        Args:
            content: Content to tag
            llm_client: Optional LLM client

        Returns:
            List of relevant tags
        """
        if llm_client:
            prompt = f"""请为以下内容生成3-5个标签。

要求：
1. 使用英文标签
2. 标签要简洁、通用
3. 反映内容的主要主题

内容：
{content[:500]}

请直接输出标签，用逗号分隔："""
            try:
                result = llm_client.chat(prompt)
                tags = [t.strip() for t in result.split(",")]
                return [t for t in tags if t][:5]
            except Exception:
                pass

        # Fallback: simple keyword extraction
        return self._simple_tags(content)

    def _simple_tags(self, content: str) -> list[str]:
        """Simple tag generation without LLM."""
        common_tags = {
            "python", "javascript", "typescript", "react", "vue", "node",
            "api", "database", "config", "test", "bug", "feature",
            "refactor", "optimize", "deploy", "docker", "git",
            "frontend", "backend", "fullstack", "mobile", "web",
            "llm", "ai", "agent", "openai", "ollama",
        }

        content_lower = content.lower()
        found = [t for t in common_tags if t in content_lower]
        return found[:5] if found else ["general"]

    def create_entry_from_task(self, task_description: str, result: str, llm_client: Any = None) -> str:
        """Create a wiki entry from a completed task."""
        # Generate title
        if llm_client:
            title_prompt = f"""根据以下任务描述，生成一个简短的项目名称/标题（中文，10字以内）。

任务：{task_description}

直接输出标题："""
            try:
                title = llm_client.chat(title_prompt).strip()[:20]
            except Exception:
                title = task_description[:20]
        else:
            title = task_description[:20]

        # Summarize result
        content = f"任务：{task_description}\n\n结果：{result}"

        # Generate tags
        tags = self.generate_tags(task_description + " " + result, llm_client)

        entry = WikiEntry(
            title=title,
            content=content,
            tags=tags,
            created_by="agent",
        )

        return self.store.add_entry(entry)
