"""Core statistical calculation logic."""


def calculate_stats(numbers: list[float]) -> dict[str, float]:
    """Calculate sum, mean, min, max, and count for a list of numbers."""
    if not numbers:
        raise ValueError("List of numbers cannot be empty")
    total = sum(numbers)
    count = len(numbers)
    return {
        "sum": total,
        "mean": total / count,
        "min": min(numbers),
        "max": max(numbers),
        "count": count,
    }


def format_result(stats: dict[str, float], fmt: str = "text") -> str:
    """Format the statistics dictionary into the requested string representation."""
    match fmt:
        case "json":
            import json
            return json.dumps(stats, indent=2)
        case "csv":
            headers = ",".join(stats.keys())
            values = ",".join(str(v) for v in stats.values())
            return f"{headers}\n{values}"
        case _:
            lines = [f"{k}: {v:.2f}" for k, v in stats.items()]
            return "\n".join(lines)