"""Streaming progress display for agent execution."""

import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable


@dataclass
class ProgressMetrics:
    """Metrics for agent execution."""
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    llm_calls: int = 0
    tool_executions: int = 0
    start_time: float = field(default_factory=time.time)
    current_task: str = ""
    current_phase: str = ""  # plan, act, reflect, done


class StreamingProgress:
    """
    Real-time progress display for agent execution.

    Features:
    - Progress bar with percentage
    - Current task display
    - LLM calls counter
    - Tool execution counter
    - Elapsed time
    - Phase indicator
    - Color-coded status (when terminal supports it)
    """

    # ANSI color codes (fallback to plain text if not a TTY)
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
    }

    # Status icons
    ICONS = {
        "plan": "📋",
        "act": "⚡",
        "reflect": "🔍",
        "done": "✅",
        "error": "❌",
        "waiting": "⏳",
        "thinking": "🧠",
        "executing": "🔧",
    }

    def __init__(self, total_tasks: int = 0, enabled: bool = True):
        """
        Initialize streaming progress.

        Args:
            total_tasks: Total number of tasks (0 for unknown)
            enabled: Whether to show progress (False for quiet mode)
        """
        self.metrics = ProgressMetrics(total_tasks=total_tasks)
        self.enabled = enabled and sys.stdout.isatty()
        self._last_line_len = 0
        self._phase_icons = self.ICONS
        self._colors = self.COLORS if self.enabled else {}
        self._update_interval = 0.1  # Update every 100ms max

    def _color(self, name: str) -> str:
        """Get color code if enabled."""
        return self._colors.get(name, "")

    def _clear_line(self) -> None:
        """Clear the current line."""
        if self.enabled:
            sys.stdout.write("\033[2K\r")  # Clear entire line
            sys.stdout.flush()

    def _print_at_line_start(self, text: str) -> None:
        """Print text at the start of the current line."""
        self._clear_line()
        print(text, end="", flush=True)
        self._last_line_len = len(text)

    def start(self, task: str = "Initializing...") -> None:
        """Start progress tracking."""
        self.metrics.start_time = time.time()
        self.metrics.current_task = task
        self.metrics.current_phase = "plan"
        self._print_status(f"{self._color('cyan')}{self._phase_icons['plan']} Starting...")

    def set_total_tasks(self, total: int) -> None:
        """Set total number of tasks."""
        self.metrics.total_tasks = total

    def update_task(self, task: str) -> None:
        """Update current task description."""
        self.metrics.current_task = task
        self._print_progress()

    def set_phase(self, phase: str) -> None:
        """Update current phase (plan, act, reflect, done)."""
        self.metrics.current_phase = phase
        self._print_progress()

    def increment_llm_calls(self, count: int = 1) -> None:
        """Increment LLM call counter."""
        self.metrics.llm_calls += count
        self._print_progress()

    def increment_tool_execution(self, count: int = 1) -> None:
        """Increment tool execution counter."""
        self.metrics.tool_executions += count
        self._print_progress()

    def task_completed(self) -> None:
        """Mark current task as completed."""
        self.metrics.completed_tasks += 1
        self._print_progress()

    def task_failed(self) -> None:
        """Mark current task as failed."""
        self.metrics.failed_tasks += 1
        self._print_progress()

    def _elapsed_time(self) -> str:
        """Get formatted elapsed time."""
        elapsed = time.time() - self.metrics.start_time
        if elapsed < 60:
            return f"{elapsed:.1f}s"
        elif elapsed < 3600:
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(elapsed // 3600)
            mins = int((elapsed % 3600) // 60)
            return f"{hours}h {mins}m"

    def _progress_bar(self, width: int = 20) -> str:
        """Generate progress bar."""
        if self.metrics.total_tasks <= 0:
            # Indeterminate progress
            return "[" + "▓" * (width - 2) + "]"
        else:
            completed = self.metrics.completed_tasks + self.metrics.failed_tasks
            progress = completed / self.metrics.total_tasks
            filled = int(progress * width)
            empty = width - filled
            return f"[{self._color('green')}{'▓' * filled}{self._color('dim')}{'░' * empty}{self._color('reset')}]"

    def _print_progress(self) -> None:
        """Print current progress state."""
        if not self.enabled:
            return

        # Phase icon
        phase_icon = self._phase_icons.get(self.metrics.current_phase, "•")
        phase_color = {
            "plan": "blue",
            "act": "yellow",
            "reflect": "magenta",
            "done": "green",
        }.get(self.metrics.current_phase, "white")

        # Progress components
        progress_bar = self._progress_bar()
        task_count = f"{self.metrics.completed_tasks}/{self.metrics.total_tasks}" if self.metrics.total_tasks > 0 else "?"
        elapsed = self._elapsed_time()
        llm = self.metrics.llm_calls
        tools = self.metrics.tool_executions

        # Truncate task name if too long
        task = self.metrics.current_task[:40]
        if len(self.metrics.current_task) > 40:
            task += "..."

        # Build status line
        line = (
            f"{self._color(phase_color)}{phase_icon}{self._color('reset')} "
            f"{progress_bar} {self._color('bold')}{task_count}{self._color('reset')} "
            f"| {self._color('cyan')}LLM:{llm}{self._color('reset')} "
            f"| {self._color('yellow')}Tools:{tools}{self._color('reset')} "
            f"| {self._color('dim')}{elapsed}{self._color('reset')} "
            f"{self._color('dim')}{task}{self._color('reset')}"
        )

        self._print_at_line_start(line)

    def _print_status(self, text: str) -> None:
        """Print a status message."""
        self._print_at_line_start(text)
        print()  # New line after status

    def log(self, event: str, message: str = "", level: str = "info") -> None:
        """
        Log an event with optional message.

        Args:
            event: Event name or icon
            message: Additional message
            level: Log level (info, success, warning, error)
        """
        if not self.enabled:
            return

        colors = {
            "info": "blue",
            "success": "green",
            "warning": "yellow",
            "error": "red",
        }
        color = colors.get(level, "white")

        self._print_at_line_start(f"{self._color(color)}{event}{self._color('reset')} {message}")
        print()  # New line after log

    def section(self, title: str) -> None:
        """Print a section header."""
        if not self.enabled:
            return
        print()
        print(f"{self._color('bold')}{'─' * 50}{self._color('reset')}")
        print(f"{self._color('bold')}{title}{self._color('reset')}")
        print(f"{self._color('dim')}{'─' * 50}{self._color('reset')}")

    def finish(self, summary: str = "") -> None:
        """Finish progress tracking."""
        self.metrics.current_phase = "done"

        if self.enabled:
            print()  # New line after progress

            # Summary box
            total_time = self._elapsed_time()
            success = self.metrics.completed_tasks
            failed = self.metrics.failed_tasks
            llm = self.metrics.llm_calls
            tools = self.metrics.tool_executions

            summary_text = summary or "Task completed"
            print(f"{self._color('bold')}{'═' * 50}{self._color('reset')}")
            print(f"{self._color('green')}✅ {summary_text}{self._color('reset')}")
            print(f"{self._color('dim')}{'─' * 50}{self._color('reset')}")
            print(f"  {self._color('green')}✅ Completed: {success}{self._color('reset')}" if success else "")
            print(f"  {self._color('red')}❌ Failed: {failed}{self._color('reset')}" if failed else "")
            print(f"  {self._color('cyan')}🧠 LLM calls: {llm}{self._color('reset')}")
            print(f"  {self._color('yellow')}🔧 Tool calls: {tools}{self._color('reset')}")
            print(f"  {self._color('dim')}⏱️  Total time: {total_time}{self._color('reset')}")
            print(f"{self._color('bold')}{'═' * 50}{self._color('reset')}")

    def debug(self, message: str) -> None:
        """Print debug message (only in debug mode)."""
        if self.enabled:
            print(f"{self._color('dim')}[DEBUG] {message}{self._color('reset')}")


class ProgressCallback:
    """
    Callback interface for progress updates.

    Use this to integrate progress tracking with external systems.
    """

    def __init__(self, progress: StreamingProgress | None = None):
        self.progress = progress or StreamingProgress(enabled=False)

    def on_task_start(self, task: str) -> None:
        """Called when a task starts."""
        self.progress.update_task(task)

    def on_task_complete(self) -> None:
        """Called when a task completes."""
        self.progress.task_completed()

    def on_task_fail(self) -> None:
        """Called when a task fails."""
        self.progress.task_failed()

    def on_llm_call(self) -> None:
        """Called after each LLM call."""
        self.progress.increment_llm_calls()

    def on_tool_execution(self) -> None:
        """Called after each tool execution."""
        self.progress.increment_tool_execution()


# Global progress instance
_global_progress: StreamingProgress | None = None


def get_progress(total_tasks: int = 0) -> StreamingProgress:
    """Get or create global progress instance."""
    global _global_progress
    if _global_progress is None:
        _global_progress = StreamingProgress(total_tasks=total_tasks)
    return _global_progress


def reset_progress() -> None:
    """Reset global progress instance."""
    global _global_progress
    _global_progress = None