"""Persistent Memory - Cross-session memory management.

Provides persistent storage of agent memories across sessions using wiki.
Features:
- remember: Save important information to persistent storage
- forget: Remove information from memory
- recall: Retrieve information from memory
- summarize session: Create a wiki entry from completed tasks
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from utils.conversation import ConversationMemory
from wiki.llm_wiki import LLMWiki, WikiEntry


class PersistentMemory:
    """
    Persistent memory system that survives across sessions.

    Uses file-based storage to persist memories between agent runs.
    """

    def __init__(self, memory_dir: str = "memory", wiki_dir: str = "wiki"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.persist_file = self.memory_dir / "memories.json"
        self.session_file = self.memory_dir / "sessions.json"

        self.conversation_memory = ConversationMemory()
        self.wiki = LLMWiki(wiki_dir)

        self._load_memories()

    def _load_memories(self) -> None:
        """Load memories from file."""
        if self.persist_file.exists():
            with open(self.persist_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.persistent_memories = data.get("memories", {})
        else:
            self.persistent_memories = {}

    def _save_memories(self) -> None:
        """Save memories to file."""
        data = {
            "updated_at": datetime.now().isoformat(),
            "memories": self.persistent_memories,
        }
        with open(self.persist_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def remember(self, key: str, value: str, overwrite: bool = True) -> str:
        """
        Remember (save) information to persistent storage.

        Args:
            key: Memory key/identifier
            value: Information to remember
            overwrite: Whether to overwrite existing memory

        Returns:
            Status message
        """
        if key in self.persistent_memories and not overwrite:
            return f"Memory '{key}' already exists. Use overwrite=True to replace."

        self.persistent_memories[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat(),
        }
        self._save_memories()
        return f"✓ Remembered: {key}"

    def recall(self, key: str = None, query: str = None) -> str:
        """
        Recall (retrieve) information from memory.

        Args:
            key: Specific memory key to retrieve
            query: Optional query to search memories (simple keyword match)

        Returns:
            Retrieved memory or search results
        """
        if key:
            if key in self.persistent_memories:
                memory = self.persistent_memories[key]
                return f"[{memory['timestamp']}] {memory['value']}"
            return f"No memory found for key: '{key}'"

        if query:
            results = []
            for k, v in self.persistent_memories.items():
                if query.lower() in k.lower() or query.lower() in v["value"].lower():
                    results.append(f"- {k}: {v['value'][:100]}")
            if results:
                return "匹配的记忆：\n" + "\n".join(results)
            return f"No memories matching '{query}'"

        # List all memories
        if not self.persistent_memories:
            return "记忆库为空。"

        lines = ["已存储的记忆："]
        for k, v in sorted(self.persistent_memories.items()):
            lines.append(f"- {k}: {v['value'][:80]}...")
        return "\n".join(lines)

    def forget(self, key: str = None, pattern: str = None) -> str:
        """
        Forget (delete) information from memory.

        Args:
            key: Specific memory key to delete
            pattern: Pattern to match for deletion (e.g., "temp_*")

        Returns:
            Status message
        """
        if key:
            if key in self.persistent_memories:
                del self.persistent_memories[key]
                self._save_memories()
                return f"✓ Forgotten: {key}"
            return f"No memory found for key: '{key}'"

        if pattern:
            to_delete = [k for k in self.persistent_memories.keys() if self._match_pattern(k, pattern)]
            if not to_delete:
                return f"No memories matching pattern: '{pattern}'"

            for k in to_delete:
                del self.persistent_memories[k]
            self._save_memories()
            return f"✓ Forgotten {len(to_delete)} memories matching '{pattern}'"

        return "Please specify key or pattern to forget."

    def _match_pattern(self, text: str, pattern: str) -> bool:
        """Simple glob-like pattern matching."""
        import fnmatch
        return fnmatch.fnmatch(text, pattern)

    def summarize_session(self, session_log: str, llm_client: Any = None) -> str:
        """
        Summarize a completed session into a wiki entry.

        Args:
            session_log: Log of the session
            llm_client: Optional LLM client for better summarization

        Returns:
            Created wiki entry ID
        """
        return self.wiki.create_entry_from_task(
            task_description="Agent Session",
            result=session_log,
            llm_client=llm_client,
        )

    def get_context(self) -> str:
        """
        Get persistent context for the agent.

        Returns:
            Context string with memories and recent session info
        """
        context_parts = []

        # Add persistent memories if any
        if self.persistent_memories:
            mem_lines = ["[持久记忆]"]
            for k, v in self.persistent_memories.items():
                mem_lines.append(f"- {k}: {v['value'][:100]}")
            context_parts.append("\n".join(mem_lines))

        # Add conversation memory summary
        if self.conversation_memory.recent_turns:
            context_parts.append(
                f"[最近对话] ({len(self.conversation_memory.recent_turns)} 条)"
            )

        return "\n\n".join(context_parts) if context_parts else ""

    def clear_all(self) -> str:
        """Clear all persistent memories."""
        count = len(self.persistent_memories)
        self.persistent_memories = {}
        self._save_memories()
        self.conversation_memory.clear()
        return f"✓ Cleared {count} memories"


class SessionMemory:
    """In-session memory with logging for later summarization."""

    def __init__(self):
        self.events: list[dict[str, Any]] = []
        self.task_results: list[dict[str, Any]] = []
        self.start_time = datetime.now()

    def log_event(self, event_type: str, description: str, data: Any = None) -> None:
        """Log an event during the session."""
        self.events.append({
            "type": event_type,
            "description": description,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        })

    def log_task_result(self, task: str, status: str, result: str) -> None:
        """Log a completed task result."""
        self.task_results.append({
            "task": task,
            "status": status,
            "result": result[:500] if result else "",
            "timestamp": datetime.now().isoformat(),
        })

    def get_session_log(self) -> str:
        """Get a formatted log of the session."""
        lines = [
            f"=== Session Summary ({self.start_time.strftime('%Y-%m-%d %H:%M')}) ===",
            "",
            f"Tasks completed: {len(self.task_results)}",
            "",
        ]

        for i, task in enumerate(self.task_results, 1):
            lines.append(f"[{i}] {task['task']}")
            lines.append(f"    状态: {task['status']}")
            if task['result']:
                lines.append(f"    结果: {task['result'][:200]}")
            lines.append("")

        return "\n".join(lines)

    def get_recent_tasks(self, limit: int = 5) -> list[dict[str, Any]]:
        """Get recent task results."""
        return self.task_results[-limit:] if len(self.task_results) > limit else self.task_results