#!/usr/bin/env python3
"""
Compact hard-mode multi-turn test — non-programmer Chinese prompts,
fewer steps, tighter prompts, multiprocessing timeout per API call.
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
API_TIMEOUT = 240  # 4 min
BASE_WORKSPACE = Path("workspace/multiturn_hard2")

# 6 steps — tight, hard requirements in compact prompts
STEPS = [
    {
        "id": "01_init",
        "prompt": (
            "做一个全家记账网页，分三个文件：index.html（结构）、style.css（样式）、app.js（逻辑）。"
            "先搭好框架，浏览器能打开看到标题和空白的记录列表区域就行。"
        ),
    },
    {
        "id": "02_form",
        "prompt": (
            "加收支记录表单。字段：金额（正数必填）、类别（吃饭/交通/购物/房租/水电/娱乐/医疗/教育/工资/其他，必选）、"
            "日期（不能填未来日期）、备注（可选）、成员（可自己添加删除成员，必选）。"
            "表单校验：金额为空或<=0时输入框旁红色提示'请输入正数金额'，日期超未来提示'日期不能是未来'，"
            "类别/成员未选提示'请选择'。用localStorage存数据。"
        ),
    },
    {
        "id": "03_filter_undo",
        "prompt": (
            "两件事：\n"
            "1. 筛选区：日期范围、类别多选、成员单选、金额范围（如>100块）、关键词搜索备注。条件可叠加。有清除按钮。\n"
            "2. 撤销重做：Ctrl+Z撤销，Ctrl+Y重做。对添加/删除/编辑/批量删除都有效。用操作栈实现。"
        ),
    },
    {
        "id": "04_dark_chart",
        "prompt": (
            "1. 深色模式切换按钮，偏好存localStorage，刷新记住。界面温馨配色，手机上按钮和字够大。\n"
            "2. 图表区：饼图（本月各类支出占比）、折线图（近6月支出趋势）、柱状图（本月各成员支出对比）。"
            "图表上方有月份选择器能切换。图表随窗口大小自适应。"
        ),
    },
    {
        "id": "05_budget_recurring",
        "prompt": (
            "1. 三级预算：总预算(>80%黄 >100%红)、分类预算(每类单独设)、成员预算。"
            "添加记录时若该类别/成员即将超预算弹提醒。预算设置页显示各自使用百分比。\n"
            "2. 固定收支自动重复：设置规则(如每月1日工资10000)，到期自动生成记录。能查看和取消规则。"
        ),
    },
    {
        "id": "06_export_polish",
        "prompt": (
            "1. 导出CSV可自选日期范围、类别、成员、字段列。可导出打印版月报(含总收支+分类汇总+成员汇总+预算执行率)。"
            "JSON全量备份和恢复，备份文件名带日期。\n"
            "2. 记录列表：可编辑、批量删除(确认框)、按日期/金额/类别排序、分页每页20条、空状态提示。"
            "顶部仪表盘卡片：本月收入/支出/结余/预算使用率。最近5条记录快速查看。"
            "超过500条记录时分页加载避免卡顿。"
        ),
    },
]


def log(msg: str):
    print(msg, flush=True)


def _api_worker(model, contents, queue):
    """Run in child process. Returns result via queue."""
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY", ""))
        resp = client.models.generate_content(model=model, contents=contents)
        queue.put(("ok", resp.text))
    except Exception as e:
        queue.put(("err", str(e)))


def call_api(model, contents, timeout=API_TIMEOUT):
    """Call Gemini API with real process timeout."""
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


def run_model(model_name: str, workspace_path: Path) -> dict:
    log(f"\n{'='*50}")
    log(f"MODEL: {model_name}")
    log(f"{'='*50}")

    if workspace_path.exists():
        shutil.rmtree(workspace_path)
    workspace_path.mkdir(parents=True, exist_ok=True)

    contents: list[types.Content] = []
    step_results = []
    start_time = time.time()

    for i, step in enumerate(STEPS):
        sid = step["id"]
        prompt = step["prompt"]
        log(f"\n[{i+1}/{len(STEPS)}] {sid}: {prompt[:80]}...")

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
                elif any(x in error_msg.lower() for x in ["500", "503", "internal error", "connection reset", "broken pipe", "timeout"]):
                    log(f"  Retryable ({error_msg[:60]}), wait 20s")
                    time.sleep(20)
                else:
                    break

        elapsed = time.time() - start_time

        if success:
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
    total_chars = sum(r["response_length"] for r in step_results)

    log(f"\n  {model_name}: {passed}/{len(STEPS)} | {total_elapsed:.0f}s | {total_chars:,} chars")

    return {
        "summary": {"model": model_name, "total_steps": len(STEPS), "passed": passed,
                     "failed": len(STEPS) - passed, "total_elapsed_s": round(total_elapsed, 1),
                     "total_response_chars": total_chars, "workspace": str(workspace_path)},
        "steps": step_results,
    }


def main():
    log(f"{'='*60}")
    log(f"HARD MODE v2 — {len(MODELS)} models × {len(STEPS)} steps (multiprocessing timeout)")
    log(f"{'='*60}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"logs/multiturn_hard2_{ts}.json"
    os.makedirs("logs", exist_ok=True)
    os.makedirs(BASE_WORKSPACE, exist_ok=True)

    results = {}
    for mi, model_name in enumerate(MODELS):
        short = model_name.replace("gemma-4-", "").replace("-it", "").replace("gemini-", "")
        ws = BASE_WORKSPACE / short
        try:
            results[model_name] = run_model(model_name, ws)
        except Exception as e:
            log(f"\n  Fatal: {e}")
            results[model_name] = {"summary": {"model": model_name, "error": str(e), "passed": 0, "total_steps": len(STEPS)}, "steps": []}

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        if mi < len(MODELS) - 1:
            log(f"\n  Wait 30s...")
            time.sleep(30)

    log(f"\n{'='*60}")
    log("FINAL")
    log(f"{'='*60}")
    for m, d in results.items():
        s = d["summary"]
        log(f"  {m}: {s['passed']}/{s['total_steps']} | {s.get('total_elapsed_s',0):.0f}s | {s.get('total_response_chars',0):,} chars")
    log(f"\nResults: {output_file}")


if __name__ == "__main__":
    main()
