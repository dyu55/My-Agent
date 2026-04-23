"""Logging utilities for agent execution tracing."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TraceLogger:
    """
    Logs agent execution for debugging and analysis.

    Writes structured JSON logs to a file for later inspection.
    """

    def __init__(self, log_dir: str = "logs"):
        """
        Initialize trace logger.

        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = Path(log_dir).resolve()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trace_file = self.log_dir / f"trace-{datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"

    def log(self, event: str, payload: dict[str, Any]) -> None:
        """
        Log an event with payload.

        Args:
            event: Event name (e.g., "agent_start", "execution_result")
            payload: Event data
        """
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "payload": payload,
        }
        with self.trace_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def get_log_path(self) -> str:
        """Get the path to the current log file."""
        return str(self.trace_file)


def setup_logger(name: str = "myagent", level: int = logging.INFO) -> logging.Logger:
    """
    Set up a standard Python logger.

    Args:
        name: Logger name
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger