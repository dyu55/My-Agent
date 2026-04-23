"""Conversation memory management for context compression."""

from typing import Any


class ConversationMemory:
    """
    Manages conversation history for context.

    Implements a compression strategy to maintain context within token limits:
    - Keeps recent turns as-is
    - Compresses older turns into summary lines
    """

    def __init__(self, max_pairs: int = 4):
        """
        Initialize conversation memory.

        Args:
            max_pairs: Maximum number of recent conversation pairs to keep
        """
        self.max_pairs = max_pairs
        self.recent_turns: list[dict[str, str]] = []
        self.summary_lines: list[str] = []

    def add(self, role: str, content: str) -> None:
        """
        Add a conversation turn.

        Args:
            role: Role name (e.g., "user", "assistant")
            content: Message content
        """
        self.recent_turns.append({"role": role, "content": content})
        self._compress()

    def _compress(self) -> None:
        """Compress conversation history when it exceeds max size."""
        max_turns = self.max_pairs * 2
        while len(self.recent_turns) > max_turns:
            oldest = self.recent_turns.pop(0)
            # Create compact summary of the turn
            compact = oldest["content"].replace("\n", " ").strip()[:180]
            self.summary_lines.append(f"- {oldest['role']}: {compact}")
            # Keep summary lines limited
            self.summary_lines = self.summary_lines[-12:]

    def build_messages(
        self,
        system_prompt: str,
        task: str | None = None
    ) -> list[dict[str, str]]:
        """
        Build messages for LLM with compression applied.

        Args:
            system_prompt: System prompt to include
            task: Optional task description to prepend

        Returns:
            List of message dictionaries for the LLM
        """
        messages = [{"role": "system", "content": system_prompt}]

        # Add compressed summary if available
        if self.summary_lines:
            messages.append({
                "role": "system",
                "content": "Summary:\n" + "\n".join(self.summary_lines)
            })

        # Add task if provided
        if task:
            messages.append({"role": "user", "content": task})

        # Add recent conversation turns
        messages.extend(self.recent_turns)
        return messages

    def clear(self) -> None:
        """Clear all conversation history."""
        self.recent_turns.clear()
        self.summary_lines.clear()

    def get_context_length(self) -> int:
        """Get approximate context length (number of messages)."""
        return len(self.recent_turns) + len(self.summary_lines) + 2  # +2 for system prompts
