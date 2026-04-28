import argparse
from src.database import Database
from src.models import Snippet

def handle_add(args: argparse.Namespace, db: Database):
    tags = args.tags.split(",") if args.tags else []
    snippet = Snippet(
        name=args.name,
        language=args.language,
        content=args.content,
        description=args.description,
        tags=[t.strip() for t in tags]
    )
    snippet_id = db.add_snippet(snippet)
    print(f"Successfully added snippet with ID: {snippet_id}")