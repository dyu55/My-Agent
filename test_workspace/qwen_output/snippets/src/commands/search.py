from src.database import SnippetDB
from src.utils.formatters import print_snippet_list
 def run(args) -> None:
    db = SnippetDB()
    try: results = db.search(args.query)
        print_snippet_list(results)
    finally:
        db.close()