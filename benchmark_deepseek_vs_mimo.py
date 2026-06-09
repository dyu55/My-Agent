#!/usr/bin/env python3
"""DeepSeek V4 Pro vs MiMo V2.5 Pro — 全面对比基准测试

覆盖维度:
  1. Coding (代码生成: 简单/中等/复杂/调试/代码审查)
  2. Planning (任务规划: 架构拆解/开发计划)
  3. Web Scraping (网页抓取: HTML解析/结构化提取)
  4. Info Extraction (信息提取: 摘要/结构化数据)
  5. Long Task (长任务: 多步骤复杂构建)
  6. Timing/Scheduled (定时任务: 响应时间一致性)
"""

import os
import sys
import time
import json
from datetime import datetime

# ============================================================
# Configuration
# ============================================================

MODELS = {
    "deepseek-v4-pro": {
        "client": None,  # lazy init
        "base_url": "https://api.deepseek.com",
        "api_key": os.getenv("BENCHMARK_DEEPSEEK_API_KEY", ""),
        "model": "deepseek-v4-pro",
        "label": "DeepSeek V4 Pro",
    },
    "mimo-v2.5-pro": {
        "client": None,
        "base_url": "https://token-plan-sgp.xiaomimimo.com/v1",
        "api_key": os.getenv("BENCHMARK_MIMO_API_KEY", ""),
        "model": "mimo-v2.5-pro",
        "label": "MiMo V2.5 Pro",
    },
}


def init_clients():
    from openai import OpenAI
    for mid, cfg in MODELS.items():
        if cfg["client"] is None:
            cfg["client"] = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"])


# ============================================================
# Test Definitions
# ============================================================

CODING_TESTS = [
    {
        "id": "code-simple",
        "category": "Coding",
        "name": "Simple: 回文检测",
        "prompt": "Write a Python function `is_palindrome(s: str) -> bool` that checks if a string is a palindrome. Include docstring and handle edge cases (empty string, case insensitivity, spaces). Return only the code.",
    },
    {
        "id": "code-medium",
        "category": "Coding",
        "name": "Medium: TTL LRU Cache",
        "prompt": "Implement a thread-safe LRU cache with TTL (time-to-live) expiration in Python. Class name: `TTL_LRU_Cache`. Methods: `get(key)`, `put(key, value, ttl_seconds)`. O(1) get/put. Evict expired entries on access. Return only the code with docstrings.",
    },
    {
        "id": "code-complex",
        "category": "Coding",
        "name": "Complex: HTTP Router",
        "prompt": "Write a minimal HTTP routing framework in Python (no external libs, only stdlib). Support: @route decorator with path and methods, before_request hooks, path parameters like /users/<id>, and a simple run(host, port) method that starts an http.server. Return only the code with clear comments.",
    },
    {
        "id": "code-debug",
        "category": "Coding",
        "name": "Debug: 修复归并排序",
        "prompt": """This merge sort implementation has bugs. Find ALL bugs, explain each one, and provide the corrected code.

```python
def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return merge(left, right)

def merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] < right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

def test():
    assert merge_sort([3,1,4,1,5,9,2,6]) == [1,1,2,3,4,5,6,9]
    assert merge_sort([5,4,3,2,1]) == [1,2,3,4,5]
    assert merge_sort([1]) == [1]
    assert merge_sort([]) == []
    print('All tests passed')

test()
```

List each bug with a clear explanation, then show the complete fixed code.""",
    },
    {
        "id": "code-review",
        "category": "Coding",
        "name": "Code Review: 安全审查",
        "prompt": """Review this Flask app for security issues, bugs, and code quality problems. For each issue found, state: severity (critical/high/medium/low), what the issue is, and the fix.

```python
import sqlite3
import hashlib
from flask import Flask, request

app = Flask(__name__)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    hashed = hashlib.md5(password.encode()).hexdigest()
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{hashed}'"
    cursor.execute(query)
    user = cursor.fetchone()
    if user:
        return f"Welcome back, {username}!"
    return "Login failed"

@app.route('/admin')
def admin():
    return open('/etc/admin_config.json').read()

if __name__ == '__main__':
    app.run(debug=True)
```""",
    },
]

