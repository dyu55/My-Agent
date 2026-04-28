import argparse
from src.database import Database
from src.utils.formatters import format_table

def handle_search(args: argparse.Namespace, db: Database):
    results = db.search_snippets(args.query)
    rows = [[s.id, s.name, s.language] for s in results]
    print(format_table(["ID", "Name", "Language"], rows))