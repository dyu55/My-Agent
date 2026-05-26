#!/usr/bin/env python3
"""
Model Deep Test Runner for Michael Agent - Optimized for Large Models
Uses direct HTTP to avoid Python ollama client issues
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


class DirectOllamaProvider:
    """Direct HTTP client for Ollama to avoid Python SDK issues."""

    def __init__(self, base_url: str, model: str, timeout: int = 600):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout

    def chat(self, prompt: str, **kwargs) -> str:
        """Send chat request via HTTP."""
        url = f"{self.base_url}/api/chat"

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 1024,  # Limit response length
                "enable_thinking": False,  # Disable thinking to speed up
            }
        }

        body = json.dumps(data).encode('utf-8')

        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result["message"]["content"]
        except urllib.error.HTTPError as e:
            raise Exception(f"HTTP {e.code}: {e.read().decode('utf-8')}")
        except Exception as e:
            raise Exception(f"Request failed: {e}")


class ModelTestRunner:
    """Test runner for model evaluation."""

    def __init__(self, model: str, base_url: str = "http://192.168.0.124:11434", timeout: int = 600):
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.results: list[TestResult] = []
        self.start_time = datetime.now().isoformat()
        self.summary = TestSummary(model=model, start_time=self.start_time)

        print(f"Initializing test runner for model: {model}")
        print(f"Server: {base_url}")

        self.provider = DirectOllamaProvider(base_url, model, timeout)
        print(f"Provider created: Direct HTTP client")

    def run_test(self, test_id: str, category: str, prompt: str,
                 expected: str | None = None) -> TestResult:
        """Run a single test and return result."""
        print(f"  [{category}] {test_id}: {prompt[:50]}...", flush=True)

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
            print(f"    ERROR: {str(e)[:100]}")

        end = time.time()
        result.response_time_ms = (end - start) * 1000

        # Estimate token count
        result.token_count = len(result.response) // 4
        if result.response_time_ms > 0:
            result.token_speed = (result.token_count / result.response_time_ms) * 1000

        return result

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

    def run_phase1_agent_core(self) -> list[TestResult]:
        """Phase 1: Agent Core Loop Tests"""
        results = []

        print("\n" + "="*60)
        print("PHASE 1: AGENT CORE LOOP")
        print("="*60)

        # Plan Phase (5 tests)
        print("\n1.1 Plan Phase Tests")
        for test_id, prompt in [
            ("plan_01", 'Create a JSON plan to build a calculator with add, subtract, multiply, divide. Include steps array.'),
            ("plan_02", 'Design a web scraper in 5 steps with dependencies.'),
            ("plan_03", 'Plan a REST API for a blog system with 5 endpoints.'),
            ("plan_04", 'Plan a sorting algorithm visualization.'),
            ("plan_05", 'Plan a CLI file encryption tool.'),
        ]:
            result = self.run_test(test_id, "Plan", prompt)
            result.success = self._validate_json_response(result.response)
            results.append(result)

        # Act Phase (5 tests)
        print("\n1.2 Act Phase Tests")
        for test_id, prompt in [
            ("act_01", 'Generate JSON to write "Hello World" to hello.txt'),
            ("act_02", 'Generate JSON array for Python project: main.py, utils/, tests/'),
            ("act_03", 'Generate JSON array: git init, git add ., git commit -m "init"'),
            ("act_04", 'Generate JSON for pytest: pytest tests/ --cov=src'),
            ("act_05", 'Generate JSON for Docker: build "myapp", run on port 8000'),
        ]:
            result = self.run_test(test_id, "Act", prompt)
            result.success = self._validate_json_response(result.response)
            results.append(result)

        # Reflect Phase (5 tests)
        print("\n1.3 Reflect Phase Tests")
        for test_id, prompt in [
            ("reflect_01", 'Analyze error: "FileNotFoundError: data.txt not found". Root cause and fix in JSON.'),
            ("reflect_02", 'Analyze: "SyntaxError at line 15: def broken()". JSON with error_type and fix.'),
            ("reflect_03", 'Test failed: AssertionError expected 200 got 401. Flaky or real bug?'),
            ("reflect_04", 'Error: "ModuleNotFoundError: requests". Fix: JSON command.'),
            ("reflect_05", 'Timeout after 30s. Suggest 3 optimizations in JSON.'),
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

        # File Tools (5 tests)
        print("\n2.1 File Tools")
        for test_id, prompt in [
            ("file_write", 'Write Python script to read CSV and output stats. JSON with code.'),
            ("file_edit", 'Edit script to add try/except for missing files. JSON diff.'),
            ("file_mkdir", 'Create Flask structure: app/, static/, templates/, tests/. JSON.'),
            ("file_list", 'Shell command to list all .py files recursively with line numbers.'),
            ("file_batch", 'Create 3 files: config.json, main.py, requirements.txt. JSON array.'),
        ]:
            result = self.run_test(test_id, "FileTools", prompt)
            results.append(result)

        # Exec Tools (4 tests)
        print("\n2.2 Exec Tools")
        for test_id, prompt in [
            ("exec_check", 'Commands to check Python, pip, pytest installed. JSON array.'),
            ("exec_install", 'pip install requests, flask, pytest with version constraints.'),
            ("exec_run", 'pytest with verbose and stop on first failure. Command only.'),
            ("exec_capture", 'Run script in background and capture PID. Shell command.'),
        ]:
            result = self.run_test(test_id, "ExecTools", prompt)
            results.append(result)

        # Git Tools (5 tests)
        print("\n2.3 Git Tools")
        for test_id, prompt in [
            ("git_status", 'Git status command and explain sections.'),
            ("git_branch", 'Create "feature/test", switch, push. Commands JSON.'),
            ("git_commit", 'Commit with message and explain flags.'),
            ("git_diff", 'Diff working dir vs staging. Command and explanation.'),
            ("git_log", 'Last 10 commits with graph. Command.'),
        ]:
            result = self.run_test(test_id, "GitTools", prompt)
            results.append(result)

        # Quality Tools (3 tests)
        print("\n2.4 Quality Tools")
        for test_id, prompt in [
            ("lint_ruff", 'Ruff command to check agent/ directory.'),
            ("type_mypy", 'Mypy to type-check cli/ module.'),
            ("security_scan", 'Bandit command for security scan.'),
        ]:
            result = self.run_test(test_id, "QualityTools", prompt)
            results.append(result)

        # Deploy Tools (3 tests)
        print("\n2.5 Deploy Tools")
        for test_id, prompt in [
            ("deploy_dockerfile", 'Dockerfile for Python 3.13 Flask app with multi-stage build.'),
            ("deploy_compose", 'docker-compose.yml for web + PostgreSQL + Redis.'),
            ("deploy_actions", 'GitHub Actions CI: lint, test, coverage.'),
        ]:
            result = self.run_test(test_id, "DeployTools", prompt)
            results.append(result)

        return results

    def run_phase3_memory(self) -> list[TestResult]:
        """Phase 3: Memory System Tests"""
        results = []

        print("\n" + "="*60)
        print("PHASE 3: MEMORY SYSTEM")
        print("="*60)

        for test_id, prompt in [
            ("memory_remember", 'Remember: user prefers dark mode. JSON memory object.'),
            ("memory_recall", 'Recall memories about Python projects. JSON array.'),
            ("memory_search", 'Search for "bug" tagged memories. Query JSON.'),
            ("memory_session", 'Get memories from session "abc123". Query JSON.'),
            ("memory_semantic", 'Find memories related to "authentication". Semantic query.'),
            ("memory_cleanup", 'Strategy for cleaning up memories older than 30 days.'),
        ]:
            result = self.run_test(test_id, "Memory", prompt)
            results.append(result)

        return results

    def run_phase4_coordinator(self) -> list[TestResult]:
        """Phase 4: Multi-Agent Coordinator Tests"""
        results = []

        print("\n" + "="*60)
        print("PHASE 4: MULTI-AGENT COORDINATOR")
        print("="*60)

        for test_id, prompt in [
            ("coord_decompose", 'Divide blog implementation into 5 parallel tasks.'),
            ("coord_deps", 'Dependencies: A, B, C, D where B on A, C on A, D on B+C.'),
            ("coord_merge", 'Merge 3 parallel agent results. Strategies JSON.'),
            ("coord_conflict", 'Two agents suggest different implementations. Resolution?'),
            ("coord_speedup", 'Speedup ratio: 4 agents vs 1 for 10 tasks. Calculation.'),
        ]:
            result = self.run_test(test_id, "Coordinator", prompt)
            results.append(result)

        return results

    def run_phase5_skills(self) -> list[TestResult]:
        """Phase 5: Skills System Tests"""
        results = []

        print("\n" + "="*60)
        print("PHASE 5: SKILLS SYSTEM")
        print("="*60)

        # Code Review
        print("\n5.1 Code Review")
        for test_id, prompt in [
            ("review_todo", 'Find TODOs in:\n```python\ndef old():\n  # TODO: refactor\n  pass\n# FIXME: broken\n```'),
            ("review_exception", 'Find empty except in:\ntry: x=1\nexcept: pass'),
            ("review_debug", 'Find debug statements: print("debug"), console.log("x")'),
        ]:
            result = self.run_test(test_id, "CodeReview", prompt)
            results.append(result)

        # Security Review
        print("\n5.2 Security Review")
        for test_id, prompt in [
            ("sec_hardcoded", 'Find secrets in:\npassword="admin"\napi_key="sk-abc"'),
            ("sec_sqli", 'Find SQL injection in:\nquery=f"SELECT * FROM users WHERE name=\'{user}\'"'),
            ("sec_shell", 'Find shell injection in:\nos.system(f"rm -rf {path}")'),
        ]:
            result = self.run_test(test_id, "SecurityReview", prompt)
            results.append(result)

        # Simplify
        print("\n5.3 Simplify")
        for test_id, prompt in [
            ("simplify_dup", 'Find duplicates in:\ndef add(a,b):return a+b\ndef sum(x,y):return x+y'),
            ("simplify_long", 'Split: def process(): validate(); fetch(); transform(); save();'),
        ]:
            result = self.run_test(test_id, "Simplify", prompt)
            results.append(result)

        return results

    def run_phase6_provider(self) -> list[TestResult]:
        """Phase 6: Model Provider Tests"""
        results = []

        print("\n" + "="*60)
        print("PHASE 6: MODEL PROVIDER")
        print("="*60)

        for test_id, prompt in [
            ("provider_connect", 'Verify connection to model server. Health check.'),
            ("provider_switch", 'Strategy to switch models mid-session.'),
            ("provider_fallback", 'Fallback: Primary fails -> backup -> default.'),
            ("provider_timeout", 'Handle 60s timeout: retry logic and feedback.'),
        ]:
            result = self.run_test(test_id, "Provider", prompt)
            results.append(result)

        return results

    def run_phase7_cli(self) -> list[TestResult]:
        """Phase 7: CLI Integration Tests"""
        results = []

        print("\n" + "="*60)
        print("PHASE 7: CLI INTEGRATION")
        print("="*60)

        for test_id, prompt in [
            ("cli_help", '/help lists all commands.'),
            ("cli_status", '/status shows fields: session, model, tests, memory.'),
            ("cli_search", '/search usage: /search <query> --tags <tags>.'),
            ("cli_task", '/task <description> starts new task.'),
            ("cli_git", 'Git via CLI: status, add, commit workflow.'),
        ]:
            result = self.run_test(test_id, "CLI", prompt)
            results.append(result)

        return results

    def run_phase8_e2e(self) -> list[TestResult]:
        """Phase 8: E2E Workflows"""
        results = []

        print("\n" + "="*60)
        print("PHASE 8: E2E WORKFLOWS")
        print("="*60)

        for test_id, prompt in [
            ("e2e_project", 'TODO CLI spec: Add/list/complete/delete, SQLite, pytest, Docker.'),
            ("e2e_bugfix", 'Bug: calculator returns 0 for division. Root cause and fix.'),
            ("e2e_feature", 'Add pagination to API: read, design, implement, test.'),
            ("e2e_refactor", 'Split 200-line function into 5 smaller functions.'),
            ("e2e_review", 'Python code review checklist: imports, naming, errors, tests.'),
        ]:
            result = self.run_test(test_id, "E2E", prompt)
            results.append(result)

        return results

    def run_phase9_stress(self) -> list[TestResult]:
        """Phase 9: Stress & Edge Cases"""
        results = []

        print("\n" + "="*60)
        print("PHASE 9: STRESS & EDGE CASES")
        print("="*60)

        for test_id, prompt in [
            ("stress_long", 'Process 100-word paragraph: summarize it.'),
            ("stress_empty", 'Handle empty input "" . Response?'  + '\n""'),
            ("stress_special", 'Handle special chars: <>&\'" . Sanitize method.'),
            ("stress_malformed", 'Parse JSON: {broken}. Error handling?'),
            ("stress_concurrent", 'Design for 10 concurrent requests. Architecture.'),
        ]:
            result = self.run_test(test_id, "Stress", prompt)
            results.append(result)

        return results

    def run_phase10_optimization(self) -> list[TestResult]:
        """Phase 10: Optimization Tests"""
        results = []

        print("\n" + "="*60)
        print("PHASE 10: OPTIMIZATION")
        print("="*60)

        for test_id, prompt in [
            ("opt_cache", 'Caching strategy: TTL, invalidation, memory limits.'),
            ("opt_cost", 'API costs: per-token pricing, budget alerts at $10.'),
            ("opt_speed", 'Reduce latency: batching, caching, parallel.'),
        ]:
            result = self.run_test(test_id, "Optimization", prompt)
            results.append(result)

        return results

    def run_all_tests(self) -> TestSummary:
        """Run all test phases."""
        print("\n" + "#"*60)
        print(f"# STARTING FULL TEST SUITE: {self.model}")
        print(f"# Start Time: {self.start_time}")
        print("#"*60)

        all_results = []
        all_results.extend(self.run_phase1_agent_core())
        all_results.extend(self.run_phase2_tools())
        all_results.extend(self.run_phase3_memory())
        all_results.extend(self.run_phase4_coordinator())
        all_results.extend(self.run_phase5_skills())
        all_results.extend(self.run_phase6_provider())
        all_results.extend(self.run_phase7_cli())
        all_results.extend(self.run_phase8_e2e())
        all_results.extend(self.run_phase9_stress())
        all_results.extend(self.run_phase10_optimization())

        self.results = all_results

        # Summary
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

        # Per-category
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
        print(f"# TEST COMPLETE")
        print(f"# Duration: {self.summary.total_duration_hours:.2f} hours")
        print(f"# Passed: {self.summary.passed}/{self.summary.total_tests} ({self.summary.success_rate:.1f}%)")
        print("#"*60)

        return self.summary

    def save_results(self, output_path: str):
        """Save results to JSON."""
        data = {
            "summary": asdict(self.summary),
            "results": [asdict(r) for r in self.results]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Results saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Model Test Runner")
    parser.add_argument("--model", required=True, help="Model name")
    parser.add_argument("--output", required=True, help="Output JSON file")
    parser.add_argument("--base-url", default="http://192.168.0.124:11434")
    parser.add_argument("--timeout", type=int, default=600)

    args = parser.parse_args()

    runner = ModelTestRunner(
        model=args.model,
        base_url=args.base_url,
        timeout=args.timeout
    )
    runner.run_all_tests()
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
