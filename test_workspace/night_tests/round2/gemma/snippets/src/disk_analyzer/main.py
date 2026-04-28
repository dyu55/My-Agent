import argparse
import sys
from pathlib import Path
from disk_analyzer.core import DiskAnalyzer

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze disk usage of a directory and find the largest items."
    )
    parser.add_argument(
        "path", 
        type=str, 
        help="The directory path to analyze"
    )
    parser.add_argument(
        "-n", "--limit", 
        type=int, 
        default=10, 
        help="Limit the number of top largest items to display (default: 10)"
    )
    parser.add_argument(
        "-h", "--human", 
        action="store_true", 
        help="Display sizes in human-readable format"
    )

    args = parser.parse_args()
    root_path = Path(args.path)

    if not root_path.exists() or not root_path.is_dir():
        print(f"Error: The path {args.path} is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    analyzer = DiskAnalyzer()
    
    print(f"Analyzing: {root_path.absolute()}")
    total_size = analyzer.get_size(root_path)
    
    display_total = analyzer.format_size(total_size) if args.human else total_size
    print(f"Total Size: {display_total}")
    print("-" * 40)
    print(f"{'Item':<30} {'Size':<10}")
    print("-" * 40)

    for item, size in analyzer.list_top_items(root_path, args.limit):
        display_size = analyzer.format_size(size) if args.human else size
        print(f"{item.name:<30} {display_size:<10}")

if __name__ == "__main__":
    main()