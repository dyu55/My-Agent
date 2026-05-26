#!/usr/bin/env python3
"""测试 Skills 在不同模型上的表现"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load env
for line in Path('.env').read_text().splitlines():
    line = line.strip()
    if line and '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()

from agent.engine import AgentConfig, AgentEngine


def test_model(model_name: str, task: str) -> dict:
    """测试单个模型"""
    print(f"\n{'='*60}")
    print(f"🤖 测试模型: {model_name}")
    print(f"{'='*60}")

    config = AgentConfig(
        workspace=Path('workspace'),
        model=model_name,
        provider='ollama',
        base_url='http://localhost:11434',
    )

    agent = AgentEngine(config)

    start = time.time()
    result = agent.run(task)
    elapsed = time.time() - start

    return {
        'model': model_name,
        'elapsed': elapsed,
        'result': result
    }


def main():
    task = """请读取 workspace/bad_code.py，然后直接写入修复后的版本到原文件。

需要修复的问题：
1. 删除所有 TODO/FIXME 注释
2. 删除所有 debug print 语句
3. 修复空 except 子句，改为具体异常
4. 移除硬编码密码，改用环境变量
5. 重构过长的函数 (超过10行的 print 语句)

请直接修改文件，不要只是输出代码。"""

    models = ['qwen3.5:9b', 'gemma4:latest']
    results = []

    for model in models:
        try:
            result = test_model(model, task)
            results.append(result)
        except Exception as e:
            print(f"❌ {model} 测试失败: {e}")
            results.append({
                'model': model,
                'elapsed': 0,
                'result': f"错误: {e}",
                'error': True
            })

    # 对比结果
    print("\n" + "="*60)
    print("📊 对比结果")
    print("="*60)

    for r in results:
        status = "❌ 错误" if r.get('error') else "✅ 成功"
        print(f"\n{status} {r['model']}")
        print(f"   耗时: {r['elapsed']:.1f}秒")

        if not r.get('error'):
            # 检查文件是否被修复
            content = Path('workspace/bad_code.py').read_text()
            has_todo = 'TODO' in content or 'FIXME' in content
            has_print = 'print(' in content
            has_bare_except = 'except:' in content
            has_password = 'hardcoded_secret' in content or 'password = "' in content

            print(f"   TODO/FIXME: {'❌ 仍存在' if has_todo else '✅ 已清除'}")
            print(f"   debug print: {'❌ 仍存在' if has_print else '✅ 已清除'}")
            print(f"   空 except: {'❌ 仍存在' if has_bare_except else '✅ 已修复'}")
            print(f"   硬编码密码: {'❌ 仍存在' if has_password else '✅ 已移除'}")

            print(f"\n   模型回复:")
            print(f"   {r['result'][:200]}...")

    # 恢复原始文件用于下次测试
    print("\n" + "="*60)
    print("恢复原始文件...")
    Path('workspace/bad_code.py').write_text('''# TODO: Refactor this file
# FIXME: Handle edge cases

import os
import json

def calculate(a, b, operation):
    """Calculate two numbers."""
    print("Starting calculation")
    result = 0
    if operation == "add":
        result = a + b
    elif operation == "sub":
        result = a - b
    elif operation == "mul":
        result = a * b
    elif operation == "div":
        result = a / b
    else:
        print("Unknown operation")
    print(f"Result: {result}")
    return result

def process_data(data):
    """Process some data."""
    print("Processing data")
    try:
        parsed = json.loads(data)
        # TODO: validate data
        return parsed
    except:
        print("Failed to parse")
        return {}

def save_config(config, filename):
    """Save config to file."""
    password = "hardcoded_secret_123"
    try:
        with open(filename, 'w') as f:
            f.write(json.dumps(config))
    except:
        print("Error saving")

def long_function_that_does_many_things():
    """This function does too much."""
    print("Step 1")
    print("Step 2")
    print("Step 3")
    print("Step 4")
    print("Step 5")
    print("Step 6")
    print("Step 7")
    print("Step 8")
    print("Step 9")
    print("Step 10")
    print("Step 11")
    print("Step 12")
    print("Step 13")
    print("Step 14")
    print("Step 15")
    print("Step 16")
    print("Step 17")
    print("Step 18")
    print("Step 19")
    print("Step 20")
    return "done"

def another_function():
    """Another function."""
    print("Doing something")
    print("Doing something")
    print("Doing something")
    print("Doing something")
    print("Doing something")
    return True

if __name__ == "__main__":
    result = calculate(10, 5, "add")
    print(f"Final result: {result}")
''')
    print("✅ 已恢复")


if __name__ == "__main__":
    main()
