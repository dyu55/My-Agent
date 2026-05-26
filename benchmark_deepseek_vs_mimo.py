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
        "api_key": "sk-6837b4fcad1f4b5d90c5910bcd3481f0",
        "model": "deepseek-v4-pro",
        "label": "DeepSeek V4 Pro",
    },
    "mimo-v2.5-pro": {
        "client": None,
        "base_url": "https://token-plan-sgp.xiaomimimo.com/v1",
        "api_key": "tp-sba9vhdblxaj6lhst12lpivbg598s6n0tpk7ytlbh8wmm299",
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
<div class="product-card" data-id="SKU-88291">
  <h1 class="product-title">Pro Wireless Headphones ANC 2.0</h1>
  <div class="pricing">
    <span class="original-price">$299.99</span>
    <span class="current-price">$199.99</span>
  </div>
  <div class="availability in-stock">In Stock (47 units)</div>
  <div class="rating">
    <span class="stars">★★★★☆</span>
    <span class="rating-value">4.2</span>
    <span class="review-count">(1,234 reviews)</span>
  </div>
  <ul class="features">
    <li>Active Noise Cancellation 2.0</li>
    <li>40-hour battery life</li>
    <li>Bluetooth 5.3</li>
    <li>Multipoint connection</li>
    <li>USB-C fast charging</li>
  </ul>
</div>
```""",
    },
]

EXTRACTION_TESTS = [
    {
        "id": "extract-summarize",
        "category": "Info Extraction",
        "name": "长文摘要 + 关键信息提取",
        "prompt": """Summarize this research abstract into exactly 3 bullet points, each ≤30 words. Then extract these fields as key-value pairs: main_finding, methodology, sample_size, speedup_achieved, limitations.

---TEXT---
Recent advances in large language models (LLMs) have demonstrated remarkable capabilities across a wide range of natural language processing tasks. However, the deployment of these models in production environments presents significant challenges related to inference latency, memory consumption, and computational cost. In this paper, we propose SparseAttention-XL, a novel attention mechanism that reduces the quadratic complexity of standard self-attention to O(n log n) while maintaining 97.8% of the original model quality as measured by perplexity and downstream task performance. Our approach introduces a learned sparsity pattern that adapts dynamically to input sequences, allowing the model to focus computational resources on semantically important token interactions while pruning irrelevant connections. We evaluated SparseAttention-XL on a suite of 1,200 benchmark tasks across 8 domains, including question answering, summarization, code generation, and mathematical reasoning. Results show an average 3.2x speedup in inference latency and a 68% reduction in peak memory usage compared to dense attention baselines, with only a 0.3 point increase in perplexity. The method is architecture-agnostic and can be applied to both encoder-decoder and decoder-only models. Limitations include reduced effectiveness on very short sequences (< 64 tokens) and additional training overhead of approximately 15% during the fine-tuning phase.""",
    },
    {
        "id": "extract-structured",
        "category": "Info Extraction",
        "name": "会议记录 → 结构化JSON",
        "prompt": """Extract the following from this meeting transcript as JSON: date, attendees (list of names), key_decisions (list of {decision, made_by}), action_items (list of {task, owner, deadline}), and next_meeting. If a field is not mentioned, set it to null.

---MEETING TRANSCRIPT---
Alice: Alright, let's start the sprint planning for May 28th. Bob, can you take notes?
Bob: Sure. So our top priority is the payment gateway integration. Charlie, you mentioned you'd handle that?
Charlie: Yes, I've already started the Stripe integration. I expect to have a PR ready by Friday, June 2nd.
Alice: Good. Diana, what about the email notification system?
Diana: I did a spike on it. I think we should go with SendGrid. Much simpler API than SES. I'll have a design doc by EOD Thursday.
Bob: And the database migration from MySQL to PostgreSQL?
Alice: That's on hold until Q3. The cost analysis didn't justify the switch right now. Let's table it.
Charlie: What about the security audit findings?
Alice: Right. Decision: we need to fix the XSS vulnerabilities in the dashboard before the next release. Diana, can you own that?
Diana: Yes, I'll prioritize it after the email design doc.
Bob: Action items summary: Charlie - Stripe PR by June 2. Diana - SendGrid design doc by Thursday, XSS fixes after. Alice - anything for you?
Alice: I'll update the roadmap and schedule the Q3 planning session. Let's meet again next Wednesday, June 4th, same time.
Bob: Got it. Meeting adjourned!""",
    },
]

LONG_TASK_TESTS = [
    {
        "id": "long-calculator",
        "category": "Long Task",
        "name": "多步骤构建: Calculator 类",
        "prompt": """Build a Python Calculator class step by step. Complete ALL 6 steps in ONE response. Include only the final complete code.

Step 1: Create a `Calculator` class with `__init__` that initializes an empty history list and a `_value` state variable starting at 0.

Step 2: Add methods: `add(a, b)`, `subtract(a, b)`, `multiply(a, b)`, `divide(a, b)`. Each stores the operation in history as a dict: {operation, operands, result, timestamp}. Each updates `_value` to the latest result.

Step 3: Add `get_history(n=5)` that returns the last n operations.

Step 4: Add `undo()` that reverts the last operation and restores previous `_value`. Requires tracking previous state before each operation.

Step 5: Add error handling: division by zero raises ValueError, type checking on numeric inputs, and a `__str__` method showing current value and operation count.

Step 6: Write a `if __name__ == '__main__':` demo block that:
- Creates a Calculator
- Performs 3-4 operations
- Prints history
- Undoes one operation
- Shows the calculator state after undo
- Demonstrates error handling

Return the complete, runnable Python file.""",
    },
]

TIMING_TESTS = [
    {
        "id": "timing-simple",
        "category": "Timing",
        "name": "简单计算 (5次)",
        "prompt": "Calculate 12345 * 67890 and return ONLY the integer result. No other text.",
        "runs": 5,
    },
    {
        "id": "timing-json",
        "category": "Timing",
        "name": "JSON生成 (3次)",
        "prompt": "Generate a JSON array of exactly 20 objects with fields: id (1-20), name (common English first name), age (integer 18-65). Return ONLY valid JSON, no explanation or markdown.",
        "runs": 3,
    },
]

ALL_TEST_GROUPS = [
    ("Coding", CODING_TESTS),
    ("Planning", PLANNING_TESTS),
    ("Web Scraping", SCRAPING_TESTS),
    ("Info Extraction", EXTRACTION_TESTS),
    ("Long Task", LONG_TASK_TESTS),
    ("Timing", TIMING_TESTS),
]


# ============================================================
# API Call Helper
# ============================================================

def call_model(cfg, prompt, max_retries=2, max_tokens=4096):
    """Call model API with retries and exponential backoff."""
    client = cfg["client"]
    model = cfg["model"]

    for attempt in range(max_retries + 1):
        try:
            start = time.time()
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=max_tokens,
            )
            elapsed = time.time() - start
            content = response.choices[0].message.content or ""
            return {
                "success": True,
                "elapsed": round(elapsed, 2),
                "content": content,
                "length": len(content),
                "attempts": attempt + 1,
            }
        except Exception as e:
            err = str(e)
            if attempt < max_retries:
                wait = 10 * (attempt + 1)
                print(f"      ⚠️  Retry {attempt+1}/{max_retries} in {wait}s: {err[:100]}")
                time.sleep(wait)
            else:
                return {"success": False, "error": err[:200]}


# ============================================================
# Scoring Functions
# ============================================================

def score_coding(content, test_id):
    """Score coding response quality (max ~10)."""
    score = 0
    reasons = []

    has_code = "```" in content or "def " in content or "class " in content
    if has_code:
        score += 2
        reasons.append("has_code")

    if "import " in content or "from " in content:
        score += 1
        reasons.append("imports")

    if '"""' in content or "'''" in content:
        score += 1
        reasons.append("docstring")

    if "->" in content and (": str" in content or ": int" in content or ": bool" in content):
        score += 1
        reasons.append("type_hints")

    if "try" in content and "except" in content:
        score += 1
        reasons.append("error_handling")

    # Test-specific scoring
    if test_id == "code-medium" and ("OrderedDict" in content or "collections" in content):
        score += 1
        reasons.append("used_ordereddict")

    if test_id == "code-complex" and ("http.server" in content or "HTTPServer" in content):
        score += 1
        reasons.append("used_stdlib_http")

    if test_id == "code-debug":
        bug_keywords = ["bug", "fix", "issue", "problem", "error", "correct", "infinite", "stack"]
        found = [w for w in bug_keywords if w in content.lower()]
        if len(found) >= 3:
            score += 2
            reasons.append(f"identified_bugs:{len(found)}")
        elif found:
            score += 1

    if test_id == "code-review":
        checks = {
            "sql_injection": "sql injection" in content.lower(),
            "md5": "md5" in content.lower(),
            "debug_mode": "debug" in content.lower() and "false" in content.lower(),
            "path_traversal": "path" in content.lower() and "traversal" in content.lower(),
            "xss": "xss" in content.lower() or "cross" in content.lower(),
            "hashlib": "hashlib" in content.lower() or "bcrypt" in content.lower(),
        }
        found_checks = [k for k, v in checks.items() if v]
        score += min(len(found_checks), 4)
        if found_checks:
            reasons.append(f"found:{','.join(found_checks)}")

    return score, reasons


def score_planning(content):
    """Score planning quality (max ~8)."""
    score = 0
    reasons = []

    if "phase" in content.lower() or "milestone" in content.lower():
        score += 1
        reasons.append("phased")

    if "week" in content.lower() or "month" in content.lower() or "day" in content.lower():
        score += 1
        reasons.append("has_timeline")

    if "dependency" in content.lower() or "depend" in content.lower():
        score += 1
        reasons.append("dependencies")

    if "postgresql" in content.lower() or "redis" in content.lower() or "kafka" in content.lower():
        score += 1
        reasons.append("concrete_tech")

    lines = content.split("\n")
    bullet_count = sum(1 for l in lines if l.strip().startswith(("- ", "* ", "+ ", "1.", "2.")))
    if bullet_count > 8:
        score += 2
        reasons.append(f"well_structured({bullet_count})")
    elif bullet_count > 3:
        score += 1
        reasons.append(f"structured({bullet_count})")

    word_count = len(content.split())
    if word_count > 200:
        score += 1
        reasons.append("detailed")

    return min(score, 8), reasons


def score_scraping(content, test_id):
    """Score scraping/extraction quality (max ~8)."""
    score = 0
    reasons = []

    has_json = ("{" in content and "}" in content) or ("[" in content and "]" in content)
    if has_json:
        score += 2
        reasons.append("json_output")

    # Try to find and parse JSON block
    try:
        # Find JSON-like content
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = content.find(start_char)
            end = content.rfind(end_char)
            if start >= 0 and end > start:
                json_str = content[start:end+1]
                parsed = json.loads(json_str)
                score += 2
                reasons.append(f"valid_json({type(parsed).__name__})")
                break
    except Exception:
        if "```json" in content or "```" in content:
            # Try extracting from markdown code block
            try:
                block_start = content.find("```json")
                if block_start == -1:
                    block_start = content.find("```")
                if block_start >= 0:
                    block_end = content.find("```", block_start + 3)
                    if block_end > block_start:
                        json_str = content[block_start:block_end].replace("```json", "").replace("```", "").strip()
                        parsed = json.loads(json_str)
                        score += 2
                        reasons.append("valid_json_md")
            except Exception:
                pass

    return min(score, 8), reasons


def score_extraction(content):
    """Score information extraction quality."""
    return score_scraping(content, "extract")


def score_long_task(content):
    """Score long task completion (max ~12)."""
    score = 0
    reasons = []

    # Check how many steps are implemented
    step_indicators = {
        "class Calculator": "step1_class",
        "def add": "step2_add",
        "def subtract": "step2_sub",
        "def multiply": "step2_mul",
        "def divide": "step2_div",
        "get_history": "step3_history",
        "def undo": "step4_undo",
        "try" in content and "except" in content: "step5_errors",
        "if __name__": "step6_demo",
    }
    for indicator, step_name in step_indicators.items():
        if isinstance(indicator, str):
            if indicator in content:
                score += 1
                reasons.append(step_name)
        elif indicator:  # bool expression
            score += 1
            reasons.append(step_name)

    has_all_ops = all(op in content for op in ["def add", "def subtract", "def multiply", "def divide"])
    if has_all_ops:
        score += 1
        reasons.append("all_operations")

    # Check for history tracking
    if "timestamp" in content.lower() or "datetime" in content.lower():
        score += 1
        reasons.append("timestamps")

    # Check for value tracking
    if "_value" in content:
        score += 1
        reasons.append("value_tracking")

    return min(score, 12), reasons


# ============================================================
# Timing Test Runner
# ============================================================

def run_timing_tests(cfg, tests):
    """Run timing/scheduled tests with multiple iterations."""
    results = []
    for test in tests:
        runs = test.get("runs", 3)
        times = []
        print(f"    [{test['id']}] {test['name']} ({runs} runs):", end=" ", flush=True)
        for i in range(runs):
            result = call_model(cfg, test["prompt"], max_tokens=200)
            if result["success"]:
                times.append(result["elapsed"])
        print(f"{' '.join(f'{t:.1f}s' for t in times)}" if times else "ALL FAILED")

        if len(times) >= 2:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            variance = sum((t - avg_time) ** 2 for t in times) / len(times)

            results.append({
                "id": test["id"],
                "name": test["name"],
                "success": True,
                "runs": runs,
                "completed": len(times),
                "avg_time": round(avg_time, 2),
                "min_time": round(min_time, 2),
                "max_time": round(max_time, 2),
                "variance": round(variance, 2),
                "std_dev": round(variance ** 0.5, 2),
                "times": [round(t, 2) for t in times],
                "consistent": variance < (avg_time * 0.3),
            })
        elif len(times) == 1:
            results.append({
                "id": test["id"], "name": test["name"],
                "success": True, "runs": runs, "completed": 1,
                "avg_time": times[0], "times": times,
            })
        else:
            results.append({"id": test["id"], "name": test["name"], "success": False})

    return results


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 80)
    print("  DeepSeek V4 Pro  vs  MiMo V2.5 Pro  —  全面基准对比")
    print("=" * 80)
    print(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  测试维度: Coding | Planning | Web Scraping | Info Extraction | Long Task | Timing")
    print("=" * 80)

    init_clients()

    all_results = {}

    for model_id, cfg in MODELS.items():
        print(f"\n{'='*60}")
        print(f"  🔵 测试模型: {cfg['label']} ({cfg['model']})")
        print(f"{'='*60}")

        model_results = {}

        for group_name, tests in ALL_TEST_GROUPS:
            print(f"\n  ── {group_name} ──")

            if group_name == "Timing":
                model_results[group_name] = run_timing_tests(cfg, tests)
                continue

            for test in tests:
                tid = test["id"]
                print(f"    [{tid}] {test['name']}...", end=" ", flush=True)
                result = call_model(cfg, test["prompt"])

                if result["success"]:
                    # Score the response
                    score_funcs = {
                        "Coding": lambda c: score_coding(c, tid),
                        "Planning": score_planning,
                        "Web Scraping": lambda c: score_scraping(c, tid),
                        "Info Extraction": score_extraction,
                        "Long Task": score_long_task,
                    }
                    score_fn = score_funcs.get(group_name, lambda c: (0, []))
                    score, reasons = score_fn(result["content"])

                    result["score"] = score
                    result["score_reasons"] = reasons
                    print(f"✅ {result['elapsed']:.1f}s | {result['length']}chars | score={score} | {reasons}")

                    # Keep first 500 chars for manual inspection, discard rest
                    result["content_preview"] = result["content"][:500]
                    result.pop("content", None)
                else:
                    print(f"❌ {result.get('error', 'unknown')[:80]}")

                model_results[tid] = result
                time.sleep(1)

        all_results[model_id] = model_results

    # ============================================================
    # Report Generation
    # ============================================================
    print("\n\n" + "=" * 80)
    print("  📊 对比报告")
    print("=" * 80)

    model_ids = list(MODELS.keys())

    # Per-dimension detailed comparison
    for group_name, tests in ALL_TEST_GROUPS:
        print(f"\n{'─'*60}")
        print(f"  📌 {group_name}")
        print(f"{'─'*60}")

        if group_name == "Timing":
            for mid in model_ids:
                timing_results = all_results.get(mid, {}).get(group_name, [])
                for r in timing_results:
                    if r.get("success") and r.get("completed", 0) >= 1:
                        status = "🟢 STABLE" if r.get("consistent") else "🟡 VARIABLE"
                        print(f"    {MODELS[mid]['label']:22s} {r['name']:24s} "
                              f"avg={r.get('avg_time',0):.1f}s σ={r.get('std_dev',0):.1f}s "
                              f"[{r.get('min_time',0):.1f}s–{r.get('max_time',0):.1f}s] {status}")
                    else:
                        print(f"    {MODELS[mid]['label']:22s} {r['name']:24s} ❌")
            continue

        for test in tests:
            tid = test["id"]
            print(f"\n  [{tid}] {test['name']}")

            # Collect both results for side-by-side
            for mid in model_ids:
                r = all_results.get(mid, {}).get(tid, {})
                if r.get("success"):
                    label = MODELS[mid]['label']
                    print(f"    {label:22s} ⏱{r['elapsed']:.1f}s  📏{r['length']}chars  "
                          f"⭐{r.get('score','-')}  {r.get('score_reasons',[])}")
                else:
                    print(f"    {MODELS[mid]['label']:22s} ❌ {r.get('error','failed')[:60]}")

    # Overall summary
    print(f"\n{'='*80}")
    print(f"  📈 综合对比 Summary")
    print(f"{'='*80}")

    for mid in model_ids:
        total_score = 0
        total_time = 0
        total_tests_done = 0
        success_count = 0
        model_data = all_results.get(mid, {})

        for group_name, tests in ALL_TEST_GROUPS:
            if group_name == "Timing":
                for r in model_data.get(group_name, []):
                    if r.get("success"):
                        n = r.get("completed", r.get("runs", 1))
                        total_time += r.get("avg_time", 0) * n
                        total_tests_done += n
                        success_count += n
                continue

            for test in tests:
                r = model_data.get(test["id"], {})
                if r.get("success"):
                    total_score += r.get("score", 0)
                    total_time += r.get("elapsed", 0)
                    total_tests_done += 1
                    success_count += 1

        avg_time = total_time / total_tests_done if total_tests_done > 0 else 0

        # Winner indicators
        print(f"\n  {MODELS[mid]['label']}")
        print(f"    成功率:     {success_count}/{total_tests_done} ({100*success_count/max(total_tests_done,1):.0f}%)")
        print(f"    总分:       {total_score}")
        print(f"    总耗时:     {total_time:.1f}s")
        print(f"    平均响应:   {avg_time:.2f}s")

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"benchmark_deepseek_vs_mimo_{timestamp}.json"

    # Clean results for JSON (remove client objects)
    clean_results = {}
    for mid, data in all_results.items():
        clean_results[mid] = {
            "label": MODELS[mid]["label"],
            "model": MODELS[mid]["model"],
            "base_url": MODELS[mid]["base_url"],
            "results": data,
        }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(clean_results, f, indent=2, ensure_ascii=False)
    print(f"\n  📁 详细结果已保存: {output_file}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
