import argparse
import sys
from .core import TextProcessor

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TextProcessor CLI: A tool to analyze and transform text."
    )
    
    parser.add_argument(
        "-i", "--input", 
        type=str, 
        help="Input text string. If not provided, reads from a file via --file."
    )
    parser.add_argument(
        "-f", "--file", 
        type=str, 
        help="Path to the text file to process."
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Count command
    subparsers.add_parser("count", help="Count words in the text")

    # Transform command
    transform_parser = subparsers.add_parser("transform", help="Transform text case")
    transform_parser.add_argument(
        "--mode", 
        choices=["upper", "lower"], 
        required=True, 
        help="Case transformation mode"
    )

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for a keyword")
    search_parser.add_argument(
        "keyword", 
        type=str, 
        help="The keyword to search for"
    )

    return parser.parse_args()

def main() -> None:
    args = parse_args()
    
    # Determine input source
    content: str | None = None
    if args.input:
        content = args.input
    elif args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: File {args.file} not found.", file=sys.stderr)
            sys.exit(1)
    
    if content is None:
        print("Error: You must provide either --input or --file.", file=sys.stderr)
        sys.exit(1)

    processor = TextProcessor(content)

    try:
        if args.command == "count":
            print(f"Word count: {processor.count_words()}")
        elif args.command == "transform":
            print(processor.transform_case(args.mode))
        elif args.command == "search":
            results = processor.find_keyword(args.keyword)
            if results:
                print(f"Keyword found at indices: {results}")
            else:
                print("Keyword not found.")
        else:
            print("Error: No command specified. Use -h for help.")
            sys.exit(1)
    except Exception as e:
        print(f"Runtime Error: {e}", file=sys.stderr)
        sys.exit(1)