"""Process Monitor - Watch and analyze process output."""

import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class MonitorState(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class ErrorPattern(Enum):
    """Common error patterns to detect."""

    SYNTAX_ERROR = r"(?i)SyntaxError|IndentationError|TabError"
    RUNTIME_ERROR = r"(?i)RuntimeError|Exception|Error:"
    IMPORT_ERROR = r"(?i)ImportError|ModuleNotFoundError|No module named"
    TEST_FAILED = r"(?i)(FAILED|ERROR|assertion).*in"
    TIMEOUT = r"(?i)timeout|timed out"
    MEMORY_ERROR = r"(?i)MemoryError|OOM|Killed"


@dataclass
class ProcessEvent:
    """An event captured from process output."""

    timestamp: datetime
    event_type: str  # "output", "error", "match", "exit"
    content: str
    line_number: int = 0
    pattern: str | None = None


@dataclass
class MonitorConfig:
    """Configuration for process monitoring."""

    patterns: list[tuple[str, str]] = field(default_factory=list)  # (name, regex)
    error_patterns: list[ErrorPattern] = field(default_factory=list)
    capture_lines: int = 10  # Lines before/after match to capture
    check_interval: float = 0.5  # Seconds between checks


@dataclass
class MonitorResult:
    """Result of a monitoring session."""

    state: MonitorState
    events: list[ProcessEvent] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    exit_code: int | None = None
    duration: float = 0.0


class ProcessMonitor:
    """
    Monitor a process and capture its output.

    Similar to Claude Code's /watch command, this can:
    - Watch a process for specific patterns
    - Detect error conditions
    - Capture output around matches
    - Notify on events
    """

    def __init__(self, config: MonitorConfig | None = None):
        self.config = config or MonitorConfig()
        self.state = MonitorState.STOPPED
        self.process: subprocess.Popen | None = None
        self.events: list[ProcessEvent] = []
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._line_number = 0
        self._start_time: float = 0

        # Add default error patterns if none specified
        if not self.config.error_patterns:
            self.config.error_patterns = list(ErrorPattern)

        # Compile patterns
        self._compiled_patterns: list[tuple[str, re.Pattern]] = []
        for name, pattern in self.config.patterns:
            self._compiled_patterns.append((name, re.compile(pattern)))

    def start(
        self,
        command: str | list[str],
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
        shell: bool = False,
    ) -> bool:
        """
        Start monitoring a process.

        Args:
            command: Command to run
            cwd: Working directory
            env: Environment variables
            shell: Run through shell

        Returns:
            True if started successfully
        """
        if self.state == MonitorState.RUNNING:
            return False

        try:
            if isinstance(command, str) and not shell:
                command = command.split()

            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                cwd=str(cwd) if cwd else None,
                env=env,
                shell=shell,
                text=True,
                bufsize=1,  # Line buffered
            )

            self.state = MonitorState.RUNNING
            self._start_time = time.time()
            self._stop_event.clear()
            self.events = []
            self._line_number = 0

            # Start monitoring thread
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()

            return True

        except Exception as e:
            self.state = MonitorState.STOPPED
            return False

    def _monitor_loop(self) -> None:
        """Monitor loop running in separate thread."""
        while not self._stop_event.is_set():
            if self.process is None:
                break

            # Check if process has finished
            if self.process.poll() is not None:
                self._on_exit(self.process.returncode or 0)
                break

            # Read output
            try:
                line = self.process.stdout.readline()
                if line:
                    self._line_number += 1
                    self._process_line(line.rstrip("\n"))
                elif self.process.poll() is not None:
                    # Process finished
                    remaining = self.process.stdout.read()
                    if remaining:
                        for line in remaining.splitlines():
                            self._line_number += 1
                            self._process_line(line)
                    self._on_exit(self.process.returncode or 0)
                    break
            except Exception:
                break

            time.sleep(self.config.check_interval)

    def _process_line(self, line: str) -> None:
        """Process a single line of output."""
        event = ProcessEvent(
            timestamp=datetime.now(),
            event_type="output",
            content=line,
            line_number=self._line_number,
        )

        # Check custom patterns
        for name, pattern in self._compiled_patterns:
            if pattern.search(line):
                event.event_type = "match"
                event.pattern = name
                self._on_pattern_match(name, line)

        # Check error patterns
        for error_pattern in self.config.error_patterns:
            if re.search(error_pattern.value, line):
                event.event_type = "error"
                self._on_error_detected(error_pattern, line)

        self.events.append(event)

    def _on_pattern_match(self, pattern_name: str, line: str) -> None:
        """Called when a pattern matches."""
        pass

    def _on_error_detected(self, error: ErrorPattern, line: str) -> None:
        """Called when an error is detected."""
        pass

    def _on_exit(self, exit_code: int) -> None:
        """Called when process exits."""
        self.state = MonitorState.STOPPED
        self.events.append(
            ProcessEvent(
                timestamp=datetime.now(),
                event_type="exit",
                content=f"Process exited with code {exit_code}",
                line_number=self._line_number,
            )
        )

    def stop(self) -> None:
        """Stop monitoring."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        if self.process:
            self.process.terminate()
            self.process = None
        self.state = MonitorState.STOPPED

    def pause(self) -> None:
        """Pause monitoring."""
        self.state = MonitorState.PAUSED

    def resume(self) -> None:
        """Resume monitoring."""
        if self.state == MonitorState.PAUSED:
            self.state = MonitorState.RUNNING

    def send_input(self, input_text: str) -> None:
        """Send input to the process."""
        if self.process and self.process.stdin:
            self.process.stdin.write(input_text + "\n")
            self.process.stdin.flush()

    def get_result(self) -> MonitorResult:
        """Get the monitoring result."""
        error_count = sum(1 for e in self.events if e.event_type == "error")
        warning_count = sum(1 for e in self.events if e.event_type == "match")

        return MonitorResult(
            state=self.state,
            events=self.events.copy(),
            error_count=error_count,
            warning_count=warning_count,
            exit_code=self.process.poll() if self.process else None,
            duration=time.time() - self._start_time if self._start_time else 0,
        )

    def get_recent_output(self, lines: int = 20) -> str:
        """Get recent output lines."""
        output_lines = [e.content for e in self.events[-lines:]]
        return "\n".join(output_lines)

    def get_errors(self) -> list[ProcessEvent]:
        """Get all error events."""
        return [e for e in self.events if e.event_type == "error"]

    def get_summary(self) -> str:
        """Get a summary of the monitoring session."""
        result = self.get_result()

        lines = [
            f"Monitor State: {result.state.value}",
            f"Duration: {result.duration:.2f}s",
            f"Exit Code: {result.exit_code}",
            f"Lines: {self._line_number}",
            f"Errors: {result.error_count}",
            f"Matches: {result.warning_count}",
        ]

        return "\n".join(lines)


def watch_command(
    command: str,
    patterns: list[str] | None = None,
    cwd: str | Path | None = None,
) -> ProcessMonitor:
    """
    Watch a command for output.

    Similar to Claude Code's /watch.

    Args:
        command: Command to run
        patterns: List of regex patterns to watch for
        cwd: Working directory

    Returns:
        ProcessMonitor instance
    """
    config = MonitorConfig()

    if patterns:
        for p in patterns:
            config.patterns.append(("custom", p))

    monitor = ProcessMonitor(config)
    monitor.start(command, cwd=cwd)

    return monitor