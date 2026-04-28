#!/usr/bin/env python3
"""CLI Todo Manager with JSON storage."""

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Optional, Any, TypedDict

STORAGE_PATH = Path.home() / ".todos.json"

class TodoDict(TypedDict):
    id: str
    text: str
    priority: str
    due_date: Optional[str]
    completed: bool

def load_todos() -> list[TodoDict]:
    """Load todos from JSON storage."""
    if not STORAGE_PATH.exists():
        return []
    with open(STORAGE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_todos(todos: list[TodoDict]) -> None:
    """Save todos to JSON storage."""
    with open(STORAGE_PATH, "w", encoding="utf-8") as f:
        json.dump(todos, f, indent=2, ensure_ascii=False)

def cmd_add(args: argparse.Namespace) -> None:
    """Add a new todo item."""
    todos = load_todos()
    new_todo: TodoDict = {
        "id": uuid.uuid4().hex[:8],
        "text": args.text,
        "priority": args.priority,
        "due_date": args.due_date,
        "completed": False,
    }
    todos.append(new_todo)
    save_todos(todos)
    print(f"Added: {new_todo['id']}")

def cmd_list(args: argparse.Namespace) -> None:
    """List todos based on status filter."""
    todos = load_todos()
    if args.status == "pending":
        todos = [t for t in todos if not t["completed"]]
    elif args.status == "completed":
        todos = [t for t in todos if t["completed"]]

    if not todos:
        print("No todos found.")
        return

    for t in todos:
        status_icon = "✅" if t["completed"] else "⬜️"
        due = t["due_date"] or "N/A"
        print(f"[{status_icon}] {t['id']} | {t['text']} | P:{t['priority']} | D:{due}")

def cmd_done(args: argparse.Namespace) -> None:
    """Mark a todo as completed."""
    todos = load_todos()
    for t in todos:
        if t["id"] == args.id:
            t["completed"] = True
            save_todos(todos)
            print(f"Marked {args.id} as done.")
            return
    print(f"Todo {args.id} not found.")

def cmd_delete(args: argparse.Namespace) -> None:
    """Delete a todo by ID."""
    todos = load_todos()
    filtered = [t for t in todos if t["id"] != args.id]
    if len(filtered) < len(todos):
        save_todos(filtered)
        print(f"Deleted {args.id}.")
    else:
        print(f"Todo {args.id} not found.")

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="CLI Todo Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_p = subparsers.add_parser("add", help="Add a new todo")
    add_p.add_argument("text", help="Todo description")
    add_p.add_argument("-p", "--priority", choices=["low", "medium", "high"], default="medium")
    add_p.add_argument("-d", "--due-date", help="Due date (YYYY-MM-DD)", default=None)

    list_p = subparsers.add_parser("list", help="List todos")
    list_p.add_argument("--status", choices=["all", "pending", "completed"], default="all")

    done_p = subparsers.add_parser("done", help="Mark a todo as done")
    done_p.add_argument("id", help="Todo ID")

    del_p = subparsers.add_parser("delete", help="Delete a todo")
    del_p.add_argument("id", help="Todo ID")

    return parser.parse_args()

def main() -> None:
    """Main entry point."""
    args = parse_args()
    match args.command:
        case "add":
            cmd_add(args)
        case "list":
            cmd_list(args)
        case "done":
            cmd_done(args)
        case "delete":
            cmd_delete(args)
        case _:
            print("Unknown command.", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()