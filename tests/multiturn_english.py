#!/usr/bin/env python3
"""
Multi-turn project building test — ALL ENGLISH prompts.
Simulates a non-programmer user building a complex project step by step.

Easy mode (8 steps): Personal finance tracker
Hard mode (6 steps): Family finance tracker with advanced features

Tests 3 Gemini API models: gemma-4-26b-a4b-it, gemma-4-31b-it, gemini-2.5-flash
"""

import os, sys, time, json, shutil, multiprocessing
from datetime import datetime
from pathlib import Path

os.chdir("/Users/donglingyu/Documents/MyAgent")
from dotenv import load_dotenv; load_dotenv()

from google import genai
from google.genai import types

MODELS = ["gemini-2.5-flash", "gemma-4-31b-it", "gemma-4-26b-a4b-it"]
RATE_LIMIT_SLEEP = 60
API_TIMEOUT = 240
BASE_WORKSPACE = Path("workspace/multiturn_english")

# ── EASY MODE (8 steps) ────────────────────────────────────
EASY_STEPS = [
    {
        "id": "e01_init",
        "prompt": (
            "Hi, I want to build a personal finance tracker web app. "
            "I don't know how to code at all. Can you help me set it up from scratch? "
            "I want to be able to open it in my browser."
        ),
    },
    {
        "id": "e02_form",
        "prompt": (
            "Now I need to be able to add income and expense records. Each record should have: "
            "an amount (how much money), a category (like food, transport, shopping, salary), "
            "an optional note, and a date. Add a form to the page where I can fill in and submit records."
        ),
    },
    {
        "id": "e03_stats",
        "prompt": (
            "Can you show some statistics on the page? I want to see: total spending this month, "
            "total income, and what's left over. My monthly budget is $5000. "
            "If I go over budget, show a big obvious red warning."
        ),
    },
    {
        "id": "e04_persist",
        "prompt": (
            "I noticed the data disappears when I close the browser. Can you make it save "
            "in the browser so my data stays when I close and reopen? No server, just my own computer."
        ),
    },
    {
        "id": "e05_ui",
        "prompt": (
            "The interface looks pretty bare. Can you make it look nicer? Warm, cozy colors "
            "suitable for home budgeting. Should also look good and be easy to use on my phone."
        ),
    },
    {
        "id": "e06_chart",
        "prompt": (
            "Add a pie chart or bar chart so I can see at a glance where my money went this month. "
            "Like how much I spent on food vs transport vs shopping."
        ),
    },
    {
        "id": "e07_budget",
        "prompt": (
            "I want to set a budget limit for each spending category: like food $1500, "
            "transport $500, shopping $1000. If any category goes over, show a clear warning "
            "on the page. The budget amounts should be editable, not hard-coded."
        ),
    },
    {
        "id": "e08_export",
        "prompt": (
            "Finally, add an export feature. Let me export my records as a spreadsheet file "
            "(like Excel or CSV) so I can use it for taxes. Include all fields: "
            "amount, category, note, date."
        ),
    },
]

