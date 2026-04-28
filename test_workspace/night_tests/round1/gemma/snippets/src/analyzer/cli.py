import argparse
import sys
from pathlib import Path
from .core import analyze_text, AnalysisResult

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze text from a file or standard input."
    )
    parser.add_argument(
        "-f", "--file", 
        type=Path, 
        help="Path to the text file to analyze"
    )
    parser.add_argument(
        "-n", "--top", 
        type=int, 
        default=5, 
        help="Number of top frequent words to display (default: 5)"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Enable verbose output"
    )
    return parser.parse_args()

def run_cli() -> None:
    args = parse_args()
    
    try:
        if args.file:
            if not args.file.exists():
                print(f"Error: File {args.file} not found.", file=sys.stderr)
                sys.exit(1)
            content = args.file.read_text(encoding="utf-8")
        elif not sys.stdin.isatty():
            content = sys.stdin.read()
        else:
            print("Error: Please provide a file via -f or pipe text to stdin.", file=sys.stderr)
            sys.exit(1)

        result = analyze_text(content, top_n=args.top)
        
        if args.verbose:
            print(f"--- Analysis Report ---")
            print(f"Total Characters: {result.char_count}")
            print(f"Total Words:      {result.word_count}")
            print(f"Top {args.top} words:")
            for word, freq in result.top_words:
                print(f"  {word}: {freq}")
        else:
            print(f"Words: {result.word_count}, Chars: {result.char_count}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)