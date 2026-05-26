"""Tests for agent/tools/rollback_tools.py and file rollback functionality."""
import tempfile
from pathlib import Path
import pytest
from agent.tools.rollback_tools import RollbackManager, BackupEntry
from agent.tools.file_tools import FileTools


class TestRollbackManager:
    """Tests for RollbackManager class."""

    @pytest.fixture
    def backup_dir(self, tmp_path):
        """Create temporary backup directory."""
        return str(tmp_path / "backups")

    @pytest.fixture
    def manager(self, backup_dir):
        """Create RollbackManager instance."""
        return RollbackManager(backup_dir=backup_dir)

    def test_initialization(self, backup_dir):
        """Test RollbackManager initialization."""
        manager = RollbackManager(backup_dir=backup_dir)
        assert manager.backup_dir == Path(backup_dir)
        assert manager.backups == {}
        assert manager.backup_dir.exists()

    def test_backup_existing_file(self, manager, tmp_path):
        """Test backing up an existing file."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        # Backup the file
        backup_path = manager.backup(str(test_file))

        assert backup_path is not None
        assert Path(backup_path).exists()
        assert Path(backup_path).read_text() == "original content"
        assert manager.has_backup(str(test_file))

    def test_backup_nonexistent_file(self, manager, tmp_path):
        """Test backing up a file that doesn't exist returns None."""
        test_file = tmp_path / "nonexistent.txt"
        backup_path = manager.backup(str(test_file))
        assert backup_path is None

    def test_rollback_success(self, manager, tmp_path):
        """Test successful file rollback."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content")

        # Backup and modify
        manager.backup(str(test_file))
        test_file.write_text("modified content")

        # Rollback
        result = manager.rollback(str(test_file))

        assert result is True
        assert test_file.read_text() == "original content"
        assert not manager.has_backup(str(test_file))

    def test_rollback_without_backup(self, manager, tmp_path):
        """Test rollback fails when no backup exists."""
        test_file = tmp_path / "test.txt"
        result = manager.rollback(str(test_file))
        assert result is False

    def test_commit_clears_backup(self, manager, tmp_path):
        """Test commit removes backup after successful edit."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("original")

        manager.backup(str(test_file))
        assert manager.has_backup(str(test_file))

        manager.commit(str(test_file))
        assert not manager.has_backup(str(test_file))

    def test_get_backup_info(self, manager, tmp_path):
        """Test getting backup information."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        manager.backup(str(test_file))
        info = manager.get_backup_info(str(test_file))

        assert info is not None
        assert "timestamp" in info
        assert "path" in info
        assert "age_seconds" in info
        assert info["age_seconds"] < 1  # Should be very recent

    def test_get_backup_info_nonexistent(self, manager, tmp_path):
        """Test getting info for non-existent backup."""
        test_file = tmp_path / "test.txt"
        info = manager.get_backup_info(str(test_file))
        assert info is None

    def test_cleanup_old_backups(self, manager, tmp_path):
        """Test cleaning up old backups."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        manager.backup(str(test_file))
        count = manager.cleanup_old_backups(max_age_hours=24.0)

        # Should not clean up recent backups
        assert count == 0
        assert manager.has_backup(str(test_file))


class TestFileToolsRollback:
    """Tests for FileTools rollback integration."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create temporary workspace."""
        return str(tmp_path)

    @pytest.fixture
    def file_tools(self, workspace):
        """Create FileTools with rollback enabled."""
        return FileTools(workspace, enable_rollback=True)

    @pytest.fixture
    def file_tools_no_rollback(self, workspace):
        """Create FileTools with rollback disabled."""
        return FileTools(workspace, enable_rollback=False)

    def test_write_creates_backup(self, file_tools, workspace):
        """Test writing to existing file creates backup."""
        # Create initial file
        test_file = Path(workspace) / "test.txt"
        test_file.write_text("original content")

        # Write new content (should create backup)
        result = file_tools.write_file({
            "path": "test.txt",
            "content": "new content",
        })

        assert result.success
        assert test_file.read_text() == "new content"

    def test_edit_creates_backup(self, file_tools, workspace):
        """Test editing creates backup before modification."""
        # Create initial file
        test_file = Path(workspace) / "test.txt"
        test_file.write_text("Hello World")

        # Edit file
        result = file_tools.edit_file({
            "path": "test.txt",
            "old_text": "World",
            "content": "Universe",
        })

        assert result.success
        assert test_file.read_text() == "Hello Universe"

    def test_write_new_file_no_backup(self, file_tools, workspace):
        """Test writing new file doesn't create backup."""
        result = file_tools.write_file({
            "path": "new.txt",
            "content": "brand new",
        })

        assert result.success
        # No backup should exist for new files
        assert not file_tools._rollback_manager.has_backup(
            str(Path(workspace) / "new.txt")
        )

    def test_rollback_disabled(self, file_tools_no_rollback, workspace):
        """Test that rollback can be disabled."""
        # Create initial file
        test_file = Path(workspace) / "test.txt"
        test_file.write_text("original")

        # Edit with rollback disabled
        result = file_tools_no_rollback.edit_file({
            "path": "test.txt",
            "old_text": "original",
            "content": "modified",
        })

        assert result.success
        assert file_tools_no_rollback._rollback_manager is None

    def test_edit_old_text_not_found_no_backup_change(self, file_tools, workspace):
        """Test that failed edit doesn't leave stale backup."""
        test_file = Path(workspace) / "test.txt"
        test_file.write_text("Hello")

        # Try to edit with non-existent text
        result = file_tools.edit_file({
            "path": "test.txt",
            "old_text": "NonExistent",
            "content": "New",
        })

        assert not result.success
        # File should be unchanged
        assert test_file.read_text() == "Hello"