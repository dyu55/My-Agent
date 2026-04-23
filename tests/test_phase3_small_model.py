#!/usr/bin/env python3
"""Phase 3: 小模型适配测试"""

import os
import sys
from pathlib import Path

# 加载环境变量
sys.path.insert(0, str(Path(__file__).parent.parent))

for line in Path('.env').read_text().splitlines():
    line = line.strip()
    if line and '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        os.environ[k.strip()] = v.strip()

import ollama
from utils.small_model import (
    ChainOfThoughtPrompts,
    FallbackStrategy,
    FallbackResult,
    OutputValidator,
    SmallModelOptimizer,
)


class MockLLM:
    """模拟 LLM 用于测试"""

    def __init__(self, response: str, delay: float = 0):
        self.response = response
        self.delay = delay
        self.call_count = 0

    def chat(self, prompt: str) -> str:
        import time
        self.call_count += 1
        if self.delay:
            time.sleep(self.delay)
        return self.response


def test_output_validator():
    """测试输出验证器"""
    print("\n" + "=" * 60)
    print("🧪 测试 OutputValidator")
    print("=" * 60)

    validator = OutputValidator()

    # 测试 1: 有效 JSON
    valid_json = '{"key": "value", "number": 123}'
    is_valid, data, error = validator.validate_json(valid_json)
    assert is_valid, f"应该解析有效 JSON: {error}"
    assert data == {"key": "value", "number": 123}
    print("✅ 测试 1: 有效 JSON 解析成功")

    # 测试 2: 带 ```json 块
    json_block = '```json\n{"key": "value"}\n```'
    is_valid, data, error = validator.validate_json(json_block)
    assert is_valid, f"应该解析 JSON 块: {error}"
    assert data == {"key": "value"}
    print("✅ 测试 2: JSON 代码块解析成功")

    # 测试 3: 文本中嵌入 JSON
    embedded = 'Some text before {"key": "value"} some text after'
    is_valid, data, error = validator.validate_json(embedded)
    assert is_valid, f"应该解析嵌入的 JSON: {error}"
    assert data == {"key": "value"}
    print("✅ 测试 3: 嵌入 JSON 解析成功")

    # 测试 4: 无效 JSON
    invalid = 'not valid json at all'
    is_valid, data, error = validator.validate_json(invalid)
    assert not is_valid, "应该拒绝无效 JSON"
    print("✅ 测试 4: 无效 JSON 正确拒绝")


def test_fallback_strategy():
    """测试降级策略"""
    print("\n" + "=" * 60)
    print("🧪 测试 FallbackStrategy")
    print("=" * 60)

    # 测试 1: 正常响应
    mock = MockLLM('{"result": "success"}')
    fallback = FallbackStrategy(mock.chat)

    result = fallback.execute_with_fallback("test prompt")
    assert result.success, f"应该成功: {result.error}"
    assert result.strategy_used in ["direct", "simplified", "regex", "safe_default"]
    print(f"✅ 测试 1: 正常响应 - 使用策略: {result.strategy_used}")

    # 测试 2: JSON 块响应
    mock = MockLLM('```json\n{"result": "from block"}\n```')
    fallback = FallbackStrategy(mock.chat)

    result = fallback.execute_with_fallback("test prompt")
    assert result.success, f"应该成功: {result.error}"
    print(f"✅ 测试 2: JSON 块提取 - 使用策略: {result.strategy_used}")

    # 测试 3: 无效响应 -> 正则提取
    mock = MockLLM('analysis: This is the analysis')
    fallback = FallbackStrategy(mock.chat)

    result = fallback.execute_with_fallback("test prompt", schema={"properties": {"analysis": {"type": "string"}}})
    assert result.success, f"应该成功: {result.error}"
    print(f"✅ 测试 3: 正则提取 - 使用策略: {result.strategy_used}")

    # 测试 4: 最终降级到默认值 (需要完全没有可提取内容)
    # 使用纯数字避免匹配任何模式
    mock = MockLLM('123 456 789')
    fallback = FallbackStrategy(mock.chat)

    result = fallback.execute_with_fallback(
        "test prompt",
        schema={"properties": {"field1": {"type": "string"}, "field2": {"type": "number"}}}
    )
    assert result.success, "应该成功降级"
    assert result.data is not None, "应该返回数据"
    print(f"✅ 测试 4: 降级成功 - 使用策略: {result.strategy_used}")


def test_cot_prompts():
    """测试 Chain-of-Thought 提示"""
    print("\n" + "=" * 60)
    print("🧪 测试 ChainOfThoughtPrompts")
    print("=" * 60)

    cot = ChainOfThoughtPrompts()

    assert len(cot.TASK_DECOMPOSITION_EXAMPLES) > 0
    print("✅ 测试 1: 任务分解示例存在")

    assert len(cot.TOOL_SELECTION_EXAMPLES) > 0
    print("✅ 测试 2: 工具选择示例存在")

    assert len(cot.ERROR_RECOVERY_EXAMPLES) > 0
    print("✅ 测试 3: 错误恢复示例存在")


def test_small_model_optimizer_integration():
    """测试小模型优化器集成"""
    print("\n" + "=" * 60)
    print("🧪 测试 SmallModelOptimizer 集成 (使用 gemma4)")
    print("=" * 60)

    # 连接到 Ollama
    client = ollama.Client(host=os.getenv('OLLAMA_HOST', 'http://localhost:11434'))
    model = os.getenv('MODEL_NAME', 'gemma4:latest')

    def llm_call(prompt: str) -> str:
        response = client.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1}
        )
        return response['message']['content']

    optimizer = SmallModelOptimizer(llm_call)

    # 测试创建任务计划
    print(f"\n🔄 使用 {model} 创建任务计划...")

    try:
        plan = optimizer.create_task_plan(
            "创建一个简单的计算器程序",
            context="当前目录为空"
        )

        assert "subtasks" in plan, "应该包含 subtasks"
        assert len(plan["subtasks"]) > 0, "应该至少有一个子任务"

        print(f"✅ 成功创建计划，包含 {len(plan['subtasks'])} 个子任务")

        # 显示计划
        print("\n📋 生成的计划:")
        for task in plan.get("subtasks", []):
            deps = f" (依赖: {', '.join(task.get('dependencies', []))})" if task.get('dependencies') else ""
            print(f"   - {task['id']}: {task['description']}{deps}")

        # 获取策略报告
        report = optimizer.get_strategy_report()
        print(f"\n📊 策略使用报告:\n{report}")

    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("=" * 70)
    print("🧪 Phase 3: 小模型适配测试套件")
    print("=" * 70)

    # 单元测试
    print("\n📦 单元测试")
    print("-" * 40)

    test_output_validator()
    test_fallback_strategy()
    test_cot_prompts()

    # 集成测试
    print("\n\n🔗 集成测试 (需要 Ollama)")
    print("-" * 40)

    test_small_model_optimizer_integration()

    print("\n" + "=" * 70)
    print("✅ 所有测试完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
