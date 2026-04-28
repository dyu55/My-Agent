import argparse
import sys
from typing import List
from models import TodoItem
from storage import TodoStorage

def main():
    parser = argparse.ArgumentParser(description="CLI Todo Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new todo")
    add_parser.add_argument("task", type=str, help="The task description")
    add_parser.add_argument("-p", "--priority", type=str, default="Medium", help="Priority (Low, Medium, High)")
    add_parser.add_argument("-d", "--due", type=str, help="Due date (YYYY-MM-DD)")

    # List command
    subparsers.add_parser("list", help="List all todos")

    # Done command
    done_parser = subparsers.add_parser("done", help="Mark a todo as completed")
    done_parser.add_argument("id", type=int, help="The ID of the todo to complete")

    # Delete command
    del_parser = subparsers.add_parser("delete", help="Delete a todo")
    del_parser.add_argument("id", type=int, help="The ID of the todo to delete")

    args = parser.parse_args()
    storage = TodoStorage()
    todos = storage.load()

    if args.command == "add":
        new_id = max([t.id for t in todos], default=0) + 1
        item = TodoItem(id=new_id, task=args.task, priority=args.priority, due_date=args.due)
        todos.append(item)
        storage.save(todos)
        print(f"Added todo #{new_id}")

    elif args.command == "list":
        if not todos:
            print("No todos found.")
            return
        print(f"{'ID':<4} {'Status':<10} {'Priority':<10} {'Due':<12} {'Task'}")
        print("-" * 50)
        for t in todos:
            status = "[X]" if t.completed else "[ ]"
            due = t.due_date if t.due_date else "N/A"
            print(f"{t.id:<4} {status:<10} {t.priority:<10} {due:<12} {t.task}")

    elif args.command == "done":
        found = False
        for t in todos:
            if t.id == args.id:
                t.completed = True
                found = True
                break
        if found:
            storage.save(todos)
            print(f"Todo #{args.id} marked as done.")
        else:
            print(f"Error: Todo #{args.id} not found.")

    elif args.command == "delete":
        original_len = len(todos)
        todos = [t for t in todos if t.id != args.id]
        if len(todos) < original_len:
            storage.save(todos)
            print(f"Todo #{args.id} deleted.")
        else:
            print(f"Error: Todo #{args.id} not found.")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()