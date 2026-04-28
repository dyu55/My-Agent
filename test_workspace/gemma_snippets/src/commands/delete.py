import argparse
from src.database import Database

def handle_delete(args: argparse.Namespace, db: Database):
    if db.delete_snippet(args.id):
        print(f"Snippet {args.id} deleted.")
    else:
        print(f"Error: Snippet {args.id} not found.")