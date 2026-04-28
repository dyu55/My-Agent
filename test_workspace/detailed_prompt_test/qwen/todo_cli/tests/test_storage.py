import pytest
from pathlib import Path
from src import storage
from src.models import TodoItem

def test_load_empty_storage(tmp_path: Path, monkeypatch) -> None:
    fake_path: Path = tmp_path / "fake_todos.json"
    monkeypatch.setattr(storage, "STORAGE_PATH", fake_path)
    assert storage.load_todos() == []

def test_save_and_load_todos(tmp_path: Path, monkeypatch) -> None:
    fake_path: Path = tmp_path / "fake_todos.json"
    monkeypatch.setattr(storage, "STORAGE_PATH", fake_path)
    todo: TodoItem = TodoItem(title="Test", priority="high")
    storage.save_todos([todo])
    loaded: list[TodoItem] = storage.load_todos()
    assert len(loaded) == 1
    assert loaded[0].title == "Test"
    assert loaded[0].priority == "high"