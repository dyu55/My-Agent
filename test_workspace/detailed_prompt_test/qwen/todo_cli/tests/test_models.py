from src.models import TodoItem

def test_create_todo_with_defaults() -> None:
    todo: TodoItem = TodoItem(title="Test")
    assert todo.title == "Test"
    assert todo.priority == "medium"
    assert todo.done is False
    assert todo.due_date is None
    assert len(todo.id) == 32

def test_create_todo_with_custom_values() -> None:
    todo: TodoItem = TodoItem(title="Custom", priority="high", due_date="2024-12-31", done=True)
    assert todo.priority == "high"
    assert todo.due_date == "2024-12-31"
    assert todo.done is True