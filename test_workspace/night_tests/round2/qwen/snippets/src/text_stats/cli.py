import argparse
import json
import sys
from pathlib import Path
from text_stats.core import analyze_file, TextStats

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="Count lines, words, and characters in a text file."
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the input text file."
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)."
    )
    return parser.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    """CLI 主入口。"""
    args = parse_args(argv)
    try:
        stats: TextStats = analyze_file(args.input_file)
        if args.output_format == "json":
            print(json.dumps(stats.__dict__))
        else:
            print(f"Lines: {stats.lines}")
            print(f"Words: {stats.words}")
            print(f"Characters: {stats.characters}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())