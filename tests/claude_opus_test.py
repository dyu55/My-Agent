#!/usr/bin/env python3
"""
Claude Opus Test Runner for Michael Agent
Uses Anthropic API (via ccswitch) to run the same tests

Usage:
    python3 tests/claude_opus_test.py --output results_claude_opus.json
"""

import argparse
import json
import time
import sys
import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class TestResult:
    """Single test result."""
    test_id: str
    category: str
    task: str
    prompt: str
    response: str
    expected: str | None = None
    success: bool = False
    response_time_ms: float = 0
    total_duration_ms: float = 0
    token_count: int = 0
    token_speed: float = 0
    error: str | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class TestSummary:
    """Summary of all tests."""
    model: str
    start_time: str
    end_time: str | None = None
    total_duration_hours: float = 0
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    success_rate: float = 0
    avg_response_time_ms: float = 0
    avg_token_speed: float = 0
    categories: dict = field(default_factory=dict)


class ClaudeOpusProvider:
    """Claude Opus provider using Anthropic API via ccswitch."""

    def __init__(self, base_url: str, api_key: str, model: str = "claude-sonnet-4-6"):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model

    def chat(self, prompt: str, **kwargs) -> str:
        """Send chat request to Claude Opus via ccswitch."""
        import urllib.request
        import urllib.error
        import time

        url = f"{self.base_url}/v1/messages"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096
        }

        # Retry logic for rate limits
        max_retries = 5
        retry_delay = 10  # seconds

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
                    # Rate limit - wait and retry
                    print(f"    Rate limited, waiting {retry_delay}s... (attempt {attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                else:
                    error_body = e.read().decode('utf-8') if e.fp else ""
                    raise Exception(f"HTTP {e.code}: {error_body}")
            except Exception as e:
                raise Exception(f"Request failed: {e}")

        raise Exception("Max retries exceeded due to rate limiting")


class ClaudeOpusTestRunner:
    """Test runner using Claude Opus."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.results: list[TestResult] = []
        self.start_time = datetime.now().isoformat()
        self.summary = TestSummary(model="claude-opus-4-5", start_time=self.start_time)

        print(f"Initializing Claude Opus test runner")
        print(f"API: {base_url}")

        self.provider = ClaudeOpusProvider(base_url, api_key)
        print(f"Provider created: Claude Opus via ccswitch")

    def run_test(self, test_id: str, category: str, prompt: str,
                 expected: str | None = None) -> TestResult:
        """Run a single test and return result."""
        print(f"  [{category}] {test_id}: {prompt[:50]}...")

        start = time.time()
        result = TestResult(
            test_id=test_id,
            category=category,
            task=test_id,
            prompt=prompt,
            expected=expected,
            response=""
        )

        try:
            response = self.provider.chat(prompt)
            result.response = response
            result.success = True
        except Exception as e:
            result.error = str(e)
            result.success = False
            print(f"    ERROR: {e}")

        end = time.time()
        result.response_time_ms = (end - start) * 1000

        # Estimate token count
        result.token_count = len(result.response) // 4
        if result.response_time_ms > 0:
            result.token_speed = (result.token_count / result.response_time_ms) * 1000

        return result

    def run_phase1_agent_core(self) -> list[TestResult]:
        """Phase 1: Agent Core Loop Tests"""
        results = []
        print("\n" + "="*60)
        print("PHASE 1: AGENT CORE LOOP")
        print("="*60)

        # Plan Phase
        print("\n1.1 Plan Phase Tests")
        for test_id, prompt in [
            ("plan_01", 'Create a step-by-step plan to build a calculator with add, subtract, multiply, divide. Output as JSON with steps array.'),
            ("plan_02", "Design a web scraper for news articles. Break down into 5 subtasks with dependencies."),
            ("plan_03", "Plan a REST API for a blog system. Include endpoints for posts, comments, users."),
        ]:
            result = self.run_test(test_id, "Plan", prompt)
            result.success = self._validate_json_response(result.response)
            results.append(result)

        # Act Phase
        print("\n1.2 Act Phase Tests")
        for test_id, prompt in [
            ("act_01", 'Generate a JSON action to write "Hello World" to hello.txt. Format: {"tool": "write", "path": "hello.txt", "content": "..."}'),
            ("act_02", 'Generate JSON actions to create a Python project structure with main.py, utils/, tests/. Output as array of actions.'),
            ("act_03", 'Generate JSON for git workflow: git init, git add ., git commit -m "initial". Format: array of commands.'),
        ]:
            result = self.run_test(test_id, "Act", prompt)
            result.success = self._validate_json_response(result.response)
            results.append(result)

        # Reflect Phase
        print("\n1.3 Reflect Phase Tests")
        for test_id, prompt in [
            ("reflect_01", 'Analyze this error: "FileNotFoundError: [Errno 2] No such file: data.txt". What is the root cause and how to fix?'),
            ("reflect_02", 'Analyze this error: "SyntaxError: invalid syntax" at line 15. The code is: def broken(). Return JSON with error_type and fix.'),
            ("reflect_03", 'A test failed: test_user_login. Error: "AssertionError: expected 200 got 401". Is this a flaky test or real bug?'),
        ]:
            result = self.run_test(test_id, "Reflect", prompt)
            results.append(result)

        return results

    def run_phase2_tools(self) -> list[TestResult]:
        """Phase 2: Tool System Tests"""
        results = []
        print("\n" + "="*60)
        print("PHASE 2: TOOL SYSTEM")
        print("="*60)

        # File Tools
        print("\n2.1 File Tools")
        for test_id, prompt in [
            ("file_write", 'Write a Python script that reads a CSV file and outputs statistics. Output as JSON with file content.'),
            ("file_edit", 'Edit the script to add try/except for missing files. Output JSON with original and new content.'),
            ("file_mkdir", 'Create directory structure for Flask app: app/, static/, templates/, tests/. Output JSON.'),
        ]:
            result = self.run_test(test_id, "FileTools", prompt)
            results.append(result)

        # Exec Tools
        print("\n2.2 Exec Tools")
        for test_id, prompt in [
            ("exec_check", 'Write commands to check if Python, pip, pytest are installed. Output JSON array.'),
            ("exec_install", 'Generate pip install command for: requests, flask, pytest. Include version constraints.'),
        ]:
            result = self.run_test(test_id, "ExecTools", prompt)
            results.append(result)

        # Git Tools
        print("\n2.3 Git Tools")
        for test_id, prompt in [
            ("git_status", 'Write git status command and explain the output sections.'),
            ("git_branch", 'Commands to create branch "feature/test", switch to it, then push.'),
            ("git_commit", 'Write commit command with message "Add authentication module" and explain flags.'),
        ]:
            result = self.run_test(test_id, "GitTools", prompt)
            results.append(result)

        # Quality Tools
        print("\n2.4 Quality Tools")
        for test_id, prompt in [
            ("lint_ruff", 'Write ruff linter command to check agent/ directory.'),
            ("security_scan", 'Write bandit command to scan for security issues.'),
        ]:
            result = self.run_test(test_id, "QualityTools", prompt)
            results.append(result)

        return results

    def run_phase3_memory(self) -> list[TestResult]:
        """Phase 3: Memory System Tests"""
        results = []
        print("\n" + "="*60)
        print("PHASE 3: MEMORY SYSTEM")
        print("="*60)

        for test_id, prompt in [
            ("memory_remember", 'Remember: the user prefers dark mode theme. Format as JSON memory object.'),
            ("memory_recall", 'Recall all memories about Python projects. Format: JSON array of memories.'),
            ("memory_search", 'Search for memories tagged with "bug". Show semantic search query.'),
        ]:
            result = self.run_test(test_id, "Memory", prompt)
            results.append(result)

        return results

    def run_phase4_skills(self) -> list[TestResult]:
        """Phase 4: Skills System Tests"""
        results = []
        print("\n" + "="*60)
        print("PHASE 4: SKILLS SYSTEM")
        print("="*60)

        # Code Review
        print("\n4.1 Code Review")
        for test_id, prompt in [
            ("review_todo", 'Find all TODO and FIXME comments in this Python code:\n```python\ndef old_func():\n    # TODO: refactor later\n    pass\n# FIXME: broken\n```'),
            ("review_exception", 'Find empty exception handling in:\n```python\ntry:\n    x = 1\nexcept:\n    pass\n```'),
        ]:
            result = self.run_test(test_id, "CodeReview", prompt)
            results.append(result)

        # Security Review
        print("\n4.2 Security Review")
        for test_id, prompt in [
            ("sec_hardcoded", 'Find hardcoded secrets in:\npassword = "admin123"\napi_key = "sk-abc123"'),
            ("sec_sqli", 'Find SQL injection in:\nquery = f"SELECT * FROM users WHERE name = \'{user}\'"'),
        ]:
            result = self.run_test(test_id, "SecurityReview", prompt)
            results.append(result)

        return results

    def run_phase5_e2e(self) -> list[TestResult]:
        """Phase 5: E2E Workflows"""
        results = []
        print("\n" + "="*60)
        print("PHASE 5: E2E WORKFLOWS")
        print("="*60)

        for test_id, prompt in [
            ("e2e_project", 'Create TODO CLI app spec: Add/list/complete/delete, SQLite storage, pytest tests, Docker.'),
            ("e2e_bugfix", 'Bug: calculator returns 0 for division. Analyze root cause and fix.'),
            ("e2e_review", 'Code review checklist for Python: imports, naming, error handling, tests.'),
        ]:
            result = self.run_test(test_id, "E2E", prompt)
            results.append(result)

        return results

    def _validate_json_response(self, response: str) -> bool:
        """Check if response contains valid JSON."""
        import re
        json_match = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', response)
        if json_match:
            try:
                json.loads(json_match.group())
                return True
            except json.JSONDecodeError:
                return False
        return False

    def run_all_tests(self) -> TestSummary:
        """Run all test phases and return summary."""
        print("\n" + "#"*60)
        print("# STARTING CLAUDE OPUS TEST SUITE")
        print(f"# Start Time: {self.start_time}")
        print("#"*60)

        all_results = []
        all_results.extend(self.run_phase1_agent_core())
        all_results.extend(self.run_phase2_tools())
        all_results.extend(self.run_phase3_memory())
        all_results.extend(self.run_phase4_skills())
        all_results.extend(self.run_phase5_e2e())

        self.results = all_results

        # Calculate summary
        end_time = datetime.now().isoformat()
        self.summary.end_time = end_time

        start_dt = datetime.fromisoformat(self.start_time)
        end_dt = datetime.fromisoformat(end_time)
        self.summary.total_duration_hours = (end_dt - start_dt).total_seconds() / 3600

        self.summary.total_tests = len(all_results)
        self.summary.passed = sum(1 for r in all_results if r.success)
        self.summary.failed = self.summary.total_tests - self.summary.passed
        self.summary.success_rate = (self.summary.passed / self.summary.total_tests * 100) if self.summary.total_tests > 0 else 0

        response_times = [r.response_time_ms for r in all_results if r.response_time_ms > 0]
        self.summary.avg_response_time_ms = sum(response_times) / len(response_times) if response_times else 0

        token_speeds = [r.token_speed for r in all_results if r.token_speed > 0]
        self.summary.avg_token_speed = sum(token_speeds) / len(token_speeds) if token_speeds else 0

        # Per-category breakdown
        categories = {}
        for result in all_results:
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

        print("\n" + "#"*60)
        print(f"# TEST SUITE COMPLETE")
        print(f"# Duration: {self.summary.total_duration_hours:.2f} hours")
        print(f"# Passed: {self.summary.passed}/{self.summary.total_tests} ({self.summary.success_rate:.1f}%)")
        print("#"*60)

        return self.summary

    def save_results(self, output_path: str):
        """Save results to JSON file."""
        data = {
            "summary": asdict(self.summary),
            "results": [asdict(r) for r in self.results]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nResults saved to: {output_path}")


def main():
    # Load config from settings
    settings_path = Path.home() / ".claude" / "settings.json"
    with open(settings_path, 'r') as f:
        settings = json.load(f)

    base_url = settings["env"].get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    api_key = settings["env"].get("ANTHROPIC_API_KEY", "")

    parser = argparse.ArgumentParser(description="Claude Opus Test Runner")
    parser.add_argument("--output", default="tests/results_claude_opus.json", help="Output JSON file")
    args = parser.parse_args()

    runner = ClaudeOpusTestRunner(base_url, api_key)
    runner.run_all_tests()
    runner.save_results(args.output)

    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    print(f"Model: {runner.summary.model}")
    print(f"Tests: {runner.summary.total_tests}")
    print(f"Success Rate: {runner.summary.success_rate:.1f}%")
    print(f"Avg Response Time: {runner.summary.avg_response_time_ms:.0f} ms")
    print("="*60)


if __name__ == "__main__":
    main()
