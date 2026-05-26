#!/usr/bin/env python3
"""
Multi-turn project building test (HARD MODE) — simulates a non-programmer user
sending plain-language prompts step by step to build a complex project.

Harder than v1: multi-file architecture, form validation, recurring transactions,
family members, dark mode, undo/redo, trend charts, custom export, keyboard shortcuts.

Tests 3 Gemini API models: gemma-4-26b-a4b-it, gemma-4-31b-it, gemini-2.5-flash
"""

import os
import sys
import time
import json
import shutil
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime
from pathlib import Path

os.chdir("/Users/donglingyu/Documents/MyAgent")
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import types

MODELS = [
    "gemini-2.5-flash",
    "gemma-4-31b-it",
    "gemma-4-26b-a4b-it",
]

RATE_LIMIT_SLEEP = 60
BASE_WORKSPACE = Path("workspace/multiturn_test_hard")

# ── HARDER project steps ────────────────────────────────────
# Requirements designed to differentiate model capabilities:
# - Multi-file architecture consistency
# - Form validation edge cases
# - Complex filtering logic
# - Undo/redo state management
# - Accessibility (keyboard nav, screen reader)
# - Recurring transaction scheduling
# - Multi-member tracking
# - Trend analysis (not just pie chart)
# - Dark mode with persistence
# - Custom export with filters

