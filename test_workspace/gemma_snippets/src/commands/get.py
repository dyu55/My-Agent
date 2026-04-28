import argparse
from src.database import Database

def handle_get(args: argparse.Namespace, db: Database):
    snippet = db.get_snippet(args.id)
    if not snippet:
        print(f"Error: Snippet with ID {args.id} not found.")
        return
    
    print(f"--- {snippet.name} ({snippet.language}) ---")
    print(f"Description: {snippet.description}")
    print(f"Tags: {', '.join(snippet.tags)}")
    print("-" * 20)
    print(snippet.content)
    print("-" * 20)