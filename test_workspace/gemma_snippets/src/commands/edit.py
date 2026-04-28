import argparse
from src.database import Database

def handle_edit(args: argparse.Namespace, db: Database):
    updates = {}
    if args.name: updates['name'] = args.name
    if args.language: updates['language'] = args.language
    if args.content: updates['content'] = args.content
    if args.description: updates['description'] = args.description
    if args.tags: updates['tags'] = [t.strip() for t in args.tags.split(",")]
    
    if not updates:
        print("No updates provided.")
        return
        
    if db.update_snippet(args.id, updates):
        print(f"Snippet {args.id} updated successfully.")
    else:
        print(f"Error: Snippet {args.id} not found.")