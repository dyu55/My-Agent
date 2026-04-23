#!/usr/bin/env python3
"""直接测试 LLM 模型修复代码的能力"""

import os
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

for line in Path('.env').read_text().splitlines():
    line = line.strip()
    if line and '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()

import ollama


def test_model_fix_code(model: str, code: str) -> tuple[str, float]:
    """让模型直接生成修复后的代码"""
    client = ollama.Client(host='http://localhost:11434')

    prompt = f"""请修复以下 Python 代码中的问题，只返回修复后的完整代码：

问题列表：
1. 删除所有 TODO/FIXME 注释
2. 删除所有 debug print 语句
3. 修复空 except 子句，改为具体异常
4. 移除硬编码密码，改用 os.environ.get("PASSWORD")
5. 重构过长的函数

原始代码：
{code}

请只返回修复后的代码，不要任何解释。"""

    start = time.time()
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.1}
    )
    elapsed = time.time() - start

    return response['message']['content'], elapsed


def check_code_quality(code: str) -> dict:
    """检查代码质量"""
    return {
        'has_todo': 'TODO' in code or 'FIXME' in code,
        'has_print': 'print(' in code,
        'has_bare_except': 'except:' in code,
        'has_password': 'hardcoded_secret' in code or ('password = "' in code and 'os.environ' not in code),
        'has_long_function': code.count('print("Step') >= 5,
    }


# 测试用的坏代码
BAD_CODE = '''# TODO: Refactor this file
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
    print(f"Result: {{result}}")
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
        return {{}}

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
    return "done"

if __name__ == "__main__":
    result = calculate(10, 5, "add")
    print(f"Final result: {{result}}")
'''

def main():
    print("=" * 70)
    print("🧪 LLM 模型代码修复能力测试")
    print("=" * 70)

    models = ['qwen3.5:9b', 'gemma4:latest']
    results = []

    for model in models:
        print(f"\n{'='*60}")
        print(f"🤖 测试模型: {model}")
        print(f"{'='*60}")

        try:
            fixed_code, elapsed = test_model_fix_code(model, BAD_CODE)
            quality = check_code_quality(fixed_code)

            print(f"\n⏱️  耗时: {elapsed:.1f}秒")
            print(f"\n📊 代码质量检查:")
            print(f"   - TODO/FIXME: {'❌ 仍存在' if quality['has_todo'] else '✅ 已清除'}")
            print(f"   - debug print: {'❌ 仍存在' if quality['has_print'] else '✅ 已清除'}")
            print(f"   - 空 except: {'❌ 仍存在' if quality['has_bare_except'] else '✅ 已修复'}")
            print(f"   - 硬编码密码: {'❌ 仍存在' if quality['has_password'] else '✅ 已移除'}")

            # 计算得分
            issues = sum(quality.values())
            score = max(0, 100 - issues * 25)
            print(f"\n📈 修复得分: {score}/100")

            print(f"\n📝 模型输出 (前 500 字):")
            print("-" * 40)
            print(fixed_code[:500])
            print("-" * 40)

            results.append({
                'model': model,
                'elapsed': elapsed,
                'quality': quality,
                'score': score,
                'code': fixed_code[:1000]
            })

        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            results.append({
                'model': model,
                'error': str(e)
            })

    # 对比总结
    print("\n" + "=" * 70)
    print("📊 对比结果总结")
    print("=" * 70)

    for r in results:
        if 'error' in r:
            print(f"\n❌ {r['model']}: {r['error']}")
        else:
            print(f"\n{'='*40}")
            print(f"🤖 {r['model']}")
            print(f"{'='*40}")
            print(f"   耗时: {r['elapsed']:.1f}秒")
            print(f"   得分: {r['score']}/100")

            q = r['quality']
            print(f"   检查项:")
            print(f"      TODO/FIXME: {'❌' if q['has_todo'] else '✅'}")
            print(f"      debug print: {'❌' if q['has_print'] else '✅'}")
            print(f"      空 except: {'❌' if q['has_bare_except'] else '✅'}")
            print(f"      硬编码密码: {'❌' if q['has_password'] else '✅'}")

    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)


if __name__ == "__main__":
    main()