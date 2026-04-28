import argparse
import sys
from pathlib import Path
from py_replace.core import ReplaceEngine

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search and replace text in a specified file."
    )
    parser.add_argument(
        "search", 
        type=str, 
        help="The text string to search for"
    )
    parser.add_argument(
        "replace", 
        type=str, 
        help="The text string to replace it with"
    )
    parser.add_argument(
        "file", 
        type=Path, 
        help="Path to the target file"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="Show how many replacements would be made without modifying the file"
    )
    parser.add_argument(
        "--verbose", 
        "-v", 
        action="store_true", 
        help="Enable verbose output"
    )

    args = parser.parse_args()

    try:
        engine = ReplaceEngine(args.search, args.replace)
        count = engine.process_file(args.file, dry_run=args.dry_run)

        if args.verbose:
            status = "would be replaced" if args.dry_run else "were replaced"
            print(f"Found {count} occurrences. They {status} in {args.file}.")
        else:
            print(f"Replacements made: {count}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied when accessing {args.file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()