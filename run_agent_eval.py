#!/usr/bin/env python3
"""
MyAgent Autonomous Evaluation Runner
Executes MyAgent on a transaction-supporting KV store coding task using three different models.
Captures performance metrics, parses steps, runs pytest on generated outputs, and saves results.
"""

import os
import sys
import time
import json
import shutil
import subprocess
from pathlib import Path

# Adjust working directory to project root
os.chdir('/Users/donglingyu/Documents/MyAgent')

TASK_PROMPT = (
    "Implement a Key-Value Store class in `kv_store.py` that supports:\n"
    "1. Time-to-live (TTL) expiration for keys.\n"
    "2. Transaction operations: `begin()`, `commit()`, and `rollback()` (supporting basic nested transactions or standard rollback).\n"
    "3. Saving and loading data from a JSON file.\n"
    "Write a comprehensive set of unit tests in `test_kv_store.py` and run pytest to verify it."
)

MODELS = [
    ("gemini-2.5-flash", "flash", "workspace_flash"),
    ("gemma-4-31b-it", "31b", "workspace_31b"),
    ("gemma-4-26b-a4b-it", "26b", "workspace_26b"),
]

def clean_workspace(path_str):
    path = Path(path_str)
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)

def run_pytest(workspace_path):
    # Try running pytest on the generated test file
    test_file = Path(workspace_path) / "test_kv_store.py"
    if not test_file.exists():
        return False, "test_kv_store.py was not created"
    
    try:
        # Run pytest inside the workspace context
        result = subprocess.run(
            ["pytest", str(test_file)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, "All tests passed"
        else:
            return False, f"pytest failed with return code {result.returncode}:\n{result.stdout}\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "pytest timed out"
    except Exception as e:
        return False, f"Failed to run pytest: {str(e)}"

def count_agent_steps(log_content):
    # Estimate agent steps based on plan progress lines or log patterns
    completed = log_content.count("✅")
    if completed > 0:
        # Subtract the final summary check if present
        completed = max(0, completed - 1)
    
    failures = log_content.count("❌")
    retries = log_content.count("Rate Limit/Error Hit") + log_content.count("重试中")
    
    return {
        "completed_tasks": completed,
        "retries": retries,
        "failures": failures,
        "total_attempts": completed + retries + failures
    }

def main():
    print("=" * 80)
    print("MYAGENT AUTONOMOUS FRAMEWORK EVALUATION")
    print("=" * 80)
    
    results = {}
    
    for i, (model_name, model_id, workspace_dir) in enumerate(MODELS):
        print(f"\n[{i+1}/{len(MODELS)}] Running MyAgent with Model: {model_name}...")
        print(f"Workspace: {workspace_dir}")
        
        # 1. Clean workspace
        clean_workspace(workspace_dir)
        
        # 2. Record start time
        start_time = time.time()
        
        # 3. Launch MyAgent subprocess
        cmd = [
            sys.executable, "main.py",
            "--provider", "gemini",
            "--model", model_name,
            "--workspace", workspace_dir,
            TASK_PROMPT
        ]
        
        log_file_path = f"agent_eval_{model_id}.log"
        print(f"Executing: {' '.join(cmd)}")
        print(f"Logging output to {log_file_path}...")
        
        success = False
        error_msg = ""
        
        with open(log_file_path, "w", encoding="utf-8") as lf:
            try:
                # Set environment for the subprocess
                env = os.environ.copy()
                # Run with 15 minutes timeout per agent run
                result = subprocess.run(
                    cmd,
                    stdout=lf,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env,
                    timeout=900
                )
                if result.returncode == 0:
                    success = True
                else:
                    error_msg = f"Agent finished with exit code {result.returncode}"
            except subprocess.TimeoutExpired:
                error_msg = "Agent execution timed out (exceeded 15 minutes)"
                lf.write("\n[TIMEOUT EXPIRED] Subprocess terminated after 15 minutes.\n")
            except Exception as e:
                error_msg = f"Failed to execute agent process: {str(e)}"
                lf.write(f"\n[EXCEPTION] {error_msg}\n")
                
        elapsed = time.time() - start_time
        print(f"Completed run in {elapsed:.2f} seconds. Success = {success}")
        
        # 4. Read logs and analyze steps
        log_content = ""
        if os.path.exists(log_file_path):
            with open(log_file_path, "r", encoding="utf-8") as lf:
                log_content = lf.read()
        
        step_metrics = count_agent_steps(log_content)
        
        # 5. Run verification tests on workspace
        test_passed = False
        test_msg = ""
        kv_store_exists = (Path(workspace_dir) / "kv_store.py").exists()
        test_kv_store_exists = (Path(workspace_dir) / "test_kv_store.py").exists()
        
        if kv_store_exists and test_kv_store_exists:
            test_passed, test_msg = run_pytest(workspace_dir)
        else:
            test_msg = f"Missing files (kv_store.py: {kv_store_exists}, test_kv_store.py: {test_kv_store_exists})"
            
        print(f"Verification: {test_msg}")
        
        results[model_id] = {
            "model_name": model_name,
            "workspace": workspace_dir,
            "elapsed_seconds": round(elapsed, 2),
            "exit_success": success,
            "error_message": error_msg,
            "kv_store_exists": kv_store_exists,
            "test_kv_store_exists": test_kv_store_exists,
            "pytest_success": test_passed,
            "pytest_message": test_msg,
            "step_metrics": step_metrics,
        }
        
        # Save incremental results
        with open("agent_eval_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        # 6. Sleep to avoid rate limits
        if i < len(MODELS) - 1:
            print("Sleeping 70 seconds to avoid rate limits...")
            time.sleep(70)
            
    print("\n" + "=" * 80)
    print("EVALUATION RUN COMPLETE")
    print("=" * 80)
    
    for mid, res in results.items():
        print(f"{res['model_name']} ({mid}):")
        print(f"  Execution Time: {res['elapsed_seconds']}s")
        print(f"  Pytest Success: {res['pytest_success']}")
        print(f"  Steps: {res['step_metrics']}")
        print(f"  Status: {res['pytest_message']}")

if __name__ == "__main__":
    main()
