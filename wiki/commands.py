"""Wiki CLI commands for the agent."""

import shlex
from typing import Any

from utils.persistent_memory import PersistentMemory, SessionMemory


class WikiCommands:
    """Commands for memory and wiki management."""

    def __init__(self, llm_client: Any = None):
        self.llm_client = llm_client
        self.persistent_memory = PersistentMemory()
        self.session_memory = SessionMemory()

    def handle_remember(self, args: str) -> str:
        """
        Handle remember command: remember <key> <value>
        Stores important information persistently.
        """
        try:
            parts = shlex.split(args) if args else []
        except ValueError:
            return "Error: Invalid argument format"

        if len(parts) < 2:
            return "Usage: remember <key> <value>"

        key = parts[0]
        value = " ".join(parts[1:])
        return self.persistent_memory.remember(key, value)

    def handle_recall(self, args: str) -> str:
        """
        Handle recall command: recall [key|query]
        Retrieves information from memory.
        """
        query = args.strip() if args else None
        return self.persistent_memory.recall(key=None, query=query)

    def handle_forget(self, args: str) -> str:
        """
        Handle forget command: forget <key|pattern>
        Deletes information from memory.
        """
        key_or_pattern = args.strip() if args else None
        if not key_or_pattern:
            return "Usage: forget <key|pattern>"

        if "*" in key_or_pattern or "?" in key_or_pattern:
            return self.persistent_memory.forget(pattern=key_or_pattern)
        return self.persistent_memory.forget(key=key_or_pattern)

    def handle_memories(self, args: str) -> str:
        """List all persistent memories."""
        return self.persistent_memory.recall()

    def handle_wiki_search(self, args: str) -> str:
        """
        Search wiki entries: wiki search <query>
        """
        if not args.strip():
            return "Usage: wiki search <query>"

        entries = self.persistent_memory.wiki.store.get_recent_entries(limit=10)
        query = args.strip()

        # Simple search
        results = []
        for entry in entries:
            if query.lower() in entry.title.lower() or query.lower() in entry.content.lower():
                results.append(entry)

        if not results:
            return f"No wiki entries found matching '{query}'"

        lines = [f"找到 {len(results)} 条相关记录："]
        for entry in results:
            lines.append(f"\n## {entry.title}")
            lines.append(f"标签: {', '.join(entry.tags)}")
            lines.append(f"内容: {entry.content[:200]}...")
            lines.append(f"更新于: {entry.updated_at}")

        return "\n".join(lines)

    def handle_wiki_list(self, args: str) -> str:
        """List all wiki entries."""
        entries = self.persistent_memory.wiki.store.get_all_entries()

        if not entries:
            return "Wiki 是空的。"

        lines = ["Wiki 条目："]
        for entry in entries:
            lines.append(f"\n- {entry.title} [{', '.join(entry.tags)}]")
            lines.append(f"  {entry.content[:100]}...")

        return "\n".join(lines)

    def handle_wiki_add(self, args: str) -> str:
        """
        Add a wiki entry: wiki add <title> <content>
        """
        try:
            parts = shlex.split(args) if args else []
        except ValueError:
            return "Error: Invalid argument format"

        if len(parts) < 2:
            return "Usage: wiki add <title> <content>"

        title = parts[0]
        content = " ".join(parts[1:])

        from wiki.llm_wiki import WikiEntry
        entry = WikiEntry(title=title, content=content)
        entry_id = self.persistent_memory.wiki.store.add_entry(entry)

        return f"✓ Wiki 条目已创建: {entry_id}"

    def handle_session_summary(self, args: str) -> str:
        """Create a summary of the current session."""
        log = self.session_memory.get_session_log()
        entry_id = self.persistent_memory.summarize_session(log, self.llm_client)
        return f"✓ Session 已保存到 Wiki: {entry_id}"

    def handle_context(self, args: str) -> str:
        """Show current context including memories."""
        return self.persistent_memory.get_context()

    def log_task(self, task: str, status: str, result: str) -> None:
        """Log a task for later session summary."""
        self.session_memory.log_task_result(task, status, result)

    def log_event(self, event_type: str, description: str, data: Any = None) -> None:
        """Log an event."""
        self.session_memory.log_event(event_type, description, data)

    def get_commands(self) -> dict[str, callable]:
        """Get all available wiki commands."""
        return {
            "remember": self.handle_remember,
            "recall": self.handle_recall,
            "forget": self.handle_forget,
            "memories": self.handle_memories,
            "wiki": self.handle_wiki_search,
            "wiki_list": self.handle_wiki_list,
            "wiki_add": self.handle_wiki_add,
            "session_summary": self.handle_session_summary,
            "context": self.handle_context,
        }