# ── HARD MODE (6 steps) ────────────────────────────────────
HARD_STEPS = [
    {
        "id": "h01_init",
        "prompt": (
            "Build a family finance tracker with 3 separate files: index.html (page structure), "
            "style.css (styling), app.js (logic). Set up the basic framework so it opens "
            "in a browser with a title and an empty record list area."
        ),
    },
    {
        "id": "h02_form",
        "prompt": (
            "Add a transaction form. Fields: amount (must be a positive number, required), "
            "category (food/transport/shopping/rent/utilities/entertainment/medical/education/salary/other, "
            "required), date (cannot be a future date), note (optional), "
            "family member (required, users can add and remove members). "
            "Validate the form: show red inline error messages next to each field — "
            "'Please enter a positive amount' for bad amount, 'Date cannot be in the future' for future dates, "
            "'Please select' for empty category or member. Use localStorage to persist data."
        ),
    },
    {
        "id": "h03_filter_undo",
        "prompt": (
            "Two things:\n"
            "1. Add filters: date range, multi-select categories, member, amount range (e.g. >$100), "
            "keyword search in notes. Filters must work together simultaneously. Include a clear button.\n"
            "2. Add undo/redo: Ctrl+Z to undo, Ctrl+Y to redo. Must work for add, delete, edit, "
            "and batch delete operations. Implement with an operation stack."
        ),
    },
    {
        "id": "h04_dark_chart",
        "prompt": (
            "1. Add a dark mode toggle button. Save the preference to localStorage so it persists "
            "after refresh. Use a warm, cozy color scheme. Make buttons and text large enough for mobile.\n"
            "2. Add charts: a pie chart showing spending by category this month, "
            "a line chart showing total spending trend over the last 6 months, "
            "a bar chart comparing spending by family member this month. "
            "Add a month selector above the charts to switch between months. Charts must be responsive."
        ),
    },
    {
        "id": "h05_budget_recurring",
        "prompt": (
            "1. Three-level budget system: total monthly budget (>80% yellow warning, >100% red warning), "
            "per-category budgets (each category has its own limit), per-member budgets. "
            "When adding a new record, show an alert if that category or member is near or over budget. "
            "Show usage percentages on the budget settings page.\n"
            "2. Recurring transactions: set up rules for automatic entries (e.g. $10000 salary on the 1st "
            "of every month). Auto-generated records should be clearly marked. Users can view and cancel rules."
        ),
    },
    {
        "id": "h06_export_polish",
        "prompt": (
            "1. Export: CSV export with options to select date range, categories, members, and which "
            "fields to include. A printable monthly report page showing total income/expense, "
            "category breakdown, member breakdown, and budget performance. "
            "Full JSON backup and restore with dated filenames.\n"
            "2. Data management: edit existing records, batch delete with confirmation dialog, "
            "sort by date/amount/category (click to toggle asc/desc), paginate 20 records per page, "
            "show a friendly empty state when no records exist. "
            "Dashboard cards at the top: monthly income, expense, balance, budget usage rate. "
            "Show the 5 most recent records for quick access. "
            "When there are more than 500 records, use paginated loading to avoid browser lag."
        ),
    },
]


def log(msg: str):
    print(msg, flush=True)


def _api_worker(model, contents, queue):
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
        resp = client.models.generate_content(model=model, contents=contents)
        queue.put(("ok", resp.text))
    except Exception as e:
        queue.put(("err", str(e)))


def call_api(model, contents, timeout=API_TIMEOUT):
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=_api_worker, args=(model, contents, queue))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        raise TimeoutError(f"API call exceeded {timeout}s")
    status, payload = queue.get()
    if status == "err":
        raise RuntimeError(payload)
    return payload


def is_rate_limit(err: str) -> bool:
    return "429" in err or "RESOURCE_EXHAUSTED" in err


