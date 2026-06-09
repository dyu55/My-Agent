#!/usr/bin/env python3
"""Agent Performance Benchmark

Measures:
  1. Task completion rate — does the agent produce working code?
  2. Token efficiency — how many LLM calls per task?
  3. Speed — wall-clock time per task
  4. Small model optimization — do short prompts help?
  5. Cache effectiveness — hit rate across runs

Usage:
  python benchmark_agent.py                        # Run all benchmarks
  python benchmark_agent.py --model qwen3:8b       # Test specific model
  python benchmark_agent.py --suite quick           # Quick smoke test
  python benchmark_agent.py --suite full            # Full benchmark suite
  python benchmark_agent.py --compare qwen3:8b,qwen3:26b  # Compare models
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# ============================================================
# Test Definitions
# ============================================================

QUICK_TASKS = [
    {
        "id": "hello-world",
        "name": "Hello World Script",
        "task": 'Create a file hello.py that prints "Hello, World!" and has a main() function.',
        "verify_file": "hello.py",
        "verify_contains": ["Hello", "def main"],
        "max_time_seconds": 60,
    },
    {
        "id": "simple-function",
        "name": "Math Utility",
        "task": "Create math_utils.py with functions: add(a,b), subtract(a,b), multiply(a,b), divide(a,b). Include type hints and handle division by zero.",
        "verify_file": "math_utils.py",
        "verify_contains": ["def add", "def divide"],
        "verify_any": [["ZeroDivisionError", "b == 0", "denominator == 0", "raise ValueError"]],
        "max_time_seconds": 90,
    },
    {
        "id": "data-class",
        "name": "Data Model",
        "task": "Create models.py with a User dataclass that has: name (str), email (str), age (int, optional). Include a validate() method that checks email format.",
        "verify_file": "models.py",
        "verify_contains": ["@dataclass", "class User", "def validate"],
        "max_time_seconds": 90,
    },
]

FULL_TASKS = QUICK_TASKS + [
    {
        "id": "cli-tool",
        "name": "CLI Tool",
        "task": "Create a CLI todo app in todo.py. Support: add <task>, list, done <id>, delete <id>. Store tasks in a JSON file. Use argparse.",
        "verify_file": "todo.py",
        "verify_contains": ["argparse", "def add", "def list", "json"],
        "max_time_seconds": 120,
    },
    {
        "id": "file-processor",
        "name": "File Processor",
        "task": "Create word_count.py that reads a text file and outputs: line count, word count, char count, most common words (top 5). Handle file not found gracefully.",
        "verify_file": "word_count.py",
        "verify_contains": ["def count", "open(", "FileNotFoundError"],
        "max_time_seconds": 120,
    },
    {
        "id": "api-wrapper",
        "name": "API Wrapper",
        "task": "Create api_client.py with a class APIClient that wraps HTTP GET/POST requests using requests library. Include: base_url config, timeout, retry logic (3 retries with exponential backoff), and JSON response parsing.",
        "verify_file": "api_client.py",
        "verify_contains": ["class APIClient", "def get", "def post"],
        "verify_any": [["retry", "retries", "backoff", "attempt"]],
        "max_time_seconds": 120,
    },
    {
        "id": "test-generation",
        "name": "Test Generation",
        "task": "Create a file calculator.py with a Calculator class (add, subtract, multiply, divide, power). Then create test_calculator.py with pytest tests covering all methods including edge cases.",
        "verify_file": "test_calculator.py",
        "verify_contains": ["import pytest", "def test_", "Calculator"],
        "max_time_seconds": 150,
    },
    {
        "id": "refactor-task",
        "name": "Code Refactoring",
        "task": (
            "Create messy_code.py with this exact content, then create clean_code.py with the refactored version:\n\n"
            "```python\n"
            "def process(d):\n"
            "    r = []\n"
            "    for i in d:\n"
            "        if i['age'] > 18 and i['active'] == True:\n"
            "            n = i['name'].upper()\n"
            "            e = i['email']\n"
            "            r.append({'name': n, 'email': e, 'adult': True})\n"
            "    return r\n"
            "```\n\n"
            "Refactored version should: use list comprehension, add type hints, use constants, add docstring, handle missing keys."
        ),
        "verify_file": "clean_code.py",
        "verify_contains": ["def process"],
        "verify_any": [
            ["TypedDict", "Dict", "dict[str", "Dict[str", "dataclass"],
            ["List", "list[", "List["],
        ],
        "max_time_seconds": 120,
    },
]


# ============================================================
# Benchmark Runner
# ============================================================


@dataclass
class TaskResult:
    """Result of a single benchmark task."""
    task_id: str
    task_name: str
    passed: bool
    duration_seconds: float
    llm_calls: int
    error: str | None = None
    file_created: bool = False
    content_matches: bool = False
    verification_details: list[str] = field(default_factory=list)


@dataclass
class BenchmarkResult:
    """Aggregated benchmark results."""
    model: str
    provider: str
    timestamp: str
    total_tasks: int
    passed: int
    failed: int
    avg_duration: float
    total_llm_calls: int
    task_results: list[TaskResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total_tasks if self.total_tasks > 0 else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "timestamp": self.timestamp,
            "total_tasks": self.total_tasks,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": f"{self.pass_rate:.1%}",
            "avg_duration": f"{self.avg_duration:.1f}s",
            "total_llm_calls": self.total_llm_calls,
            "tasks": [
                {
                    "id": tr.task_id,
                    "name": tr.task_name,
                    "passed": tr.passed,
                    "duration": f"{tr.duration_seconds:.1f}s",
                    "llm_calls": tr.llm_calls,
                    "error": tr.error,
                    "details": tr.verification_details,
                }
                for tr in self.task_results
            ],
        }


def verify_task(task_def: dict, workspace: Path) -> tuple[bool, list[str]]:
    """Verify that a task produced the expected output."""
    details = []
    verify_name = task_def["verify_file"]

    # Search for the file in workspace (may be in subdirectory)
    matches = list(workspace.rglob(verify_name))
    file_path = matches[0] if matches else (workspace / verify_name)

    # Check file exists
    if not file_path.exists():
        details.append(f"FAIL: {verify_name} not created")
        return False, details

    content = file_path.read_text()
    details.append(f"OK: {task_def['verify_file']} created ({len(content)} chars)")

    # Check required content
    all_match = True
    for keyword in task_def.get("verify_contains", []):
        if keyword in content:
            details.append(f"OK: contains '{keyword}'")
        else:
            details.append(f"FAIL: missing '{keyword}'")
            all_match = False

    # Check "any-of" groups — at least one keyword per group must match
    for group in task_def.get("verify_any", []):
        if any(kw in content for kw in group):
            matched = next(kw for kw in group if kw in content)
            details.append(f"OK: contains '{matched}' (from group)")
        else:
            details.append(f"FAIL: missing any of {group}")
            all_match = False

    # Try to parse the Python file for syntax errors
    try:
        compile(content, str(file_path), "exec")
        details.append("OK: valid Python syntax")
    except SyntaxError as e:
        details.append(f"FAIL: syntax error — {e}")
        all_match = False

    return all_match, details


def run_single_task(task_def: dict, model: str, provider: str,
                    base_url: str, api_key: str | None) -> TaskResult:
    """Run a single benchmark task in an isolated workspace."""
    task_id = task_def["id"]
    task_name = task_def["name"]
    workspace = Path(f"_benchmark_workspaces/{task_id}_{int(time.time())}")
    workspace.mkdir(parents=True, exist_ok=True)

    print(f"  ▶ {task_name}...", end="", flush=True)
    start = time.time()

    try:
        from agent.engine import AgentConfig, AgentEngine

        llm_call_count = 0

        def on_progress(phase: str, detail: str, elapsed: float):
            nonlocal llm_call_count
            if phase == "act":
                llm_call_count += 1

        config = AgentConfig(
            workspace=workspace,
            model=model,
            provider=provider,
            base_url=base_url,
            api_key=api_key,
            trace_enabled=False,
            progress_callback=on_progress,
        )

        agent = AgentEngine(config)
        agent.run(task_def["task"])

        # Verify output
        passed, details = verify_task(task_def, workspace)
        duration = time.time() - start

        status = "PASS" if passed else "FAIL"
        print(f" {status} ({duration:.1f}s, {llm_call_count} LLM calls)")

        return TaskResult(
            task_id=task_id,
            task_name=task_name,
            passed=passed,
            duration_seconds=duration,
            llm_calls=llm_call_count,
            file_created=(workspace / task_def["verify_file"]).exists(),
            content_matches=passed,
            verification_details=details,
        )

    except Exception as e:
        duration = time.time() - start
        print(f" ERROR ({duration:.1f}s): {e}")
        return TaskResult(
            task_id=task_id,
            task_name=task_name,
            passed=False,
            duration_seconds=duration,
            llm_calls=0,
            error=str(e),
        )
    finally:
        # Clean up workspace
        shutil.rmtree(workspace, ignore_errors=True)


def resolve_provider_config(provider: str, model: str, base_url: str, api_key: str | None):
    """Resolve provider config from args and environment variables."""
    provider = provider.lower()

    if provider == "mimo":
        base_url = base_url or os.getenv("MIMO_BASE_URL", "https://token-plan-sgp.xiaomimimo.com/v1")
        api_key = api_key or os.getenv("MIMO_API_KEY")
        model = model or os.getenv("MIMO_MODEL", "mimo-v2.5")
    elif provider == "deepseek":
        base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    elif provider == "openai":
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        model = model or "gpt-4o"
    elif provider == "ollama":
        base_url = base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        model = model or os.getenv("MODEL_NAME", "qwen3.5:9b")
    elif provider == "gemini":
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        model = model or os.getenv("GEMINI_MODEL", "gemma-4-31b-it")

    return model, provider, base_url, api_key


def run_benchmark(
    model: str | None = None,
    provider: str = "ollama",
    base_url: str | None = None,
    api_key: str | None = None,
    suite: str = "quick",
) -> BenchmarkResult:
    """Run the full benchmark suite."""
    tasks = QUICK_TASKS if suite == "quick" else FULL_TASKS

    # Resolve provider config from environment
    model, provider, base_url, api_key = resolve_provider_config(provider, model, base_url, api_key)

    print(f"\n{'='*60}")
    print(f"  Agent Benchmark: {model} ({provider})")
    print(f"  Base URL: {base_url}")
    print(f"  Suite: {suite} ({len(tasks)} tasks)")
    print(f"{'='*60}\n")

    results = []
    for task_def in tasks:
        result = run_single_task(task_def, model, provider, base_url, api_key)
        results.append(result)

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    avg_dur = sum(r.duration_seconds for r in results) / total if total > 0 else 0
    total_calls = sum(r.llm_calls for r in results)

    benchmark = BenchmarkResult(
        model=model,
        provider=provider,
        timestamp=datetime.now().isoformat(),
        total_tasks=total,
        passed=passed,
        failed=total - passed,
        avg_duration=avg_dur,
        total_llm_calls=total_calls,
        task_results=results,
    )

    # Print summary
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} passed ({benchmark.pass_rate:.0%})")
    print(f"  Avg duration: {avg_dur:.1f}s")
    print(f"  Total LLM calls: {total_calls}")
    print(f"{'='*60}")

    return benchmark


def compare_models(models: list[str], suite: str = "quick"):
    """Run benchmark on multiple models and compare."""
    results = []
    for model in models:
        print(f"\n{'#'*60}")
        print(f"  Testing: {model}")
        print(f"{'#'*60}")
        benchmark = run_benchmark(model=model, suite=suite)
        results.append(benchmark)

    # Print comparison table
    print(f"\n{'='*60}")
    print(f"  COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"{'Model':<25} {'Pass Rate':>10} {'Avg Time':>10} {'LLM Calls':>10}")
    print(f"{'-'*55}")
    for r in results:
        print(f"{r.model:<25} {r.pass_rate:>9.0%} {r.avg_duration:>9.1f}s {r.total_llm_calls:>10}")

    # Save results
    report = {
        "timestamp": datetime.now().isoformat(),
        "suite": suite,
        "models": [r.to_dict() for r in results],
    }
    report_path = f"benchmark_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  Report saved: {report_path}")


# ============================================================
# CLI
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="Agent Performance Benchmark")
    parser.add_argument("--model", default=None, help="Model to test (default: from .env)")
    parser.add_argument("--provider", default="ollama", help="Provider (ollama/openai/anthropic/mimo/deepseek)")
    parser.add_argument("--base-url", default=None, help="API base URL (default: from .env)")
    parser.add_argument("--api-key", default=None, help="API key (default: from .env)")
    parser.add_argument("--suite", choices=["quick", "full"], default="quick",
                        help="Benchmark suite: quick (3 tasks) or full (8 tasks)")
    parser.add_argument("--compare", default=None,
                        help="Comma-separated models to compare (e.g., qwen3:8b,qwen3:26b)")
    args = parser.parse_args()

    if args.compare:
        models = [m.strip() for m in args.compare.split(",")]
        compare_models(models, suite=args.suite)
    else:
        benchmark = run_benchmark(
            model=args.model,
            provider=args.provider,
            base_url=args.base_url,
            api_key=args.api_key,
            suite=args.suite,
        )
        report_path = f"benchmark_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w") as f:
            json.dump(benchmark.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\n  Report saved: {report_path}")


if __name__ == "__main__":
    main()