PROJECT_STEPS = [
    {
        "id": "step_01_init",
        "prompt": (
            "你好，我想做一个全家人都能用的记账网页。我完全不懂编程。"
            "我希望项目分成三个文件：一个放页面结构、一个放样式、一个放逻辑，"
            "不要把所有东西塞在一个文件里。"
            "先帮我搭好框架，能在浏览器打开看到基本布局就行。"
        ),
    },
    {
        "id": "step_02_form_validation",
        "prompt": (
            "现在加一个添加收支记录的表单。每笔记录要有：金额、类别（吃饭/交通/购物/"
            "房租/水电/娱乐/医疗/教育/工资/其他）、日期、备注（可选）、"
            "还有是谁花的（比如爸爸、妈妈、孩子，可以自己添加成员）。"
            "表单填完提交前要检查：金额必须是正数不能为空，"
            "类别必须选一个，日期不能填未来的日期，"
            "成员不能为空。填错了要在那个输入框旁边显示红色提示文字。"
        ),
    },
    {
        "id": "step_03_filter_search",
        "prompt": (
            "记录多了以后找起来很麻烦。帮我加搜索和筛选功能："
            "能按日期范围筛选（从哪天到哪天）、按类别筛选（多选，"
            "比如同时看吃饭和交通）、按成员筛选、"
            "还能按金额范围筛选（比如只看100块以上的支出）。"
            "还有一个搜索框，能搜备注里的关键词。"
            "筛选条件可以同时起作用，比如搜'超市'同时只显示吃饭和购物的记录。"
            "所有筛选条件显示在页面上，能随时清除。"
        ),
    },
    {
        "id": "step_04_recurring_undo",
        "prompt": (
            "两件事：\n"
            "第一，我每个月房租、水电、工资都是固定的，能不能设置自动重复的记录？"
            "比如设置'每月1号工资收入10000块'，然后每个月自动出现。"
            "要能看到哪些是自动生成的，还能取消某个自动规则。\n"
            "第二，我有时候会不小心删错记录或者改错数字，能不能加撤销和重做功能？"
            "就是我删了一条记录，能按Ctrl+Z撤销回来，还能按Ctrl+Y重做。"
            "撤销重做要对添加、删除、修改都有效。"
        ),
    },
    {
        "id": "step_05_ui_dark_mode",
        "prompt": (
            "界面现在需要好好美化一下。我希望：\n"
            "1. 配色方案好看温馨，适合家庭使用\n"
            "2. 手机上也好用，按钮和字都够大\n"
            "3. 加一个深色模式切换按钮，点了以后整个页面变成深色背景浅色字，"
            "适合晚上记账。再点一下切回浅色。\n"
            "4. 深色模式的偏好要记住，刷新页面后还是深色。\n"
            "5. 页面要能用键盘操作，比如Tab键切换输入框，Enter提交表单。"
        ),
    },
    {
        "id": "step_06_charts_trend",
        "prompt": (
            "帮我做数据可视化，不只是简单的饼图：\n"
            "1. 一个饼图显示本月各支出类别的占比\n"
            "2. 一个折线图显示最近6个月每个月的总支出变化趋势，"
            "这样我能看出来哪个月花多了\n"
            "3. 一个柱状图对比本月各成员的支出，看谁花最多\n"
            "4. 图表上面显示月份选择器，能切换查看不同月份的数据\n"
            "图表要能响应窗口大小变化，手机上也能看清楚。"
        ),
    },
    {
        "id": "step_07_budget_multi",
        "prompt": (
            "预算功能要做细致一点：\n"
            "1. 能设置月总预算（比如5000块），超过80%就显示黄色警告，"
            "超过100%显示红色警告\n"
            "2. 能给每个类别单独设预算，比如吃饭1500、交通500，超了要提醒\n"
            "3. 能给每个成员设预算上限，比如孩子一个月零花钱最多500块\n"
            "4. 预算设置页面要清晰，一眼能看出总预算、分类预算、成员预算"
            "各自用了多少百分比\n"
            "5. 当某类支出超过预算时，在添加新记录时就弹提示："
            "'注意：吃饭已经花了1400，预算还剩100'"
        ),
    },
    {
        "id": "step_08_export_backup",
        "prompt": (
            "导出和数据备份：\n"
            "1. 能导出成CSV文件，但导出前能选择：导出全部还是按日期范围导出、"
            "按类别导出、按成员导出。导出的列可以勾选要哪些字段。\n"
            "2. 能导出成一个适合打印的页面，显示当月收支汇总报表，"
            "包括总收支、分类汇总、成员汇总、预算执行情况。\n"
            "3. 能备份全部数据到一个JSON文件（包括记录、设置、预算、成员），"
            "也能从备份文件恢复。备份文件名带上日期。"
        ),
    },
    {
        "id": "step_09_data_management",
        "prompt": (
            "数据管理功能：\n"
            "1. 能编辑已有的记录（点了编辑按钮后，表单自动填上原来的数据，修改后保存）\n"
            "2. 能批量删除记录（勾选多条然后一键删除，删除前要确认）\n"
            "3. 能对记录排序：按日期、按金额、按类别，点一下升序再点降序\n"
            "4. 页面顶部显示总记录数、当前筛选后的记录数\n"
            "5. 如果没有任何记录，页面显示一个友好的空状态提示，引导用户添加第一笔记录\n"
            "6. 所有对数据的操作都要支持撤销重做（和之前的Ctrl+Z功能配合）"
        ),
    },
    {
        "id": "step_10_polish",
        "prompt": (
            "最后做一些完善：\n"
            "1. 页面加载时如果数据量大（超过500条记录），列表要分批显示，"
            "不要一次加载卡住浏览器（每页显示20条，下面有翻页按钮）\n"
            "2. 加一个仪表盘概览页，顶部一行卡片显示：本月收入、本月支出、"
            "本月结余、预算使用率，每个卡片用不同颜色\n"
            "3. 首页顶部显示最近的5条记录，方便快速查看\n"
            "4. 当月的第一天自动弹出提示：'新的一月开始了！上个月你总共花了X元，"
            "主要在Y类别上。这个月要继续加油！'\n"
            "5. 整体性能优化：如果操作卡顿，想办法让它流畅。"
        ),
    },
]


def log(msg: str):
    print(msg)
    sys.stdout.flush()


def is_rate_limit(err: str) -> bool:
    return "429" in err or "RESOURCE_EXHAUSTED" in err


def is_retryable(err: str) -> bool:
    return (is_rate_limit(err) or "500" in err or "503" in err
            or "internal error" in err.lower() or "timeout" in err.lower()
            or "deadline" in err.lower() or "canceled" in err.lower()
            or "connection reset" in err.lower()
            or "connection aborted" in err.lower()
            or "broken pipe" in err.lower()
            or "[errno 54]" in err.lower() or "[errno 32]" in err.lower())


