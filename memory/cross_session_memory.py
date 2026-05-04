"""Cross-session learning - stores and retrieves learned patterns across sessions.

This module implements persistent learning that survives across sessions:
1. Code patterns - common solutions found during development
2. Task patterns - successful task decompositions
3. Error patterns - bugs and their fixes
4. Best practices - coding conventions learned over time

Based on the external memory architecture from external_memory.py
"""

import json
import re
from dataclasses import dataclass, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class LearnedPattern:
    """
    A learned pattern from previous sessions.

    Patterns are automatically extracted from successful task completions
    and can be recalled when similar tasks arise.
    """

    id: str
    name: str
    pattern_type: str  # "code", "task", "error", "best_practice"
    content: str  # The pattern content (code, task structure, etc.)
    description: str  # Human-readable description
    tags: list[str] = field(default_factory=list)
    success_count: int = 0  # How many times this pattern helped
    failure_count: int = 0  # How many times this pattern failed
    first_learned: str = ""  # ISO timestamp
    last_used: str = ""  # ISO timestamp
    last_successful: str = ""  # ISO timestamp
    source_session: str = ""  # Where this was learned
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def confidence(self) -> float:
        """Calculate confidence score based on success rate."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5  # Neutral
        return self.success_count / total

    @property
    def is_stale(self) -> bool:
        """Check if pattern is stale (not used in 30 days)."""
        if not self.last_used:
            # Never used - check if learned recently
            if not self.first_learned:
                return True
            learned_date = datetime.fromisoformat(self.first_learned)
            return (datetime.now() - learned_date).days > 30

        last_used_date = datetime.fromisoformat(self.last_used)
        return (datetime.now() - last_used_date).days > 30

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "pattern_type": self.pattern_type,
            "content": self.content,
            "description": self.description,
            "tags": self.tags,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "first_learned": self.first_learned,
            "last_used": self.last_used,
            "last_successful": self.last_successful,
            "source_session": self.source_session,
            "metadata": self.metadata,
            "confidence": self.confidence,
            "is_stale": self.is_stale,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearnedPattern":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            pattern_type=data["pattern_type"],
            content=data["content"],
            description=data.get("description", ""),
            tags=data.get("tags", []),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            first_learned=data.get("first_learned", ""),
            last_used=data.get("last_used", ""),
            last_successful=data.get("last_successful", ""),
            source_session=data.get("source_session", ""),
            metadata=data.get("metadata", {}),
        )


class CrossSessionMemory:
    """
    Cross-session persistent learning system.

    Features:
    - Stores learned patterns in JSON
    - Tracks success/failure rates
    - Extracts patterns from session logs
    - Provides similarity-based retrieval
    - Auto-cleanup of stale patterns
    """

    # Pattern type constants
    TYPE_CODE = "code"
    TYPE_TASK = "task"
    TYPE_ERROR = "error"
    TYPE_BEST_PRACTICE = "best_practice"

    def __init__(self, memory_dir: str = "memory/patterns"):
        """
        Initialize cross-session memory.

        Args:
            memory_dir: Directory for pattern storage
        """
        self.memory_dir = Path(memory_dir)
        self.patterns_file = self.memory_dir / "patterns.json"
        self.index_file = self.memory_dir / "index.json"

        # Ensure directory exists
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self._patterns: dict[str, LearnedPattern] = {}
        self._tag_index: dict[str, set[str]] = {}  # tag -> pattern_ids
        self._type_index: dict[str, set[str]] = {}  # type -> pattern_ids

        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load patterns from disk."""
        if not self.patterns_file.exists():
            return

        try:
            with open(self.patterns_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for pattern_data in data.get("patterns", []):
                pattern = LearnedPattern.from_dict(pattern_data)
                self._patterns[pattern.id] = pattern
                self._rebuild_indices(pattern)

        except (json.JSONDecodeError, KeyError):
            # Corrupted file - start fresh
            pass

    def _save_patterns(self) -> None:
        """Save patterns to disk."""
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "patterns": [p.to_dict() for p in self._patterns.values()],
        }

        with open(self.patterns_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _rebuild_indices(self, pattern: LearnedPattern) -> None:
        """Rebuild search indices for a pattern."""
        # Tag index
        for tag in pattern.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(pattern.id)

        # Type index
        if pattern.pattern_type not in self._type_index:
            self._type_index[pattern.pattern_type] = set()
        self._type_index[pattern.pattern_type].add(pattern.id)

    def learn(
        self,
        name: str,
        pattern_type: str,
        content: str,
        description: str = "",
        tags: list[str] | None = None,
        source_session: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Learn a new pattern.

        Args:
            name: Pattern name
            pattern_type: Type (code, task, error, best_practice)
            content: Pattern content
            description: Human-readable description
            tags: Searchable tags
            source_session: Session where this was learned
            metadata: Additional metadata

        Returns:
            Pattern ID
        """
        pattern_id = f"pattern_{len(self._patterns) + 1:04d}"

        pattern = LearnedPattern(
            id=pattern_id,
            name=name,
            pattern_type=pattern_type,
            content=content,
            description=description,
            tags=tags or [],
            success_count=0,
            failure_count=0,
            first_learned=datetime.now().isoformat(),
            last_used=datetime.now().isoformat(),
            source_session=source_session,
            metadata=metadata or {},
        )

        self._patterns[pattern_id] = pattern
        self._rebuild_indices(pattern)
        self._save_patterns()

        return pattern_id

    def recall(
        self,
        query: str,
        pattern_type: str | None = None,
        tags: list[str] | None = None,
        limit: int = 5,
        min_confidence: float = 0.0,
    ) -> list[LearnedPattern]:
        """
        Recall patterns matching query.

        Args:
            query: Search query (matched against name, description, content)
            pattern_type: Filter by type
            tags: Filter by tags
            limit: Maximum results
            min_confidence: Minimum confidence score

        Returns:
            List of matching patterns, sorted by relevance
        """
        query_lower = query.lower()
        results: list[tuple[float, LearnedPattern]] = []

        # Filter by type
        candidate_ids: set[str] | None = None
        if pattern_type:
            candidate_ids = self._type_index.get(pattern_type, set()).copy()
        else:
            candidate_ids = set(self._patterns.keys())

        # Filter by tags
        if tags:
            tagged_ids: set[str] = set()
            for tag in tags:
                tagged_ids.update(self._tag_index.get(tag, set()))
            candidate_ids &= tagged_ids if candidate_ids else tagged_ids

        # Score candidates
        for pattern_id in candidate_ids:
            pattern = self._patterns[pattern_id]

            # Skip low confidence
            if pattern.confidence < min_confidence:
                continue

            # Calculate relevance score
            score = 0.0

            # Exact name match
            if query_lower in pattern.name.lower():
                score += 10.0

            # Description match
            if query_lower in pattern.description.lower():
                score += 5.0

            # Content match
            if query_lower in pattern.content.lower():
                score += 3.0

            # Tag match
            for tag in pattern.tags:
                if query_lower in tag.lower():
                    score += 2.0
                    break

            # Boost by success count
            score += pattern.success_count * 0.1

            # Recency boost
            if pattern.last_used:
                days_ago = (datetime.now() - datetime.fromisoformat(pattern.last_used)).days
                if days_ago < 7:
                    score += 5.0
                elif days_ago < 30:
                    score += 2.0

            if score > 0:
                results.append((score, pattern))

        # Sort by score (descending)
        results.sort(key=lambda x: x[0], reverse=True)

        return [pattern for _, pattern in results[:limit]]

    def record_success(self, pattern_id: str) -> bool:
        """
        Record a successful use of a pattern.

        Args:
            pattern_id: Pattern ID

        Returns:
            True if recorded, False if pattern not found
        """
        if pattern_id not in self._patterns:
            return False

        pattern = self._patterns[pattern_id]
        pattern.success_count += 1
        pattern.last_used = datetime.now().isoformat()
        pattern.last_successful = datetime.now().isoformat()

        self._save_patterns()
        return True

    def record_failure(self, pattern_id: str) -> bool:
        """
        Record a failed use of a pattern.

        Args:
            pattern_id: Pattern ID

        Returns:
            True if recorded, False if pattern not found
        """
        if pattern_id not in self._patterns:
            return False

        pattern = self._patterns[pattern_id]
        pattern.failure_count += 1
        pattern.last_used = datetime.now().isoformat()

        self._save_patterns()
        return True

    def forget(self, pattern_id: str) -> bool:
        """
        Remove a pattern.

        Args:
            pattern_id: Pattern ID

        Returns:
            True if removed, False if not found
        """
        if pattern_id not in self._patterns:
            return False

        del self._patterns[pattern_id]
        self._save_patterns()
        return True

    def cleanup_stale(self, days: int = 30) -> int:
        """
        Remove stale patterns.

        Args:
            days: Number of days without use to consider stale

        Returns:
            Number of patterns removed
        """
        to_remove = []

        for pattern_id, pattern in self._patterns.items():
            if pattern.is_stale and pattern.success_count == 0:
                # Only auto-remove patterns that were never successful
                to_remove.append(pattern_id)

        for pattern_id in to_remove:
            del self._patterns[pattern_id]

        if to_remove:
            self._save_patterns()

        return len(to_remove)

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        return {
            "total_patterns": len(self._patterns),
            "by_type": {
                ptype: len(ids)
                for ptype, ids in self._type_index.items()
            },
            "total_tags": len(self._tag_index),
            "avg_confidence": (
                sum(p.confidence for p in self._patterns.values()) / len(self._patterns)
                if self._patterns
                else 0.5
            ),
            "high_confidence": sum(
                1 for p in self._patterns.values() if p.confidence >= 0.8
            ),
            "stale_patterns": sum(1 for p in self._patterns.values() if p.is_stale),
        }


class PatternExtractor:
    """
    Extracts patterns from session logs and task completions.

    Analyzes completed tasks and session logs to automatically
    identify reusable patterns.
    """

    def __init__(self, memory: CrossSessionMemory | None = None):
        self.memory = memory or CrossSessionMemory()

    def extract_from_code(
        self,
        code: str,
        description: str,
        tags: list[str] | None = None,
        session_id: str = "",
    ) -> str:
        """
        Extract a code pattern from source code.

        Args:
            code: Source code snippet
            description: What this code does
            tags: File type, language, etc.
            session_id: Source session

        Returns:
            Pattern ID
        """
        # Detect language from tags
        language = "python"
        if tags:
            for tag in tags:
                if tag in {"js", "javascript", "typescript", "ts"}:
                    language = "javascript"
                    break
                elif tag in {"go", "golang"}:
                    language = "go"
                    break

        return self.memory.learn(
            name=f"Code pattern: {description[:50]}",
            pattern_type=CrossSessionMemory.TYPE_CODE,
            content=code,
            description=description,
            tags=["code", language] + (tags or []),
            source_session=session_id,
            metadata={"language": language},
        )

    def extract_from_task(
        self,
        task_name: str,
        task_structure: str,
        successful_subtasks: list[str],
        session_id: str = "",
    ) -> str:
        """
        Extract a task pattern from a successful task decomposition.

        Args:
            task_name: Name of the task
            task_structure: JSON structure of task decomposition
            successful_subtasks: List of completed subtask descriptions
            session_id: Source session

        Returns:
            Pattern ID
        """
        return self.memory.learn(
            name=f"Task pattern: {task_name[:50]}",
            pattern_type=CrossSessionMemory.TYPE_TASK,
            content=task_structure,
            description=f"Task '{task_name}' with {len(successful_subtasks)} subtasks",
            tags=["task", "decomposition"] + [s.lower().replace(" ", "_") for s in successful_subtasks[:5]],
            source_session=session_id,
            metadata={"subtask_count": len(successful_subtasks)},
        )

    def extract_from_error(
        self,
        error_type: str,
        error_message: str,
        fix_code: str,
        session_id: str = "",
    ) -> str:
        """
        Extract an error pattern and its fix.

        Args:
            error_type: Type of error (SyntaxError, ValueError, etc.)
            error_message: Original error message
            fix_code: Code that fixed the error
            session_id: Source session

        Returns:
            Pattern ID
        """
        return self.memory.learn(
            name=f"Error fix: {error_type}",
            pattern_type=CrossSessionMemory.TYPE_ERROR,
            content=fix_code,
            description=f"Fix for {error_type}: {error_message[:100]}",
            tags=["error", "fix", error_type.lower()],
            source_session=session_id,
            metadata={"error_type": error_type, "error_message": error_message},
        )

    def extract_from_session_logs(
        self,
        session_dir: Path,
        session_id: str,
    ) -> list[str]:
        """
        Extract patterns from session logs.

        Args:
            session_dir: Directory containing session logs
            session_id: Session ID to analyze

        Returns:
            List of extracted pattern IDs
        """
        pattern_ids = []
        session_file = session_dir / f"{session_id}.json"

        if not session_file.exists():
            return pattern_ids

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            # Extract from checkpoints
            for checkpoint in session_data.get("checkpoints", []):
                if checkpoint.get("status") == "success":
                    summary = checkpoint.get("summary", "")
                    if summary:
                        pattern_ids.append(
                            self.memory.learn(
                                name=f"Checkpoint: {summary[:50]}",
                                pattern_type=CrossSessionMemory.TYPE_BEST_PRACTICE,
                                content=json.dumps(checkpoint.get("details", {})),
                                description=summary,
                                tags=["checkpoint", "session"],
                                source_session=session_id,
                            )
                        )

        except (json.JSONDecodeError, KeyError):
            pass

        return pattern_ids


# Convenience functions
_global_memory: CrossSessionMemory | None = None


def get_cross_session_memory(memory_dir: str = "memory/patterns") -> CrossSessionMemory:
    """Get or create global cross-session memory."""
    global _global_memory
    if _global_memory is None:
        _global_memory = CrossSessionMemory(memory_dir)
    return _global_memory


def learn_pattern(
    name: str,
    pattern_type: str,
    content: str,
    description: str = "",
    tags: list[str] | None = None,
) -> str:
    """Quick way to learn a pattern."""
    return get_cross_session_memory().learn(
        name=name,
        pattern_type=pattern_type,
        content=content,
        description=description,
        tags=tags,
    )


def recall_patterns(
    query: str,
    pattern_type: str | None = None,
    limit: int = 5,
) -> list[LearnedPattern]:
    """Quick way to recall patterns."""
    return get_cross_session_memory().recall(
        query=query,
        pattern_type=pattern_type,
        limit=limit,
    )
