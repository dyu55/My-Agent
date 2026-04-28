import pytest
from pathlib import Path
from src.commands import add
from src.commands import list as list_commands
from src.commands import done
from src.commands import delete
from src import storage
from src.models import TodoItem

@pytest.fixture(autouse=True)
def setup_fake_storage(tmp_path: Path, monkeypatch) -> None:
    fake_path: Path = tmp_path / "test_todos.json"
    monkeypatch.setattr(storage, "STORAGE_PATH", fake_path)
    storage.save_todos([])

def test_add_command_creates_todo(tmp_path: Path) -> None:
    result: TodoItem = add.add("Buy milk", "low", "2024-01-01")
    assert result.title == "Buy milk"
    todos: list[TodoItem] = storage.load_todos()
    assert len(todos) == 1

def test_list_command_returns_todos(tmp_path: Path) -> None:
    storage.save_todos([])
    todos: list[TodoItem] = list_commands.list_todos()
    assert todos == []

def test_mark_done_command_updates_status(tmp_path: Path) -> None:
    new_todo: TodoItem = add.add("Task", "medium")
    result: TodoItem | None = done.mark_done(new_todo.id)
    assert result is not None
    assert result.done is True

def test_delete_command_removes_todo(tmp_path: Path) -> None:
    new_todo: TodoItem = add.add("Del me", "high")
    result: TodoItem | None = delete.delete_todo(new_todo.id)
    assert result is not None
    assert len(storage.load_todos()) == 0

def test_mark_done_nonexistent_returns_none(tmp_path: Path) -> None:
    result: TodoItem | None = done.mark_done("nonexistent-id")
    assert result is None