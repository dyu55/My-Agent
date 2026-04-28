import argparse
import json
from pathlib import Path
import pytest

import todo

@pytest.fixture
def mock_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Mock the storage path to use tmp_path/.todos.json"""
    monkeypatch.setattr(todo, "STORAGE_PATH", tmp_path / ".todos.json")
    return tmp_path

def test_add_todo(mock_storage: Path, capfd: pytest.CaptureFixture[str]) -> None:
    args = argparse.Namespace(text="Write report", priority="high", due_date="2024-05-01")
    todo.cmd_add(args)
    out, _ = capfd.readouterr()
    assert "Added:" in out
    data = json.loads(mock_storage.joinpath(".todos.json").read_text())
    assert len(data) == 1
    assert data[0]["text"] == "Write report"
    assert data[0]["priority"] == "high"
    assert data[0]["due_date"] == "2024-05-01"
    assert data[0]["completed"] is False

def test_list_all_todos(mock_storage: Path, capfd: pytest.CaptureFixture[str]) -> None:
    args_add = argparse.Namespace(text="Clean room", priority="low", due_date=None)
    todo.cmd_add(args_add)
    args_list = argparse.Namespace(status="all")
    todo.cmd_list(args_list)
    out, _ = capfd.readouterr()
    assert "Clean room" in out
    assert "⬜️" in out

def test_list_filter_pending(mock_storage: Path, capfd: pytest.CaptureFixture[str]) -> None:
    args_add = argparse.Namespace(text="Pending task", priority="medium", due_date="2024-01-01")
    todo.cmd_add(args_add)
    todo_id = json.loads(mock_storage.joinpath(".todos.json").read_text())[0]["id"]
    todo.cmd_done(argparse.Namespace(id=todo_id))

    args_list = argparse.Namespace(status="pending")
    todo.cmd_list(args_list)
    out, _ = capfd.readouterr()
    assert "Pending task" not in out
    assert "No todos found." in out

def test_mark_done(mock_storage: Path, capfd: pytest.CaptureFixture[str]) -> None:
    args_add = argparse.Namespace(text="Pay bills", priority="medium", due_date="2024-06-15")
    todo.cmd_add(args_add)
    todo_id = json.loads(mock_storage.joinpath(".todos.json").read_text())[0]["id"]

    args_done = argparse.Namespace(id=todo_id)
    todo.cmd_done(args_done)
    out, _ = capfd.readouterr()
    assert f"Marked {todo_id} as done." in out

    data = json.loads(mock_storage.joinpath(".todos.json").read_text())
    assert data[0]["completed"] is True

def test_delete_todo(mock_storage: Path, capfd: pytest.CaptureFixture[str]) -> None:
    args_add = argparse.Namespace(text="Old task", priority="low", due_date=None)
    todo.cmd_add(args_add)
    todo_id = json.loads(mock_storage.joinpath(".todos.json").read_text())[0]["id"]

    args_delete = argparse.Namespace(id=todo_id)
    todo.cmd_delete(args_delete)
    out, _ = capfd.readouterr()
    assert f"Deleted {todo_id}." in out

    data = json.loads(mock_storage.joinpath(".todos.json").read_text())
    assert len(data) == 0

def test_not_found_done(mock_storage: Path, capfd: pytest.CaptureFixture[str]) -> None:
    args = argparse.Namespace(id="nonexistent")
    todo.cmd_done(args)
    out, _ = capfd.readouterr()
    assert "not found" in out

def test_not_found_delete(mock_storage: Path, capfd: pytest.CaptureFixture[str]) -> None:
    args = argparse.Namespace(id="nonexistent")
    todo.cmd_delete(args)
    out, _ = capfd.readouterr()
    assert "not found" in out