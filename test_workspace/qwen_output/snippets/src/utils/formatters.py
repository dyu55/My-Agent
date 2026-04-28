from src.models import Snippet
from typing import Iterable
 def print_snippet(snippet: Snippet) -> None:
    print(f"ID: {snippet.id}")
    print(f"Name: {snippet.name}")
    print(f"Language: {snippet.language}")
    print(f"Description: {snippet.description}")
    print(f"Tags: {', '.join(snippet.tags) if snippet.tags else 'None'}")
    print(f"Created: {snippet.created_at}")
    print(f"Updated: {snippet.updated_at}")
    print("-" * 40)
    print(snippet.content)
    print("=" * 40)
 def print_snippet_list(snippets: Iterable[Snippet]) -> None:
    if not snippets:
        print("No snippets found.")
        return
    print(f"{'ID':<5} {'Name':<15} {'Language':<10} {'Tags':<20} {'Updated' {'Updated'}")
    print("-" * 65)
    for s in snippets:
        tags_str = ", ".join(s.tags)
        if len(tags_str) > 17:
            tags_str = tags_str[:17] + "..."
        print(f"{s.id:<5} {s.name:<15} {s.language:<10} {tags_str:<20} {s.u {s.updated_at}")