"""Cost Tracker - Track and estimate LLM API costs."""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# Pricing per 1M tokens (USD) as of 2024
MODEL_PRICING = {
    # Ollama (local, free but electricity cost estimate)
    "ollama": {
        "default": {"input": 0.0, "output": 0.0, "per_1m_cost": 0.01},  # ~$0.01/M for electricity
    },
    # OpenAI
    "openai": {
        "gpt-4o": {"input": 5.0, "output": 15.0, "per_1m_cost": 20.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60, "per_1m_cost": 0.75},
        "gpt-4-turbo": {"input": 10.0, "output": 30.0, "per_1m_cost": 40.0},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50, "per_1m_cost": 2.0},
    },
    # Anthropic
    "anthropic": {
        "claude-opus-4": {"input": 15.0, "output": 75.0, "per_1m_cost": 90.0},
        "claude-sonnet-4": {"input": 3.0, "output": 15.0, "per_1m_cost": 18.0},
        "claude-haiku-4": {"input": 0.80, "output": 4.0, "per_1m_cost": 4.8},
        "claude-3-opus": {"input": 15.0, "output": 75.0, "per_1m_cost": 90.0},
        "claude-3-sonnet": {"input": 3.0, "output": 15.0, "per_1m_cost": 18.0},
        "claude-3-haiku": {"input": 0.25, "output": 1.25, "per_1m_cost": 1.5},
    },
    # Google
    "google": {
        "gemini-1.5-pro": {"input": 1.25, "output": 5.0, "per_1m_cost": 6.25},
        "gemini-1.5-flash": {"input": 0.075, "output": 0.30, "per_1m_cost": 0.375},
        "gemini-pro": {"input": 0.125, "output": 0.50, "per_1m_cost": 0.625},
    },
}


@dataclass
class APIUsage:
    """Record of a single API call."""
    timestamp: float
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost: float
    success: bool
    error: str | None = None


@dataclass
class CostSummary:
    """Summary of costs over a period."""
    total_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    by_model: dict[str, dict[str, Any]] = field(default_factory=dict)
    by_day: dict[str, float] = field(default_factory=dict)


