from pathlib import Path
from typing import NamedTuple

class ReplaceResult(NamedTuple):
    files_modified: int
    total_replacements: int
    modified_paths: list[Path]

def replace_text_in_file(file_path: Path, search_str: str, replace_str: str) -> int:
    """
    Replaces all occurrences of search_str with replace_str in a specific file.
    Returns the number of replacements made.
    """
    content = file_path.read_text(encoding="utf-8")
    if search_str not in content:
        return 0
    
    new_content = content.replace(search_str, replace_str)
    count = content.count(search_str)
    file_path.write_text(new_content, encoding="utf-8")
    return count

def replace_text_in_dir(
    root_dir: Path, 
    search_str: str, 
    replace_str: str, 
    extensions: list[str] | None = None
) -> ReplaceResult:
    """
    Recursively searches and replaces text in files within the directory.
    """
    modified_paths: list[Path] = []
    total_replacements = 0

    # Walk through directory recursively
    for file_path in root_dir.rglob("*"):
        if not file_path.is_file():
            continue
        
        # Filter by extension if provided
        if extensions and file_path.suffix not in extensions:
            continue

        try:
            count = replace_text_in_file(file_path, search_str, replace_str)
            if count > 0:
                total_replacements += count
                modified_paths.append(file_path)
        except (UnicodeDecodeError, PermissionError) as e:
            print(f"Skipping {file_path}: {e}")

    return ReplaceResult(
        files_modified=len(modified_paths),
        total_replacements=total_replacements,
        modified_paths=modified_paths
    )