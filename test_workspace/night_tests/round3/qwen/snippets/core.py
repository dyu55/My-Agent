from pathlib import Path
from typing import NamedTuple


class TextMetrics(NamedTuple):
    lines: int
    words: int
    characters: int


def count_text(file_path: Path) -> TextMetrics:
    """Calculate line, word, and character counts for a given file."""
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    with file_path.open(encoding="utf-8") as fh:
        content = fh.read()

    return TextMetrics(
        lines=len(content.splitlines()),
        words=len(content.split()),
        characters=len(content),
    )