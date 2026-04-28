import argparse
from pathlib import Path
from .processor import replace_text_in_dir

def run() -> int:
    parser = argparse.ArgumentParser(
        description="Recursively replace text in files within a directory."
    )
    parser.add_argument("directory", type=Path, help="Target directory to search")
    parser.add_argument("search", type=str, help="The string to search for")
    parser.add_argument("replace", type=str, help="The replacement string")
    parser.add_argument(
        "-e", "--ext", 
        type=str, 
        nargs="+", 
        help="Filter by file extensions (e.g., .txt .md)",
        default=None
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Print modified files"
    )

    args = parser.parse_args()

    if not args.directory.is_dir():
        print(f"Error: {args.directory} is not a valid directory.")
        return 1

    result = replace_text_in_dir(
        root_dir=args.directory,
        search_str=args.search,
        replace_str=args.replace,
        extensions=args.ext
    )

    if args.verbose:
        for path in result.modified_paths:
            print(f"Modified: {path}")

    print(f"Finished. Modified {result.files_modified} files. Total replacements: {result.total_replacements}.")
    return 0