#!/usr/bin/env python3
"""
Claude Model Test Runner
Tests multiple Claude models via ccswitch or direct API

Usage:
    python3 tests/claude_test.py --model claude-sonnet-4-6 --output results_sonnet.json
    python3 tests/claude_test.py --model claude-haiku-4-5 --output results_haiku.json
"""

import argparse
import json
import time
import sys
import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
import urllib.request
import urllib.error


@dataclass
class TestResult:
    test_id: str
    category: str
    task: str
    prompt: str
    response: str
    success: bool = False
    response_time_ms: float = 0
    token_count: int = 0
    token_speed: float = 0
    error: str | None = None


@dataclass
class TestSummary:
    model: str
    start_time: str
    end_time: str | None = None
    total_duration_hours: float = 0
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    success_rate: float = 0
    avg_response_time_ms: float = 0
    categories: dict = field(default_factory=dict)


class ClaudeProvider:
    def __init__(self, base_url: str, api_key: str, model: str = "claude-sonnet-4-6"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model

    def chat(self, prompt: str, **kwargs) -> str:
        url = f"{self.base_url}/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048
        }

        max_retries = 5
        retry_delay = 5

        for attempt in range(max_retries):
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode('utf-8'),
                headers=headers,
                method='POST'
            )

            try:
                with urllib.request.urlopen(req, timeout=120) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    return result["content"][0]["text"]
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print(f"    Rate limited, waiting {retry_delay}s... (attempt {attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    raise Exception(f"HTTP {e.code}: {e.read().decode('utf-8')}")
            except Exception as e:
                raise Exception(f"Request failed: {e}")

        raise Exception("Max retries exceeded")


class ClaudeTestRunner:
    def __init__(self, model: str, base_url: str, api_key: str):
        self.model = model
        self.results: list[TestResult] = []
        self.start_time = datetime.now().isoformat()
        self.summary = TestSummary(model=model, start_time=self.start_time)

        print(f"Testing model: {model}")
        self.provider = ClaudeProvider(base_url, api_key, model)

    def run_test(self, test_id: str, category: str, prompt: str) -> TestResult:
        print(f"  [{category}] {test_id}: {prompt[:50]}...", flush=True)

        start = time.time()
        result = TestResult(
            test_id=test_id, category=category, task=test_id,
            prompt=prompt, response=""
        )

        try:
            response = self.provider.chat(prompt)
            result.response = response
            result.success = True
        except Exception as e:
            result.error = str(e)
            result.success = False
            print(f"    ERROR: {str(e)[:80]}")

        end = time.time()
        result.response_time_ms = (end - start) * 1000
        result.token_count = len(result.response) // 4
        if result.response_time_ms > 0:
            result.token_speed = (result.token_count / result.response_time_ms) * 1000

        return result

    def _validate_json(self, response: str) -> bool:
        import re
        json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', response)
        if json_match:
            try:
                json.loads(json_match.group())
                return True
            except:
                return False
        return False

    def run_tests(self) -> TestSummary:
        print("\n" + "="*60)
        print("PHASE 1: AGENT CORE LOOP")
        print("="*60)

        results = []

        # Plan Phase (3 tests)
        print("\n1.1 Plan")
        for test_id, prompt in [
            ("plan_01", 'Create a JSON plan to build a calculator with add, subtract, multiply, divide.'),
            ("plan_02", 'Design a web scraper in 5 steps with dependencies.'),
            ("plan_03", 'Plan a REST API for a blog system.'),
        ]:
            result = self.run_test(test_id, "Plan", prompt)
            result.success = self._validate_json(result.response)
            results.append(result)

        # Act Phase (3 tests)
        print("\n1.2 Act")
        for test_id, prompt in [
            ("act_01", 'Generate JSON to write "Hello World" to hello.txt'),
            ("act_02", 'Generate JSON array for Python project structure.'),
            ("act_03", 'Generate JSON for git init, add, commit workflow.'),
        ]:
            result = self.run_test(test_id, "Act", prompt)
            result.success = self._validate_json(result.response)
            results.append(result)

        # Reflect Phase (3 tests)
        print("\n1.3 Reflect")
        for test_id, prompt in [
            ("reflect_01", 'Analyze: "FileNotFoundError: data.txt". JSON with root cause and fix.'),
            ("reflect_02", 'Test failed: AssertionError 200 vs 401. Flaky or real bug?'),
            ("reflect_03", 'Error: "ModuleNotFoundError: requests". Fix in JSON.'),
        ]:
            result = self.run_test(test_id, "Reflect", prompt)
            results.append(result)

        print("\n" + "="*60)
        print("PHASE 2: TOOL SYSTEM")
        print("="*60)

        # File Tools (3 tests)
        print("\n2.1 File")
        for test_id, prompt in [
            ("file_write", 'Write Python script to read CSV. JSON with code.'),
            ("file_edit", 'Edit script to add try/except. JSON diff.'),
            ("file_mkdir", 'Create Flask structure: app/, static/, templates/. JSON.'),
        ]:
            result = self.run_test(test_id, "FileTools", prompt)
            results.append(result)

        # Git Tools (3 tests)
        print("\n2.2 Git")
        for test_id, prompt in [
            ("git_status", 'Git status command and explain sections.'),
            ("git_branch", 'Commands: create branch, switch, push. JSON.'),
            ("git_commit", 'Commit with message and explain flags.'),
        ]:
            result = self.run_test(test_id, "GitTools", prompt)
            results.append(result)

        print("\n" + "="*60)
        print("PHASE 3: MEMORY")
        print("="*60)

        for test_id, prompt in [
            ("memory_01", 'Remember: user prefers dark mode. JSON.'),
            ("memory_02", 'Recall memories about Python projects. JSON array.'),
            ("memory_03", 'Search for "bug" tagged memories. Query JSON.'),
        ]:
            result = self.run_test(test_id, "Memory", prompt)
            results.append(result)

        print("\n" + "="*60)
        print("PHASE 4: SKILLS")
        print("="*60)

        # Code Review (2 tests)
        print("\n4.1 Code Review")
        for test_id, prompt in [
            ("review_01", 'Find TODOs in:\n```python\n# TODO: refactor\ndef old(): pass\n```'),
            ("review_02", 'Find empty except in:\ntry: x=1\nexcept: pass'),
        ]:
            result = self.run_test(test_id, "CodeReview", prompt)
            results.append(result)

        # Security (2 tests)
        print("\n4.2 Security")
        for test_id, prompt in [
            ("sec_01", 'Find secrets in:\npassword="admin"\napi_key="sk-abc"'),
            ("sec_02", 'Find SQL injection in:\nquery=f"SELECT * FROM users WHERE name=\'{user}\'"'),
        ]:
            result = self.run_test(test_id, "Security", prompt)
            results.append(result)

        print("\n" + "="*60)
        print("PHASE 5: E2E")
        print("="*60)

        for test_id, prompt in [
            ("e2e_01", 'TODO CLI spec: Add/list/complete/delete, SQLite, pytest.'),
            ("e2e_02", 'Bug: calculator returns 0 for division. Root cause and fix.'),
            ("e2e_03", 'Python code review checklist: imports, naming, errors, tests.'),
        ]:
            result = self.run_test(test_id, "E2E", prompt)
            results.append(result)

        self.results = results

        # Summary
        end_time = datetime.now().isoformat()
        self.summary.end_time = end_time
        self.summary.total_duration_hours = (datetime.fromisoformat(end_time) - datetime.fromisoformat(self.start_time)).total_seconds() / 3600

        self.summary.total_tests = len(results)
        self.summary.passed = sum(1 for r in results if r.success)
        self.summary.failed = self.summary.total_tests - self.summary.passed
        self.summary.success_rate = (self.summary.passed / self.summary.total_tests * 100) if self.summary.total_tests > 0 else 0

        response_times = [r.response_time_ms for r in results if r.response_time_ms > 0]
        self.summary.avg_response_time_ms = sum(response_times) / len(response_times) if response_times else 0

        # Per-category
        categories = {}
        for result in results:
            if result.category not in categories:
                categories[result.category] = {"total": 0, "passed": 0}
            categories[result.category]["total"] += 1
            if result.success:
                categories[result.category]["passed"] += 1

        for cat in categories:
            cat_total = categories[cat]["total"]
            cat_passed = categories[cat]["passed"]
            categories[cat]["rate"] = (cat_passed / cat_total * 100) if cat_total > 0 else 0

        self.summary.categories = categories

        print("\n" + "="*60)
        print("TEST COMPLETE")
        print(f"Duration: {self.summary.total_duration_hours:.2f}h")
        print(f"Passed: {self.summary.passed}/{self.summary.total_tests} ({self.summary.success_rate:.1f}%)")
        print("="*60)

        return self.summary

    def save_results(self, output_path: str):
        data = {
            "summary": asdict(self.summary),
            "results": [asdict(r) for r in self.results]
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Claude Model Test Runner")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Model name (claude-sonnet-4-6, claude-haiku-4-5, claude-opus-4-5)")
    parser.add_argument("--output", default="tests/results_claude.json", help="Output JSON file")
    args = parser.parse_args()

    # Load config
    settings_path = Path.home() / ".claude" / "settings.json"
    with open(settings_path, 'r') as f:
        settings = json.load(f)

    base_url = settings["env"].get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    api_key = settings["env"].get("ANTHROPIC_API_KEY", "")

    runner = ClaudeTestRunner(args.model, base_url, api_key)
    runner.run_tests()
    runner.save_results(args.output)

    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Model: {runner.summary.model}")
    print(f"Duration: {runner.summary.total_duration_hours:.2f}h")
    print(f"Tests: {runner.summary.total_tests}")
    print(f"Success Rate: {runner.summary.success_rate:.1f}%")
    print(f"Avg Response: {runner.summary.avg_response_time_ms:.0f}ms")
    for cat, stats in runner.summary.categories.items():
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({stats['rate']:.1f}%)")
    print("="*60)


if __name__ == "__main__":
    main()