class CostTracker:
    """
    Track LLM API usage and costs.

    Provides:
    - Per-call tracking
    - Budget alerts
    - Usage reports
    - Cost estimation
    """

    def __init__(
        self,
        state_dir: str | None = None,
        budget_limit: float | None = None,
    ):
        if state_dir is None:
            state_dir = "memory"

        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.usage_file = self.state_dir / "api_usage.json"
        self.budget_limit = budget_limit

        self._usage: list[APIUsage] = []
        self._budget_warned = False

        self._load_usage()

    def _load_usage(self) -> None:
        """Load usage from disk."""
        if self.usage_file.exists():
            try:
                with open(self.usage_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self._usage = [
                    APIUsage(**u) for u in data
                ]
            except (json.JSONDecodeError, TypeError):
                pass

    def _save_usage(self) -> None:
        """Save usage to disk."""
        data = [
            {
                "timestamp": u.timestamp,
                "provider": u.provider,
                "model": u.model,
                "input_tokens": u.input_tokens,
                "output_tokens": u.output_tokens,
                "latency_ms": u.latency_ms,
                "cost": u.cost,
                "success": u.success,
                "error": u.error,
            }
            for u in self._usage
        ]

        with open(self.usage_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def estimate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Estimate cost for a call.

        Args:
            provider: Provider name
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Normalize provider
        provider = provider.lower()

        # Try exact match first
        if provider in MODEL_PRICING:
            models = MODEL_PRICING[provider]
            if model in models:
                pricing = models[model]
                input_cost = (input_tokens / 1_000_000) * pricing["input"]
                output_cost = (output_tokens / 1_000_000) * pricing["output"]
                return input_cost + output_cost

            # Try partial match
            for model_name, pricing in models.items():
                if model_name in model or model in model_name:
                    input_cost = (input_tokens / 1_000_000) * pricing["input"]
                    output_cost = (output_tokens / 1_000_000) * pricing["output"]
                    return input_cost + output_cost

        # Default estimate for unknown models
        # Assume ~$2/M tokens average
        return (input_tokens + output_tokens) / 1_000_000 * 2.0

    def record_call(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool = True,
        error: str | None = None,
    ) -> tuple[float, bool]:
        """
        Record an API call.

        Args:
            provider: Provider name
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            latency_ms: Response latency
            success: Whether call succeeded
            error: Error message if failed

        Returns:
            Tuple of (cost, budget_exceeded)
        """
        cost = self.estimate_cost(provider, model, input_tokens, output_tokens)

        usage = APIUsage(
            timestamp=time.time(),
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost=cost,
            success=success,
            error=error,
        )

        self._usage.append(usage)
        self._save_usage()

        # Check budget
        total_cost = self.get_summary().total_cost
        budget_exceeded = (
            self.budget_limit is not None and
            total_cost > self.budget_limit and
            not self._budget_warned
        )

        if budget_exceeded:
            self._budget_warned = True

        return cost, budget_exceeded

    def get_summary(
        self,
        since: float | None = None,
    ) -> CostSummary:
        """
        Get cost summary.

        Args:
            since: Unix timestamp to filter from (None = all time)

        Returns:
            CostSummary with aggregated data
        """
        usage = self._usage
        if since:
            usage = [u for u in usage if u.timestamp >= since]

        summary = CostSummary()

        for u in usage:
            summary.total_calls += 1
            summary.total_input_tokens += u.input_tokens
            summary.total_output_tokens += u.output_tokens
            summary.total_cost += u.cost
            summary.total_latency_ms += u.latency_ms

            # By model
            if u.model not in summary.by_model:
                summary.by_model[u.model] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                }

            summary.by_model[u.model]["calls"] += 1
            summary.by_model[u.model]["input_tokens"] += u.input_tokens
            summary.by_model[u.model]["output_tokens"] += u.output_tokens
            summary.by_model[u.model]["cost"] += u.cost

            # By day
            day = datetime.fromtimestamp(u.timestamp).strftime("%Y-%m-%d")
            if day not in summary.by_day:
                summary.by_day[day] = 0.0
            summary.by_day[day] += u.cost

        if summary.total_calls > 0:
            summary.avg_latency_ms = summary.total_latency_ms / summary.total_calls

        return summary

    def get_report(self, since: float | None = None) -> str:
        """
        Get a human-readable cost report.

        Args:
            since: Unix timestamp to filter from

        Returns:
            Formatted report string
        """
        summary = self.get_summary(since)

        lines = [
            "=" * 50,
            "LLM Cost Report",
            "=" * 50,
            f"Total API Calls: {summary.total_calls}",
            f"Total Input Tokens: {summary.total_input_tokens:,}",
            f"Total Output Tokens: {summary.total_output_tokens:,}",
            f"Total Cost: ${summary.total_cost:.4f}",
            f"Average Latency: {summary.avg_latency_ms:.0f}ms",
            "",
            "Costs by Model:",
            "-" * 30,
        ]

        for model, data in sorted(
            summary.by_model.items(),
            key=lambda x: x[1]["cost"],
            reverse=True,
        ):
            lines.append(
                f"  {model}: ${data['cost']:.4f} "
                f"({data['calls']} calls, "
                f"{data['input_tokens'] + data['output_tokens']:,} tokens)"
            )

        if summary.by_day:
            lines.extend([
                "",
                "Costs by Day:",
                "-" * 30,
            ])
            for day, cost in sorted(summary.by_day.items(), reverse=True)[:7]:
                lines.append(f"  {day}: ${cost:.4f}")

        if self.budget_limit:
            remaining = self.budget_limit - summary.total_cost
            lines.extend([
                "",
                "=" * 50,
                f"Budget: ${self.budget_limit:.2f}",
                f"Spent: ${summary.total_cost:.2f}",
                f"Remaining: ${remaining:.2f}",
            ])

        return "\n".join(lines)

    def budget_alert(self) -> str | None:
        """
        Check if budget threshold is exceeded.

        Returns:
            Alert message or None if under budget
        """
        if self.budget_limit is None:
            return None

        summary = self.get_summary()
        if summary.total_cost >= self.budget_limit:
            return (
                f"BUDGET ALERT: ${summary.total_cost:.4f} spent "
                f"(limit: ${self.budget_limit:.2f})"
            )

        if summary.total_cost >= self.budget_limit * 0.8:
            return (
                f"BUDGET WARNING: ${summary.total_cost:.4f} spent "
                f"(80% of ${self.budget_limit:.2f} limit)"
            )

        return None

    def reset(self) -> None:
        """Reset all usage data."""
        self._usage = []
        self._budget_warned = False
        self._save_usage()


# Global tracker instance
_global_tracker: CostTracker | None = None


def get_global_tracker(
    budget_limit: float | None = None,
) -> CostTracker:
    """Get or create the global cost tracker."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = CostTracker(budget_limit=budget_limit)
    return _global_tracker


def track_llm_call(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
    success: bool = True,
    error: str | None = None,
) -> tuple[float, bool]:
    """
    Track an LLM call using the global tracker.

    Returns:
        Tuple of (cost, budget_exceeded)
    """
    tracker = get_global_tracker()
    return tracker.record_call(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        success=success,
        error=error,
    )
