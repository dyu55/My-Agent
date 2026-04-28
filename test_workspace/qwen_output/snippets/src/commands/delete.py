from src.database import SnippetDB
 def run(args) -> None:
    db = SnippetDB()
    try: success = db.delete(args.id)
        if success:
            print(f"Snippet {args.id} deleted successfully.")
        else:
            print(f"Snippet with ID {args.id} not found.")
    finally:
        db.close()