PLANNING_TESTS = [
    {
        "id": "plan-ecommerce",
        "category": "Planning",
        "name": "电商微服务架构拆解",
        "prompt": "You are planning a mid-scale e-commerce platform. Decompose the system into microservices. For each service, provide: name, responsibility, 3-5 key API endpoints, recommended data store, and dependencies on other services. Then give a 6-month phased roadmap with milestones. Be concrete — use real technology names (PostgreSQL, Redis, Kafka, etc.).",
    },
    {
        "id": "plan-cli-tool",
        "category": "Planning",
        "name": "CLI TODO 工具开发计划",
        "prompt": "Plan the development of a CLI TODO management tool in Python (like todo.txt CLI but modern). Provide: project structure with file names, module responsibilities, subtask breakdown with dependencies, estimated hours per subtask, recommended execution order, testing strategy, and packaging plan for PyPI. Be specific.",
    },
]

SCRAPING_TESTS = [
    {
        "id": "scrape-articles",
        "category": "Web Scraping",
        "name": "HTML文章列表提取",
        "prompt": """Extract all article titles, URLs, and dates from this HTML snippet. Return as a clean JSON array of objects. Handle missing fields gracefully (set to null if absent). Ignore sponsored content.

```html
<div class="article-list">
  <article>
    <h2><a href="/post/ai-breakthrough-2026">AI Breakthrough Changes Everything in 2026</a></h2>
    <span class="date">2026-05-20</span>
    <p class="excerpt">Researchers at DeepMind announced a revolutionary new model architecture...</p>
  </article>
  <article>
    <h2><a href="/post/python-4-roadmap">Python 4.0: The Official Roadmap</a></h2>
    <span class="date">2026-05-18</span>
  </article>
  <article>
    <h2><a href="/post/rust-vs-zig-2026">Rust vs Zig in 2026: A Practical Comparison</a></h2>
    <!-- date missing intentionally -->
    <p class="excerpt">Both languages have evolved significantly...</p>
  </article>
  <article class="sponsored">
    <h2><a href="/post/sponsored-cloud">Why Your Startup Needs Serverless</a></h2>
    <span class="date">2026-05-15</span>
  </article>
</div>
```""",
    },
    {
        "id": "scrape-product",
        "category": "Web Scraping",
        "name": "商品页结构化提取",
        "prompt": """Extract product information from this HTML product card into a structured JSON object. Include: name, price (numeric, use current/discounted price), currency, in_stock (boolean), rating (numeric 0-5), review_count (numeric), and features (list of strings).

```html
<div class="product-card">
  <h1 class="product-title">Wireless Noise-Cancelling Headphones Pro X</h1>
  <div class="pricing">
    <span class="original-price">$299.99</span>
    <span class="current-price">$199.99</span>
    <span class="discount-badge">-33%</span>
  </div>
  <div class="availability in-stock">In Stock</div>
  <div class="rating">
    <span class="stars" data-rating="4.5">★★★★½</span>
    <span class="review-count">2,847 reviews</span>
  </div>
  <ul class="features">
    <li>Active Noise Cancellation (ANC)</li>
    <li>40-hour battery life</li>
    <li>Bluetooth 5.3 with multipoint</li>
    <li>USB-C fast charging</li>
    <li>Foldable design with carrying case</li>
  </ul>
</div>
```""",
    },
]

EXTRACTION_TESTS = [
    {
        "id": "extract-summary",
        "category": "Info Extraction",
        "name": "论文摘要提取",
        "prompt": """Read this paper abstract and extract: title, authors, main_finding (one sentence), methodology (one sentence), and limitations (if any). Return as JSON.

```
SparseAttention-XL: Scaling Transformers to Million-Token Contexts

John Smith, Alice Chen, Bob Williams
MIT CSAIL, 2026

We introduce SparseAttention-XL, a novel attention mechanism that reduces the quadratic complexity of self-attention to O(n log n) while retaining 97.8% of the original model quality. Our approach uses learned dynamic sparsity patterns that adapt to input content, combined with a streaming memory mechanism for long-range dependencies. On a suite of 1,200 tasks across 8 domains, SparseAttention-XL achieves 3.2x faster inference and 68% lower peak memory compared to dense attention, with only a 0.3 perplexity increase. The method is particularly effective for sequences beyond 10k tokens, though it shows diminishing returns for sequences under 64 tokens. Training overhead is approximately 15% compared to standard transformers.
```""",
    },
    {
        "id": "extract-structured",
        "category": "Info Extraction",
        "name": "会议纪要结构化提取",
        "prompt": """Extract structured information from this meeting transcript into JSON. Output fields: date, attendees (list), key_decisions (list of {decision, made_by}), action_items (list of {task, assignee, deadline}). If a field is missing, set it to null.

```
Team Sync - May 28, 2023

Attendees: Alice, Bob, Charlie, Diana

Alice: Okay, let's start. First item — the dashboard XSS vulnerability. We need to fix that before the next release.
Bob: Agreed. I'll take that. Can have a patch by Friday.
Alice: Great, deadline Friday June 2nd for the XSS fix.

Charlie: On the database migration — I've been looking at the PostgreSQL migration plan. It's more complex than we thought.
Diana: Should we postpone?
Charlie: I think we should put it on hold until Q3. We don't have the bandwidth right now.
Alice: Makes sense. Database migration on hold until Q3.

Diana: For the email notification system, I researched a few providers. I recommend we go with SendGrid. Good API, reasonable pricing.
Alice: Any objections? None? Okay, SendGrid it is. Diana, can you set up the integration?
Diana: Yes, I'll have a prototype by next Wednesday, June 7th.

Bob: One more thing — the mobile app login flow needs UX review. The current flow has a 23% drop-off rate.
Alice: Good catch. Let's schedule a UX review session. I'll coordinate with the design team.
```""",
    },
]

