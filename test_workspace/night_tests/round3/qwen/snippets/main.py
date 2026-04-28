import sys
from cli import parse_args
from core import count_text, TextMetrics


def main(args: list[str] | None = None) -> None:
    """Entry point for the CLI application."""
    parsed = parse_args(args)

    try:
        metrics: TextMetrics = count_text(parsed.file)
        print(f"Lines:      {metrics.lines}")
        print(f"Words:      {metrics.words}")
        print(f"Characters: {metrics.characters}")

        if parsed.verbose:
            print(f"Processed: {parsed.file.resolve()}")
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()