from src.database import SnippetDB
from src.utils.formatters import print_snippet
 def run(args) -> None:
    db = SnippetDB()
    try: snippet = db.get(args.id)
        if snippet:
            print_snippet(snippet)
        else:
            print(f"Snippet with ID {args.id} not found.")
    finally:
        db.close()