LONG_TESTS = [
    {
        "id": "long-calculator",
        "category": "Long Task",
        "name": "多步骤计算器构建",
        "prompt": """Build a complete calculator class in Python step by step. Follow these instructions in order:

1. Create a `Calculator` class with an `__init__` method that initializes `history` (empty list) and `_value` (0).

2. Add methods `add(n)`, `subtract(n)`, `multiply(n)`, `divide(n)` that modify `_value` and log each operation to `history` with timestamp. Division by zero should raise ValueError.

3. Add a `history` property that returns a copy of the operation history list. Each entry should be a dict: {operation, operand, result, timestamp}.

4. Add an `undo()` method that reverts the last operation by replaying history from scratch (excluding the last entry).

5. Add input validation: all numeric operands must be int or float. Raise TypeError otherwise.

6. Add a `__str__` method that shows the current value and number of operations.

7. Write a demo section at the bottom that creates a Calculator, performs several operations, shows history, undoes one, and prints state. Use `if __name__ == '__main__'` guard.

Return the complete code.""",
    },
]

TIMING_TESTS = [
    {
        "id": "timing-simple",
        "category": "Timing",
        "name": "简单计算 (5次)",
        "prompt": "What is 123 * 456 + 789? Answer with just the number.",
        "runs": 5,
    },
    {
        "id": "timing-json",
        "category": "Timing",
        "name": "JSON生成 (3次)",
        "prompt": """Generate a valid JSON object with these fields:
- name: "benchmark-test"
- version: "1.0"
- scores: [95, 87, 92, 78, 88]
- metadata: {author: "AI", date: "2026-05-26", tags: ["test", "benchmark"]}
Return ONLY the JSON object, no explanation.""",
        "runs": 3,
    },
]

ALL_TESTS = CODING_TESTS + PLANNING_TESTS + SCRAPING_TESTS + EXTRACTION_TESTS + LONG_TESTS
TIMING_MAP = {t["id"]: t for t in TIMING_TESTS}


# ============================================================
# Scoring
# ============================================================

def score_coding(result):
    """Score coding tests: has_code, imports, docstring, type_hints, error_handling, etc."""
    reasons = []
    content = result.get("content", "")
    if not content:
        return 0, reasons

    if "```" in content or "def " in content or "class " in content:
        reasons.append("has_code")
    if "import " in content:
        reasons.append("imports")
    if '"""' in content or "'''" in content:
        reasons.append("docstring")
    if ": str" in content or ": bool" in content or ": int" in content or "->" in content:
        reasons.append("type_hints")
    if "raise" in content or "try" in content:
        reasons.append("error_handling")
    if "threading" in content or "thread" in content.lower():
        reasons.append("threading")
    if "http.server" in content:
        reasons.append("used_stdlib_http")

    return len(reasons), reasons


def score_planning(result):
    """Score planning tests: structure, services, endpoints, data_stores, roadmap."""
    reasons = []
    content = result.get("content", "")
    if not content:
        return 0, reasons

    if "service" in content.lower() or "microservice" in content.lower():
        reasons.append("has_services")
    if "endpoint" in content.lower() or "api" in content.lower():
        reasons.append("has_endpoints")
    if any(db in content.lower() for db in ["postgresql", "mysql", "mongodb", "redis", "kafka"]):
        reasons.append("has_datastores")
    if "month" in content.lower() or "phase" in content.lower() or "roadmap" in content.lower():
        reasons.append("has_roadmap")
    if "dependency" in content.lower() or "depends" in content.lower():
        reasons.append("has_dependencies")

    return len(reasons), reasons


