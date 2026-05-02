"""Rollback Manager - Provides file backup and restore functionality.

This module provides the RollbackManager class that creates backups of files
before modifications and can restore them on error.
"""
from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class BackupEntry:
    """Represents a file backup entry."""
    path: Path
    timestamp: float
    original_path: str | None = None


class RollbackManager:
    """
    Manages file backups for safe editing.

    Usage:
        manager = RollbackManager(backup_dir=".agent_backups")

        # Before editing a file
        manager.backup("/path/to/file.py")

        # After successful edit
        manager.commit("/path/to/file.py")

        # On error, rollback
        manager.rollback("/path/to/file.py")
    """

    def __init__(self, backup_dir: str = ".agent_backups"):
        """
        Initialize the RollbackManager.

        Args:
            backup_dir: Directory to store backups (relative to workspace)
        """
        self.backup_dir = Path(backup_dir)
        self.backups: dict[str, BackupEntry] = {}
        self._ensure_backup_dir()

    def _ensure_backup_dir(self) -> None:
        """Ensure backup directory exists."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup(self, file_path: str) -> str | None:
        """
        Create a backup of a file before modification.

        Args:
            file_path: Path to the file to backup

        Returns:
            Path to the backup file, or None if file doesn't exist
        """
        path = Path(file_path)

        # Only backup if file exists
        if not path.exists():
            return None

        # Create unique backup filename with timestamp
        backup_name = f"{int(time.time() * 1000)}_{path.name}"
        backup_path = self.backup_dir / backup_name

        # Copy file to backup location
        shutil.copy2(path, backup_path)

        # Record backup
        self.backups[file_path] = BackupEntry(
            path=backup_path,
            timestamp=time.time(),
            original_path=file_path,
        )

        return str(backup_path)

    def rollback(self, file_path: str) -> bool:
        """
        Restore a file from its backup.

        Args:
            file_path: Path to the file to restore

        Returns:
            True if rollback successful, False otherwise
        """
        if file_path not in self.backups:
            return False

        backup = self.backups[file_path]

        try:
            shutil.copy2(backup.path, file_path)
            # Clean up backup file
            backup.path.unlink(missing_ok=True)
            del self.backups[file_path]
            return True
        except Exception:
            return False

    def commit(self, file_path: str) -> None:
        """
        Clean up backup after successful modification.

        Args:
            file_path: Path to the file that was successfully modified
        """
        if file_path in self.backups:
            backup = self.backups[file_path]
            backup.path.unlink(missing_ok=True)
            del self.backups[file_path]

    def get_backup_info(self, file_path: str) -> dict[str, Any] | None:
        """
        Get information about a file's backup.

        Args:
            file_path: Path to the file

        Returns:
            Dict with backup info, or None if no backup exists
        """
        if file_path not in self.backups:
            return None

        backup = self.backups[file_path]
        return {
            "path": str(backup.path),
            "timestamp": backup.timestamp,
            "age_seconds": time.time() - backup.timestamp,
        }

    def has_backup(self, file_path: str) -> bool:
        """Check if a file has a backup."""
        return file_path in self.backups

    def cleanup_old_backups(self, max_age_hours: float = 24.0) -> int:
        """
        Remove old backup files.

        Args:
            max_age_hours: Maximum age of backups to keep

        Returns:
            Number of backups removed
        """
        cutoff = time.time() - (max_age_hours * 3600)
        count = 0

        for backup in self.backups.values():
            if backup.timestamp < cutoff:
                backup.path.unlink(missing_ok=True)
                count += 1

        # Clean up entries
        self.backups = {
            fp: be for fp, be in self.backups.items()
            if be.timestamp >= cutoff
        }

        return count

    def clear_all_backups(self) -> int:
        """
        Remove all backups.

        Returns:
            Number of backups removed
        """
        count = len(self.backups)

        for backup in self.backups.values():
            backup.path.unlink(missing_ok=True)

        self.backups.clear()
        return count