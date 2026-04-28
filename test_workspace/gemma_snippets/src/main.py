import argparse
import sys
from src.database import Database
from src.commands.add import handle_add
from src.commands.list import handle_list
from src.commands.get import handle_get
from src.commands.edit import handle_edit
from src.commands.delete import handle_delete
from src.commands.search import handle_search

def main():
    parser = argparse.ArgumentParser(description="CLI Code Snippet Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Add
    parser_add = subparsers.add_parser("add", help="Add a new snippet")
    parser_add.add_argument("name", help="Snippet name")
    parser_add.add_argument("language", help="Programming language")
    parser_add.add_argument("content", help="Code content")
    parser_add.add_argument("description", help="Brief description")
    parser_add.add_argument("tags", help="Comma separated tags")
    parser_add.set_defaults(func=handle_add)

    # List
    parser_list = subparsers.add_parser("list", help="List all snippets")
    parser_list.set_defaults(func=handle_list)

    # Get
    parser_get = subparsers.add_parser("get", help="Get a specific snippet")
    parser_get.add_argument("id", type=int, help="Snippet ID")
    parser_get.set_defaults(func=handle_get)

    # Edit
    parser_edit = subparsers.add_parser("edit", help="Edit a snippet")
    parser_edit.add_argument("id", type=int, help="Snippet ID")
    parser_edit.add_argument("--name", help="New name")
    parser_edit.add_argument("--language", help="New language")
    parser_edit.add_argument("--content", help="New content")
    parser_edit.add_argument("--description", help="New description")
    parser_edit.add_argument("--tags", help="New comma separated tags")
    parser_edit.set_defaults(func=handle_edit)

    # Delete
    parser_delete = subparsers.add_parser("delete", help="Delete a snippet")
    parser_delete.add_argument("id", type=int, help="Snippet ID")
    parser_delete.set_defaults(func=handle_delete)

    # Search
    parser_search = subparsers.add_parser("search", help="Search snippets")
    parser_search.add_argument("query", help="Search keyword")
    parser_search.set_defaults(func=handle_search)

    args = parser.parse_args()
    db = Database()
    
    try:
        args.func(args, db)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()