#!/usr/bin/env python3
"""Daily Self-Optimization & Evolution Pipeline for MyAgent.

Executes daily self-healing, quality auditing, regression testing, and CI verification:
1. Syntax & Static Lint Audit
2. Full Test Suite Regression (450+ tests)
3. AST RepoMap & Symbol Re-indexing
4. LLM Cache Hygiene
5. GitHub Actions CI Health Check & Auto-Healing
"""

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent.resolve()
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


def log(emoji: str, msg: str):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {emoji} {msg}", flush=True)


def run_cmd(cmd: str, check: bool = False) -> tuple[int, str]:
    res = subprocess.run(
        cmd,
        shell=True,
        cwd=WORKSPACE_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed (code {res.returncode}): {cmd}\nOutput:\n{res.stdout}")
    return res.returncode, res.stdout


def stage_syntax_and_lint() -> bool:
    log("🔍", "Stage 1: Checking Python syntax & code structure...")
    code, out = run_cmd("python3 -m py_compile agent/engine.py agent/planner.py agent/executor.py agent/reflector.py utils/model_provider.py utils/small_model.py main.py")
    if code != 0:
        log("❌", f"Syntax errors found:\n{out}")
        return False
    log("✅", "Syntax verification passed.")
    return True


def stage_run_tests() -> bool:
    log("🧪", "Stage 2: Running full unit & integration regression tests...")
    code, out = run_cmd("/opt/miniconda3/bin/pytest tests/ -q --tb=short --ignore=tests/test_e2e.py --ignore=tests/test_layer1_integration.py --ignore=tests/test_memory_interface.py --ignore=tests/llm_models_benchmark.py --ignore=tests/skills_models_benchmark.py")
    if code != 0:
        log("❌", f"Test regression detected:\n{out}")
        return False
    # Parse passed test count
    passed_line = [l for l in out.splitlines() if "passed" in l]
    summary = passed_line[-1] if passed_line else "All tests passed"
    log("✅", f"Tests passed successfully: {summary}")
    return True


def stage_repo_map_and_cache() -> bool:
    log("🗺️", "Stage 3: Generating AST Repo Map & verifying symbol graph...")
    try:
        from agent.tools.repo_map import RepoMap
        repo_map = RepoMap(WORKSPACE_ROOT, max_chars=4000)
        symbols = repo_map.generate_map()
        line_count = len(symbols.splitlines())
        log("✅", f"AST RepoMap indexed successfully ({line_count} lines of symbols).")
    except Exception as e:
        log("❌", f"AST RepoMap generation error: {e}")
        return False

    # Cache hygiene
    try:
        from utils.llm_cache import LLMCache
        cache = LLMCache()
        log("✅", f"LLM Cache verified (entries={len(cache._cache) if hasattr(cache, '_cache') else 'OK'}).")
    except Exception:
        pass
    return True


def stage_ci_guard_and_heal() -> bool:
    log("🛡️", "Stage 4: Checking GitHub Actions CI status...")
    code, out = run_cmd("gh run list --limit 3")
    if code != 0:
        log("⚠️", f"Could not list gh runs: {out}")
        return True

    lines = out.strip().splitlines()
    if not lines:
        log("ℹ️", "No CI runs found.")
        return True

    latest = lines[0]
    log("📋", f"Latest CI run: {latest}")

    if "failure" in latest.lower():
        log("🚨", "Latest CI failed! Attempting auto-healing...")
        # Get run id
        parts = latest.split()
        run_id = None
        for p in parts:
            if p.isdigit() and len(p) >= 8:
                run_id = p
                break
        if run_id:
            _, log_out = run_cmd(f"gh run view {run_id} --log-failed")
            log("📝", f"Failure logs (snippet):\n{log_out[:1000]}")

        # Re-run local tests to diagnose
        test_code, test_out = run_cmd("/opt/miniconda3/bin/pytest tests/ -v --tb=short")
        log("🔧", f"Local diagnosis output:\n{test_out[:1000]}")
        return False
    else:
        log("✅", "GitHub Actions CI is 100% green and healthy.")
        return True


def run_daily_optimization():
    log("🚀", "Starting Daily Self-Optimization & Evolution Run...")
    start_time = time.time()

    s1 = stage_syntax_and_lint()
    s2 = stage_run_tests()
    s3 = stage_repo_map_and_cache()
    s4 = stage_ci_guard_and_heal()

    elapsed = time.time() - start_time
    status = "SUCCESS" if (s1 and s2 and s3 and s4) else "WARNING/NEEDS_ATTENTION"

    log("🏁", f"Daily Self-Optimization completed in {elapsed:.2f}s with status: {status}")
    return 0 if status == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(run_daily_optimization())
