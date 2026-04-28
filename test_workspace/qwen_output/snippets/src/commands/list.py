from src.database import SnippetDB
from src.utils.formatters import print_snippet_list
 def run(args) -> None:
    db = SnippetDB()
    try: snippets = db.list_all()
        print_snippet_list(snippets)
    finally:
        db.close()