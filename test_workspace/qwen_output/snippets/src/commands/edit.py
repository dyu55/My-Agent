from src.database import SnippetDB
from src.utils.formatters import print_snippet
 def run(args) -> None:
    db = SnippetDB()
    try: snippet = db.get(args.id)
        if not snippet:
            print(f"Snippet with ID {args.id} not found.")
            return
 if args.name is not None:
            snippet.name = args.name
        if args.language is not None:
            snippet.language = args.language
        if args.content is not None:
            snippet.content = args.content
        if args.description is not None:
            snippet.description = args.description
        if args.tags is not None:
            snippet.tags = args.tags.split(",")
 updated = db.update(snippet)
        if updated:
            print(f"Snippet updated successfully! ID: {updated.id}")
            print_snippet(updated)
    finally:
        db.close()