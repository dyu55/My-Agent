import argparse
import sys
from typing import Any
from src.models import TodoItem
from src.commands import add
from src.commands import list as list_commands
from src.commands import done
from src.commands import delete

def build_parser() -> argparse.ArgumentParser:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(description="CLI Todo Manager")
    subparsers: argparse._SubParsersAction[str] = parser.add_subparsers(dest="command", required=True)

    add_parser: argparse.ArgumentParser = subparsers.add_parser("add", help="Add a new todo")
    add_parser.add_argument("title", type=str, help="Todo title")
    add_parser.add_argument("--priority", choices=["low", "medium", "high"], default="medium", type=str)
    add_parser.add_argument("--due-date", type=str, default=None)

    subparsers.add_parser("list", help="List all todos")

    done_parser: argparse.ArgumentParser = subparsers.add_parser("done", help="Mark a todo as done")
    done_parser.add_argument("id", type=str, help="Todo ID")

    delete_parser: argparse.ArgumentParser = subparsers.add_parser("delete", help="Delete a todo")
    delete_parser.add_argument("id", type=str, help="Todo ID")

    return parser

def main() -> None:
    parser: argparse.ArgumentParser = build_parser()
    args: argparse.Namespace = parser.parse_args()

    match args.command:
        case "add":
            result: TodoItem = add.add(title=args.title, priority=args.priority, due_date=args.due_date)
            print(f"Added: {result.id} - {result.title}")
        case "list":
            todos: list[TodoItem] = list_commands.list_todos()
            for t in todos:
                status: str = "Done" if t.done else "Pending"
                print(f"[{status}] {t.id} | {t.title} | Priority: {t.priority} | Due: {t.due_date}")
        case "done":
            result: TodoItem | None = done.mark_done(args.id)
            if result:
                print(f"Marked done: {result.id}")
            else:
                print("Todo not found", file=sys.stderr)
                sys.exit(1)
        case "delete":
            result: TodoItem | None = delete.delete_todo(args.id)
            if result:
                print(f"Deleted: {result.id}")
            else:
                print("Todo not found", file=sys.stderr)
                sys.exit(1)

if __name__ == "__main__":
    main()