import argparse
import sys
from src.commands import add, list as list_cmd, get, edit, delete, search

def main() -> None:
    parser = argparse.ArgumentParser(description="CLI Code Snippet Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    add_parser = subparsers.add_parser("add", help="Add a new snippet")
    add_parser.add_argument("--name", "-n", required=True, help="Snippet name")
    add_parser.add_argument("--language", "-l", required=True, help="Programming language")
    add_parser.add_argument("--content", "-c", required=True, help="Code content")
    add_parser.add_argument("--description", "-d", default="", help="Description")
    add_parser.add_argument("--tags", "-t", default="", help="Comma-separated tags")

    subparsers.add_parser("list", help="List all snippets")

    get_parser = subparsers.add_parser("get", help="Get a snippet by ID")
    get_parser.add_argument("id", type=int, help="Snippet ID")

    edit_parser = subparsers.add_parser("edit", help="Edit a snippet")
    edit_parser.add_argument("id", type=int, help="Snippet ID")
    edit_parser.add_argument("--name", "-n", help="New name")
    edit_parser.add_argument("--language", "-l", help="New language")
    edit_parser.add_argument("--content", "-c", help="New content")
    edit_parser.add_argument("--description", "-d", help="New description")
    edit_parser.add_argument("--tags", "-t", help="New comma-separated tags")

    delete_parser = subparsers.add_parser("delete", help="Delete a snippet")
    delete_parser.add_argument("id", type=int, help="Snippet ID")

    search_parser = subparsers.add_parser("search", help="Search snippets")
    search_parser.add_argument("query", help="Search query")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "add": add.run,
        "list": list_cmd.run,
        "get": get.run,
        "edit": edit.run,
        "delete": delete.run,
        "search": search.run,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
