# CLI Todo Manager

A simple, type-safe command-line todo manager built with Python 3.10+.

## Installation

Install dependencies:
```bash
pip install -e .
```

## Usage

```bash
# Add a todo
todo add "Buy groceries" --priority high --due-date 2024-12-31

# List todos
todo list

# Mark a todo as done
todo done <todo-id>

# Delete a todo
todo delete <todo-id>
```

## Testing

Run tests with pytest:
```bash
pytest