def score_scraping(result):
    """Score scraping tests: json_output, valid_json, all_fields, ignores_sponsored."""
    reasons = []
    content = result.get("content", "")
    if not content:
        return 0, reasons

    # Try to find JSON in the response
    if "```json" in content or "```" in content:
        reasons.append("json_output")
    elif content.strip().startswith("[") or content.strip().startswith("{"):
        reasons.append("json_output")

    try:
        parsed = json.loads(content)
        reasons.append("valid_json")
        if isinstance(parsed, list):
            reasons.append(f"valid_json(list,{len(parsed)}items)")
        else:
            reasons.append("valid_json(dict)")
    except json.JSONDecodeError:
        # Try to extract JSON from markdown
        import re
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1))
                reasons.append("valid_json")
                if isinstance(parsed, list):
                    reasons.append(f"valid_json(list,{len(parsed)}items)")
                else:
                    reasons.append("valid_json(dict)")
            except json.JSONDecodeError:
                pass

    return len(reasons), reasons


def score_extraction(result):
    """Score extraction tests: json_output, valid_json, structured fields."""
    reasons = []
    content = result.get("content", "")
    if not content:
        return 0, reasons

    if content.strip().startswith("{") or "json" in content.lower():
        reasons.append("json_output")

    try:
        parsed = json.loads(content)
        reasons.append("valid_json(dict)")
    except json.JSONDecodeError:
        import re
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
        if match:
            try:
                json.loads(match.group(1))
                reasons.append("valid_json(dict)")
            except json.JSONDecodeError:
                pass

    return len(reasons), reasons


def score_long_task(result):
    """Score long tasks: check for each required step."""
    reasons = []
    content = result.get("content", "")
    if not content:
        return 0, reasons

    if "class Calculator" in content or "class Calculator:" in content:
        reasons.append("step1_class")
    if "def add" in content:
        reasons.append("step2_add")
    if "def subtract" in content:
        reasons.append("step2_sub")
    if "def multiply" in content:
        reasons.append("step2_mul")
    if "def divide" in content:
        reasons.append("step2_div")
    if "history" in content.lower():
        reasons.append("step3_history")
    if "def undo" in content:
        reasons.append("step4_undo")
    if "ValueError" in content or "TypeError" in content:
        reasons.append("step5_errors")
    if "__main__" in content or "if __name__" in content:
        reasons.append("step6_demo")
    if "add" in content and "subtract" in content and "multiply" in content and "divide" in content:
        reasons.append("all_operations")
    if "datetime" in content or "timestamp" in content.lower():
        reasons.append("timestamps")
    if "_value" in content:
        reasons.append("value_tracking")

    return len(reasons), reasons


SCORERS = {
    "Coding": score_coding,
    "Planning": score_planning,
    "Web Scraping": score_scraping,
    "Info Extraction": score_extraction,
    "Long Task": score_long_task,
}


# ============================================================
# API Call Helper
# ============================================================

def call_model(client, model, prompt, max_retries=2):
    """Call the model API with retry logic."""
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            content = response.choices[0].message.content or ""
            return {
                "success": True,
                "content": content,
                "attempts": attempt + 1,
                "length": len(content),
            }
        except Exception as e:
            if attempt < max_retries:
                time.sleep(2 ** attempt)
            else:
                return {
                    "success": False,
                    "error": str(e),
                    "attempts": attempt + 1,
                    "content": "",
                    "length": 0,
                }


# ============================================================
# Benchmark Runner
# ============================================================