def run_model(model_name: str, workspace_path: Path) -> dict:
    short = model_name.replace("gemma-4-", "").replace("-it", "").replace("gemini-", "")
    log(f"\n{'='*60}")
    log(f"MODEL: {model_name}")
    log(f"{'='*60}")

    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    workspace_path.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("GEMINI_API_KEY", "")
    client = genai.Client(api_key=api_key)

    API_TIMEOUT = 300  # 5 min per call

    def call_api(model, contents):
        """Call Gemini API in a thread with timeout."""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                client.models.generate_content,
                model=model,
                contents=contents,
            )
            return future.result(timeout=API_TIMEOUT)

    contents: list[types.Content] = []
    step_results = []
    start_time = time.time()
    total_prompt_chars = 0
    total_response_chars = 0

    for i, step in enumerate(PROJECT_STEPS):
        step_id = step["id"]
        prompt = step["prompt"]
        log(f"\n[{i+1}/{len(PROJECT_STEPS)}] {step_id}")
        # Show first line of prompt
        first_line = prompt.strip().split("\n")[0][:100]
        log(f"  {first_line}...")

        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=prompt)],
        ))
        total_prompt_chars += len(prompt)

        max_retries = 5
        response_text = ""
        success = False
        error_msg = ""

        for attempt in range(max_retries):
            try:
                response = call_api(model_name, contents)
                response_text = response.text
                success = True
                break
            except FuturesTimeoutError:
                error_msg = "API call timed out after 5 minutes"
                log(f"  Timeout, retrying (attempt {attempt+1}/{max_retries})...")
                time.sleep(10)
                continue
            except Exception as e:
                error_msg = str(e)
                if is_rate_limit(error_msg):
                    log(f"  429, waiting {RATE_LIMIT_SLEEP}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(RATE_LIMIT_SLEEP)
                elif is_retryable(error_msg):
                    log(f"  Retryable error, waiting 30s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(30)
                else:
                    break

        elapsed = time.time() - start_time

        if success:
            total_response_chars += len(response_text)
            contents.append(types.Content(
                role="model",
                parts=[types.Part(text=response_text)],
            ))
            log(f"  OK {len(response_text)} chars | total: {elapsed:.0f}s")
            (workspace_path / f"{step_id}.txt").write_text(response_text, encoding="utf-8")
        else:
            log(f"  FAIL: {error_msg[:150]}")

        step_results.append({
            "step_id": step_id,
            "prompt": prompt,
            "response_preview": response_text[:500] if success else "",
            "response_length": len(response_text) if success else 0,
            "success": success,
            "error": error_msg[:500] if error_msg else "",
            "elapsed_total_s": round(elapsed, 1),
        })

        time.sleep(2)

    total_elapsed = time.time() - start_time
    passed = sum(1 for r in step_results if r["success"])

    log(f"\n  {model_name}: {passed}/{len(PROJECT_STEPS)} steps | {total_elapsed:.0f}s | "
        f"prompt: {total_prompt_chars} chars | response: {total_response_chars} chars")

    return {
        "summary": {
            "model": model_name,
            "total_steps": len(PROJECT_STEPS),
            "passed": passed,
            "failed": len(PROJECT_STEPS) - passed,
            "total_elapsed_s": round(total_elapsed, 1),
            "total_prompt_chars": total_prompt_chars,
            "total_response_chars": total_response_chars,
            "workspace": str(workspace_path),
        },
        "steps": step_results,
    }


def main():
    log("=" * 70)
    log("MULTI-TURN HARD MODE — Project Building Test (Gemini API)")
    log(f"Models: {len(MODELS)} | Steps: {len(PROJECT_STEPS)}")
    log(f"Project: Family Finance Tracker (multi-file, advanced features)")
    log("=" * 70)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"logs/multiturn_hard_results_{timestamp}.json"
    os.makedirs("logs", exist_ok=True)
    os.makedirs(BASE_WORKSPACE, exist_ok=True)

    all_results = {}

    for mi, model_name in enumerate(MODELS):
        short = model_name.replace("gemma-4-", "").replace("-it", "").replace("gemini-", "")
        ws = BASE_WORKSPACE / short

        try:
            result = run_model(model_name, ws)
            all_results[model_name] = result
        except Exception as e:
            log(f"\n  Fatal: {e}")
            all_results[model_name] = {
                "summary": {"model": model_name, "error": str(e), "passed": 0, "total_steps": len(PROJECT_STEPS)},
                "steps": [],
            }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        if mi < len(MODELS) - 1:
            log(f"\n  Waiting 30s before next model...")
            time.sleep(30)

    log("\n" + "=" * 70)
    log("FINAL SUMMARY — HARD MODE")
    log("=" * 70)
    for model_name, data in all_results.items():
        s = data.get("summary", {})
        log(f"  {model_name}: {s.get('passed',0)}/{s.get('total_steps',10)} | "
            f"{s.get('total_elapsed_s',0):.0f}s | {s.get('total_response_chars',0):,} chars")
    log(f"\nResults: {output_file}")


if __name__ == "__main__":
    main()
