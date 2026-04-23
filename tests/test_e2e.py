#!/usr/bin/env python3
"""
End-to-End 测试脚本
测试完整的 Agent 工作流程
"""

import os
import sys
import time
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    for line in Path('.env').read_text().splitlines():
        line = line.strip()
        if line and '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()
except FileNotFoundError:
    pass


def test_e2e_file_creation():
    """E2E 测试：创建文件并写入内容"""
    print("\n" + "=" * 60)
    print("🧪 E2E 测试: 文件创建")
    print("=" * 60)

    from main import create_agent
    import argparse

    with tempfile.TemporaryDirectory() as tmpdir:
        args = argparse.Namespace(
            task=None,
            chat=False,
            model=os.getenv('MODEL_NAME', 'gemma4:latest'),
            provider='ollama',
            workspace=tmpdir,
            max_retries=2,
            no_llm_reflection=False,
            list_providers=False,
        )

        agent = create_agent(args)

        # 任务：创建 Python 文件
        result = agent.run("创建一个简单的 hello.py 文件，输出 'Hello, World!'")

        print(f"\n📋 结果: {result}")

        # 检查文件是否存在
        hello_file = Path(tmpdir) / "hello.py"
        if hello_file.exists():
            content = hello_file.read_text()
            print(f"✅ 文件已创建")
            print(f"📄 内容:\n{content[:200]}")
            return True
        else:
            print(f"❌ 文件未创建")
            return False


def test_e2e_task_decomposition():
    """E2E 测试：任务分解"""
    print("\n" + "=" * 60)
    print("🧪 E2E 测试: 任务分解")
    print("=" * 60)

    from utils.small_model import SmallModelOptimizer

    def llm_call(prompt):
        from utils.model_provider import ModelManager
        manager = ModelManager("ollama", os.getenv('MODEL_NAME', 'gemma4:latest'))
        return manager.chat(prompt)

    optimizer = SmallModelOptimizer(llm_call)

    task = "创建一个待办事项应用，需要：1) 添加任务 2) 列出任务 3) 删除任务"
    plan = optimizer.create_task_plan(task, context="空目录")

    print(f"\n📋 计划包含 {len(plan.get('subtasks', []))} 个子任务:")
    for i, task in enumerate(plan.get('subtasks', []), 1):
        print(f"   {i}. {task.get('description', 'N/A')}")

    return len(plan.get('subtasks', [])) > 0


def test_e2e_multi_step_task():
    """E2E 测试：多步骤任务"""
    print("\n" + "=" * 60)
    print("🧪 E2E 测试: 多步骤任务")
    print("=" * 60)

    from main import create_agent
    import argparse

    with tempfile.TemporaryDirectory() as tmpdir:
        args = argparse.Namespace(
            task=None,
            chat=False,
            model=os.getenv('MODEL_NAME', 'gemma4:latest'),
            provider='ollama',
            workspace=tmpdir,
            max_retries=3,
            no_llm_reflection=False,
            list_providers=False,
        )

        agent = create_agent(args)

        # 复杂任务：创建多个文件
        result = agent.run(
            "在当前目录创建一个简单的计算器："
            "1) 创建 calculator.py 包含 add/sub/mul/div 函数"
            "2) 创建 main.py 调用计算器"
        )

        print(f"\n📋 结果: {result}")

        # 检查文件是否存在
        files_created = []
        for fname in ['calculator.py', 'main.py']:
            fpath = Path(tmpdir) / fname
            if fpath.exists():
                files_created.append(fname)

        print(f"✅ 创建的文件: {files_created}")
        return len(files_created) >= 1


def main():
    """主函数"""
    print("=" * 70)
    print("🧪 E2E 测试套件")
    print("=" * 70)

    results = []

    # 1. 文件创建测试
    try:
        passed = test_e2e_file_creation()
        results.append(("文件创建", passed))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("文件创建", False))

    # 2. 任务分解测试
    try:
        passed = test_e2e_task_decomposition()
        results.append(("任务分解", passed))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("任务分解", False))

    # 3. 多步骤任务测试
    try:
        passed = test_e2e_multi_step_task()
        results.append(("多步骤任务", passed))
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        results.append(("多步骤任务", False))

    # 总结
    print("\n" + "=" * 70)
    print("📊 E2E 测试结果")
    print("=" * 70)

    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {name}: {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\n总计: {passed}/{total} 通过")


if __name__ == "__main__":
    main()
