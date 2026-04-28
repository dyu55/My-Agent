import argparse
from src.database import Database
from src.utils.formatters import format_table

def handle_list(args: argparse.Namespace, db: Database):
    snippets = db.list_snippets()
    rows = [[s.id, s.name, s.language, ",".join(s.tags)] for s in snippets]
    print(format_table(["ID", "Name", "Language", "Tags"], rows))