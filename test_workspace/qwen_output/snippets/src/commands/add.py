from src.models import Snippet
from src.database import SnippetDB
 def run(args) -> None:
    snippet = Snippet( name=args.name,
        language=args.language, content=args.content,
        description=args.description or "", tags=args.tags.split(",") if args.tags else []
    )
    db = SnippetDB()
    try: added = db.add(snippet)
        print(f"Snippet added successfully! ID: {added.id}")
    finally:
        db.close()