def run_benchmark():
    init_clients()

    results = {}

    for model_id, cfg in MODELS.items():
        print(f"\n{'='*60}")
        print(f"  Testing: {cfg['label']} ({model_id})")
        print(f"{'='*60}")

        if not cfg["api_key"]:
            print(f"  ⚠️  Skipping {model_id}: API key not set (set BENCHMARK_{model_id.upper().replace('-', '_')}_API_KEY)")
            results[model_id] = {
                "label": cfg["label"],
                "model": cfg["model"],
                "base_url": cfg["base_url"],
                "error": "API key not configured",
                "results": {},
            }
            continue

        model_results = {}
        client = cfg["client"]
        model = cfg["model"]

        # Run all standard tests
        for test in ALL_TESTS:
            tid = test["id"]
            cat = test["category"]
            name = test["name"]
            print(f"\n  [{cat}] {name}...", end=" ", flush=True)

            start = time.time()
            result = call_model(client, model, test["prompt"])
            elapsed = time.time() - start

            if result["success"]:
                scorer = SCORERS.get(cat, lambda r: (0, []))
                score, reasons = scorer(result)
                result["elapsed"] = round(elapsed, 2)
                result["score"] = score
                result["score_reasons"] = reasons
                result["content_preview"] = result["content"][:200]
                del result["content"]  # Don't store full content in results file
                model_results[tid] = result
                print(f"✓ ({elapsed:.1f}s, score={score})")
            else:
                result["elapsed"] = round(elapsed, 2)
                model_results[tid] = result
                print(f"✗ ({elapsed:.1f}s) - {result.get('error', 'unknown')}")

        # Run timing tests
        timing_results = []
        for tdef in TIMING_TESTS:
            tid = tdef["id"]
            name = tdef["name"]
            runs = tdef.get("runs", 3)
            print(f"\n  [Timing] {name}...", end=" ", flush=True)

            times = []
            completed = 0
            for i in range(runs):
                start = time.time()
                result = call_model(client, model, tdef["prompt"], max_retries=1)
                elapsed = time.time() - start
                if result["success"]:
                    times.append(round(elapsed, 2))
                    completed += 1

            if times:
                avg = sum(times) / len(times)
                variance = sum((t - avg) ** 2 for t in times) / len(times)
                timing_results.append({
                    "id": tid,
                    "name": name,
                    "success": True,
                    "runs": runs,
                    "completed": completed,
                    "avg_time": round(avg, 2),
                    "min_time": round(min(times), 2),
                    "max_time": round(max(times), 2),
                    "variance": round(variance, 2),
                    "std_dev": round(variance ** 0.5, 2),
                    "times": times,
                    "consistent": variance < 1.0,
                })
                print(f"✓ avg={avg:.1f}s (n={completed}/{runs})")
            else:
                timing_results.append({
                    "id": tid,
                    "name": name,
                    "success": False,
                    "runs": runs,
                    "completed": 0,
                })
                print("✗ all failed")

        model_results["Timing"] = timing_results

        results[model_id] = {
            "label": cfg["label"],
            "model": cfg["model"],
            "base_url": cfg["base_url"],
            "results": model_results,
        }

    return results


def print_summary(results):
    """Print a summary table of results."""
    print(f"\n\n{'='*80}")
    print(f"  BENCHMARK SUMMARY")
    print(f"{'='*80}")

    for model_id, data in results.items():
        if "error" in data:
            print(f"\n  {data['label']}: SKIPPED ({data['error']})")
            continue

        model_results = data["results"]
        print(f"\n  {data['label']} ({model_id}):")

        # Categorize results
        for test_id, result in model_results.items():
            if test_id == "Timing":
                continue
            if isinstance(result, dict) and "success" in result:
                status = "✓" if result["success"] else "✗"
                score = result.get("score", "N/A")
                elapsed = result.get("elapsed", "N/A")
                print(f"    {status} {test_id}: score={score}, time={elapsed}s")

        # Timing summary
        timing = model_results.get("Timing", [])
        if timing:
            for t in timing:
                if t.get("success"):
                    print(f"    ⏱  {t['name']}: avg={t['avg_time']}s, consistent={t['consistent']}")


def save_results(results, filepath=None):
    """Save results to a JSON file."""
    if filepath is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"benchmark_deepseek_vs_mimo_{timestamp}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n  Results saved to: {filepath}")
    return filepath


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  DeepSeek V4 Pro vs MiMo V2.5 Pro — Benchmark")
    print("=" * 60)
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Check API keys
    missing = []
    for mid, cfg in MODELS.items():
        if not cfg["api_key"]:
            env_var = f"BENCHMARK_{mid.upper().replace('-', '_')}_API_KEY"
            missing.append(f"{cfg['label']} ({env_var})")

    if missing:
        print("  ⚠️  Missing API keys for: " + ", ".join(missing))
        print("  Set the corresponding environment variables and retry.")
        if len(missing) == len(MODELS):
            print("  No models configured. Exiting.")
            sys.exit(1)
        print()

    results = run_benchmark()
    print_summary(results)
    save_results(results)
