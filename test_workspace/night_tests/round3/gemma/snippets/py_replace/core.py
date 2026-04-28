from pathlib import Path

class ReplaceEngine:
    """Handles the logic of searching and replacing text in files."""

    def __init__(self, search_text: str, replace_text: str):
        self.search_text = search_text
        self.replace_text = replace_text

    def replace_in_content(self, content: str) -> tuple[str, int]:
        """
        Replaces all occurrences of search_text with replace_text.
        Returns a tuple of (new_content, count_of_replacements).
        """
        count = content.count(self.search_text)
        new_content = content.replace(self.search_text, self.replace_text)
        return new_content, count

    def process_file(self, file_path: Path, dry_run: bool = False) -> int:
        """
        Processes a single file. If dry_run is True, it does not write to disk.
        Returns the number of replacements made.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        new_content, count = self.replace_in_content(content)

        if count > 0 and not dry_run:
            file_path.write_text(new_content, encoding="utf-8")

        return count