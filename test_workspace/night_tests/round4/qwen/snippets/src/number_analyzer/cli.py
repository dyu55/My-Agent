"""Command-line interface argument parsing and execution."""

import argparse
import sys
from .core import calculate_stats, format_result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="number-analyzer",
        description="Calculate basic statistics for a list of numbers."
    )
    parser.add_argument(
        "numbers",
        type=float,
        nargs="+",
        help="One or more numbers to analyze."
    )
    parser.add_argument(
        "-f", "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format (default: text)."
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Main entry point for the CLI."""
    args = parse_args(argv)
    try:
        stats = calculate_stats(args.numbers)
        result = format_result(stats, args.format)
        print(result)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)