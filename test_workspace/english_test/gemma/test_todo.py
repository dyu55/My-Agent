import pytest
import os
from pathlib import Path
from storage import TodoStorage
from models import TodoItem

@pytest.fixture
def temp_storage(tmp_path):
    file = tmp_path / "test_todos.json"
    return TodoStorage(filepath=str(file))

def test_storage_save_load(temp_storage):
    todos = [
        TodoItem(id=1, task="Test 1", priority="High"),
        TodoItem(id=2, task="Test 2", priority="Low", due_date="2023-12-31")
    ]
    temp_storage.save(todos)
    
    loaded = temp_storage.load()
    assert len(loaded) == 2
    assert loaded[0].task == "Test 1"
    assert loaded[1].priority == "Low"
    assert loaded[1].due_date == "2023-12-31"

def test_storage_empty_file(temp_storage):
    # File doesn't exist yet
    assert temp_storage.load() == []

def test_todo_item_serialization():
    item = TodoItem(id=5, task="Serialize me", priority="Medium")
    data = item.to_dict()
    assert data["id"] == 5
    assert data["task"] == "Serialize me"
    
    new_item = TodoItem.from_dict(data)
    assert new_item == item

def test_todo_item_defaults():
    item = TodoItem(id=1, task="Default test")
    assert item.priority == "Medium"
    assert item.completed is False
    assert item.due_date is None