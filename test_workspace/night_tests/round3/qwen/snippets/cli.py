import argparse
from pathlib import Path
from typing import Optional


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    """Configure and parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Count lines, words, and characters in a text file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Path to the target text file.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output with resolved file path.",
    )
    return parser.parse_args(args)