def run_test(model_name: str, workspace_path: Path, steps: list, label: str) -> dict:
    log(f"\n{'='*50}")
    log(f"[{label}] MODEL: {model_name}")
    log(f"{'='*50}")

    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    workspace_path.mkdir(parents=True, exist_ok=True)

    contents: list[types.Content] = []
    step_results = []
    start_time = time.time()
    total_chars = 0

    for i, step in enumerate(steps):
        sid = step["id"]
        prompt = step["prompt"]
        log(f"\n[{i+1}/{len(steps)}] {sid}: {prompt[:100]}...")

        contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))

        success = False
        error_msg = ""
        response_text = ""

        for attempt in range(5):
            try:
                response_text = call_api(model_name, contents)
                success = True
                break
            except TimeoutError:
                log(f"  Timeout {API_TIMEOUT}s, retry {attempt+1}/5")
                time.sleep(5)
            except Exception as e:
                error_msg = str(e)
                if is_rate_limit(error_msg):
                    log(f"  429, wait {RATE_LIMIT_SLEEP}s")
                    time.sleep(RATE_LIMIT_SLEEP)
                elif any(x in error_msg.lower() for x in [
                    "500", "503", "internal error", "connection reset",
                    "broken pipe", "timeout", "deadline",
                ]):
                    log(f"  Retryable ({error_msg[:60]}), wait 20s")
                    time.sleep(20)
                else:
                    break

        elapsed = time.time() - start_time

        if success:
            total_chars += len(response_text)
            contents.append(types.Content(role="model", parts=[types.Part(text=response_text)]))
            (workspace_path / f"{sid}.txt").write_text(response_text, encoding="utf-8")
            log(f"  OK {len(response_text)} chars | {elapsed:.0f}s")
        else:
            log(f"  FAIL: {error_msg[:120]}")

        step_results.append({
            "step_id": sid, "prompt": prompt,
            "response_length": len(response_text) if success else 0,
            "success": success, "error": error_msg[:500] if error_msg else "",
            "elapsed_total_s": round(elapsed, 1),
        })
        time.sleep(2)

    total_elapsed = time.time() - start_time
    passed = sum(1 for r in step_results if r["success"])

    log(f"\n  [{label}] {model_name}: {passed}/{len(steps)} | {total_elapsed:.0f}s | {total_chars:,} chars")

    return {
        "summary": {
            "label": label, "model": model_name,
            "total_steps": len(steps), "passed": passed,
            "failed": len(steps) - passed,
            "total_elapsed_s": round(total_elapsed, 1),
            "total_response_chars": total_chars,
        },
        "steps": step_results,
    }


def main():
    log(f"{'='*60}")
    log(f"MULTI-TURN ENGLISH TEST — Easy (8) + Hard (6)")
    log(f"Models: {len(MODELS)}")
    log(f"{'='*60}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"logs/multiturn_english_{ts}.json"
    os.makedirs("logs", exist_ok=True)
    os.makedirs(BASE_WORKSPACE, exist_ok=True)

    all_results = {}

    # Run easy mode
    for mi, model_name in enumerate(MODELS):
        short = model_name.replace("gemma-4-", "").replace("-it", "").replace("gemini-", "")
        ws = BASE_WORKSPACE / f"easy_{short}"
        key = f"easy_{model_name}"
        try:
            all_results[key] = run_test(model_name, ws, EASY_STEPS, "EASY")
        except Exception as e:
            log(f"\n  Fatal: {e}")
            all_results[key] = {"summary": {"model": model_name, "label": "EASY", "error": str(e), "passed": 0, "total_steps": len(EASY_STEPS)}, "steps": []}
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        if mi < len(MODELS) - 1:
            log("\n  Wait 30s...")
            time.sleep(30)

    # Run hard mode
    for mi, model_name in enumerate(MODELS):
        short = model_name.replace("gemma-4-", "").replace("-it", "").replace("gemini-", "")
        ws = BASE_WORKSPACE / f"hard_{short}"
        key = f"hard_{model_name}"
        try:
            all_results[key] = run_test(model_name, ws, HARD_STEPS, "HARD")
        except Exception as e:
            log(f"\n  Fatal: {e}")
            all_results[key] = {"summary": {"model": model_name, "label": "HARD", "error": str(e), "passed": 0, "total_steps": len(HARD_STEPS)}, "steps": []}
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        if mi < len(MODELS) - 1:
            log("\n  Wait 30s...")
            time.sleep(30)

    # ── final ──────────────────────────────────────────────
    log(f"\n{'='*60}")
    log("FINAL SUMMARY — ENGLISH PROMPTS")
    log(f"{'='*60}")
    for mode in ["easy", "hard"]:
        log(f"\n--- {mode.upper()} MODE ---")
        for model_name in MODELS:
            key = f"{mode}_{model_name}"
            d = all_results.get(key, {}).get("summary", {})
            log(f"  {model_name}: {d.get('passed',0)}/{d.get('total_steps','?')} | {d.get('total_elapsed_s',0):.0f}s | {d.get('total_response_chars',0):,} chars")
    log(f"\nResults: {output_file}")


if __name__ == "__main__":
    main()
