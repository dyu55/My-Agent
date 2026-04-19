import os
import json
import subprocess
from pathlib import Path
import ollama  # 请先 pip install ollama

# --- 配置区 ---
WORKSPACE = Path("./workspace").resolve()
WORKSPACE.mkdir(exist_ok=True)
MODEL_NAME = "gemma2:27b"  # 确保你 Ollama 里有这个模型
MAX_FAILURES = 5

def is_safe_path(path):
    target = (WORKSPACE / path).resolve()
    return target.is_relative_to(WORKSPACE)

# --- 工具定义 ---
def tool_write(path, content):
    if not is_safe_path(path): return "Error: Access Denied"
    (WORKSPACE / path).write_text(content, encoding='utf-8')
    return f"Success: File {path} written."

def tool_read(path, start=1, end=100):
    if not is_safe_path(path): return "Error: Access and path check failed"
    try:
        lines = (WORKSPACE / path).read_text().splitlines()
        subset = lines[start-1:end]
        # 给读取的内容加上行号，方便 Agent 观察
        numbered = "\n".join([f"{i+start}: {line}" for i, line in enumerate(subset)])
        return f"Content of {path}:\n{numbered}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

def tool_execute(script):
    try:
        # 在 workspace 目录下执行
        result = subprocess.run(
            script, shell=True, capture_output=True, text=True, cwd=WORKSPACE, timeout=30
        )
        status = "Success" if result.returncode == 0 else "Failed"
        return f"Exit Code: {result.returncode}\nWhat happened:\n{result.stdout}\n{result.stderr}"
    except Exception as e:
        return f"Error executing command: {str(e)}"

# --- 核心调度器 ---
def run_agent(task):
    messages = [
        {"role": "system", "content": f"你是一个 Coding Agent。你必须通过 JSON 调用工具。工作目录是 {WORKSPACE}。格式参考之前讨论的 Thought + JSON。"},
        {"role": "user", "content": task}
    ]
    
    failure_count = 0
    
    while failure_count < MAX_FAILURES:
        response = ollama.chat(model=MODEL_NAME, messages=messages)
        raw_content = response['message']['content']
        print(f"\n--- Model Output ---\n{raw_content}")

        # 尝试提取 JSON
        try:
            # 方案 A 的严格解析：找到第一个 { 和最后一个 }
            start_idx = raw_content.find('{')
            end_idx = raw_content.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON block found in response.")
                
            action = json.loads(raw_content[start_idx:end_idx])
            
            # 执行工具逻辑
            cmd = action.get("command")
            if cmd == "write":
                obs = tool_write(action['path'], action['content'])
            elif cmd == "read":
                obs = tool_read(action['path'], action.get('start', 1), action.get('end', 100))
            elif cmd == "execute":
                obs = tool_execute(action['script'])
            elif cmd == "finish":
                print("✅ 任务完成！")
                break
            else:
                obs = "Error: Unknown command."

            # 成功执行一次动作后，重置失败计数
            failure_count = 0 
            messages.append({"role": "assistant", "content": raw_content})
            messages.append({"role": "user", "content": f"What happened:\n{obs}"})

        except Exception as e:
            failure_count += 1
            print(f"⚠️ 格式解析错误 ({failure_count}/{MAX_FAILURES}): {e}")
            messages.append({"role": "user", "content": "Error: Your last response was not a valid JSON. Please try again."})

    if failure_count >= MAX_FAILURES:
        print("❌ 连续失败次数过多，程序终止。")

# --- 启动 ---
if __name__ == "__main__":
    run_agent("在 main.py 里写一个简单的 FastAPI 服务并运行它。")
