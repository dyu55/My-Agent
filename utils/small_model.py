"""小模型适配工具 - Phase 3

为 8B/9B 等小模型优化的提示模板和降级策略。
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class FallbackResult:
    """降级策略执行结果"""
    success: bool
    data: dict[str, Any] | None
    strategy_used: str
    error: str | None = None


class ChainOfThoughtPrompts:
    """
    Chain-of-Thought 提示模板库

    为小模型提供 Few-shot examples 以提高输出质量。
    """

    # 任务分解的 Few-shot 示例
    TASK_DECOMPOSITION_EXAMPLES = """
## Few-shot 示例

示例 1: 简单任务
输入: "运行测试"
输出:
{
  "analysis": "这是一个简单的单步任务",
  "subtasks": [
    {"id": "task_1", "description": "运行 pytest 测试", "dependencies": []}
  ]
}

示例 2: 复杂任务
输入: "创建一个用户认证系统"
输出:
{
  "analysis": "需要创建前后端的完整认证系统",
  "subtasks": [
    {"id": "task_1", "description": "设计数据库模型（用户表）", "dependencies": []},
    {"id": "task_2", "description": "创建后端认证 API", "dependencies": ["task_1"]},
    {"id": "task_3", "description": "创建前端登录页面", "dependencies": []},
    {"id": "task_4", "description": "集成测试", "dependencies": ["task_2", "task_3"]}
  ]
}

示例 3: 有依赖的任务
输入: "重构项目并添加新功能"
输出:
{
  "analysis": "需要先重构代码，然后添加功能",
  "subtasks": [
    {"id": "task_1", "description": "了解当前代码结构", "dependencies": []},
    {"id": "task_2", "description": "重构代码结构", "dependencies": ["task_1"]},
    {"id": "task_3", "description": "添加新功能", "dependencies": ["task_2"]},
    {"id": "task_4", "description": "验证新功能", "dependencies": ["task_3"]}
  ]
}
"""

    # 工具选择的 Few-shot 示例
    TOOL_SELECTION_EXAMPLES = """
## 工具选择指南

### 创建新文件
- 使用: write 命令
- 示例: {"command": "write", "path": "hello.py", "content": "print('hello')"}

### 修改现有文件
- 使用: edit 命令
- 示例: {"command": "edit", "path": "main.py", "old_text": "old code", "content": "new code"}

### 读取文件
- 使用: read 命令
- 示例: {"command": "read", "path": "config.py"}

### 执行脚本
- 使用: execute 命令
- 示例: {"command": "execute", "script": "python test.py"}

### 搜索代码
- 使用: search 命令
- 示例: {"command": "search", "query": "TODO"}

### 列出目录
- 使用: list_dir 命令
- 示例: {"command": "list_dir", "path": "."}

### 创建目录
- 使用: mkdir 命令
- 示例: {"command": "mkdir", "path": "src/utils"}
"""

    # 错误恢复的 Few-shot 示例
    ERROR_RECOVERY_EXAMPLES = """
## 错误恢复策略

### 语法错误
问题: "SyntaxError" 或 "IndentationError"
策略: 检查缩进，修复后重试

### 导入错误
问题: "ModuleNotFoundError"
策略: 先安装依赖: {"command": "pip_install", "packages": ["package_name"]}

### 文件不存在
问题: "File not found"
策略: 检查路径，可能需要创建目录

### 权限错误
问题: "Permission denied"
策略: 使用其他路径或命令

### JSON 解析失败
问题: 模型输出不是有效 JSON
策略: 简化提示，只要求输出 JSON
"""


class OutputValidator:
    """
    输出验证器

    验证 LLM 输出是否为有效的 JSON。
    """

    def __init__(self):
        self.validation_history: list[dict[str, Any]] = []

    def validate_json(self, output: str) -> tuple[bool, dict[str, Any] | None, str | None]:
        """
        验证 JSON 输出。

        Returns:
            (is_valid, parsed_data, error_message)
        """
        # 尝试直接解析
        try:
            data = json.loads(output)
            self.validation_history.append({"strategy": "direct", "success": True})
            return True, data, None
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 块
        extracted = self._extract_json_block(output)
        if extracted:
            try:
                data = json.loads(extracted)
                self.validation_history.append({"strategy": "block_extraction", "success": True})
                return True, data, None
            except json.JSONDecodeError:
                pass

        self.validation_history.append({"strategy": "all", "success": False, "output": output[:100]})
        return False, None, "Failed to parse JSON"

    def _extract_json_block(self, text: str) -> str | None:
        """从文本中提取 JSON 代码块。"""
        # 尝试 ```json ... ```
        match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if match:
            return match.group(1).strip()

        # 尝试 ``` ... ```
        match = re.search(r"```\s*([\s\S]*?)\s*```", text)
        if match:
            content = match.group(1).strip()
            if content.startswith("{") or content.startswith("["):
                return content

        # 尝试从 { 或 [ 开始到最后一个 } 或 ]
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            if start_char in text:
                start_idx = text.index(start_char)
                # 找到最后一个匹配
                last_end = text.rfind(end_char)
                if last_end > start_idx:
                    candidate = text[start_idx:last_end + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except json.JSONDecodeError:
                        pass

        return None


class FallbackStrategy:
    """
    降级策略

    当主要策略失败时的备选方案。
    """

    def __init__(self, llm_call: Callable[[str], str]):
        """
        Args:
            llm_call: LLM 调用函数
        """
        self.llm_call = llm_call
        self.strategy_history: list[str] = []

    def execute_with_fallback(
        self,
        prompt: str,
        schema: dict[str, Any] | None = None,
        max_retries: int = 3,
    ) -> FallbackResult:
        """
        执行带降级的 LLM 调用。

        策略链:
        1. 直接调用 (带 JSON 格式要求)
        2. 简化提示 (只要求 JSON)
        3. 使用正则提取关键字段
        4. 安全默认值

        Args:
            prompt: 原始提示
            schema: 期望的 JSON schema
            max_retries: 最大重试次数

        Returns:
            FallbackResult
        """
        # 策略 1: 直接调用
        self.strategy_history.append("direct")
        result = self._try_direct_call(prompt, schema)
        if result.success:
            return result

        # 策略 2: 简化提示
        self.strategy_history.append("simplified")
        result = self._try_simplified_prompt(prompt, schema)
        if result.success:
            return result

        # 策略 3: 正则提取
        self.strategy_history.append("regex")
        result = self._try_regex_extraction(prompt, schema)
        if result.success:
            return result

        # 策略 4: 安全默认值
        self.strategy_history.append("safe_default")
        return self._get_safe_default(schema)

    def _try_direct_call(
        self, prompt: str, schema: dict[str, Any] | None
    ) -> FallbackResult:
        """策略 1: 直接调用。"""
        try:
            # 简化 schema 为字符串描述
            schema_hint = ""
            if schema:
                schema_hint = f"\n\n期望的 JSON 结构: {json.dumps(schema, ensure_ascii=False)}"

            enhanced_prompt = f"""{prompt}{schema_hint}

重要: 你必须只返回有效的 JSON，不要任何其他文字。"""

            response = self.llm_call(enhanced_prompt)

            validator = OutputValidator()
            is_valid, data, error = validator.validate_json(response)

            if is_valid and data:
                return FallbackResult(
                    success=True,
                    data=data,
                    strategy_used="direct"
                )
            return FallbackResult(
                success=False,
                data=None,
                strategy_used="direct",
                error=error or "Invalid JSON"
            )
        except Exception as e:
            return FallbackResult(
                success=False,
                data=None,
                strategy_used="direct",
                error=str(e)
            )

    def _try_simplified_prompt(
        self, prompt: str, schema: dict[str, Any] | None
    ) -> FallbackResult:
        """策略 2: 简化提示，只要求 JSON。"""
        try:
            # 构建最简单的 JSON 格式要求
            required_fields = []
            if schema and "properties" in schema:
                required_fields = list(schema["properties"].keys())

            fields_hint = ""
            if required_fields:
                fields_hint = f"\n\n必须包含的字段: {', '.join(required_fields)}"

            simplified_prompt = f"""{prompt}{fields_hint}

只返回 JSON，不要任何解释。用这个格式:
{{"field1": "value1", "field2": "value2"}}
"""

            response = self.llm_call(simplified_prompt)

            validator = OutputValidator()
            is_valid, data, error = validator.validate_json(response)

            if is_valid and data:
                return FallbackResult(
                    success=True,
                    data=data,
                    strategy_used="simplified"
                )
            return FallbackResult(
                success=False,
                data=None,
                strategy_used="simplified",
                error=error or "Invalid JSON"
            )
        except Exception as e:
            return FallbackResult(
                success=False,
                data=None,
                strategy_used="simplified",
                error=str(e)
            )

    def _try_regex_extraction(
        self, prompt: str, schema: dict[str, Any] | None
    ) -> FallbackResult:
        """策略 3: 使用正则提取关键字段。"""
        try:
            # 重新调用获取原始响应
            response = self.llm_call(prompt + "\n\n请简洁回答。")

            extracted: dict[str, Any] = {}

            # 尝试提取常见字段
            patterns = {
                "analysis": r"(?:分析|analysis)[:：]?\s*(.+?)(?:\n|$)",
                "description": r"(?:描述|description)[:：]?\s*(.+?)(?:\n|$)",
                "suggestion": r"(?:建议|suggestion)[:：]?\s*(.+?)(?:\n|$)",
                "id": r"(?:id|ID)[:：]?\s*([a-zA-Z0-9_]+)",
                "status": r"(?:status|状态)[:：]?\s*([a-zA-Z_]+)",
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, response, re.IGNORECASE)
                if match:
                    extracted[key] = match.group(1).strip()

            # 如果提取到任何内容，认为成功
            if extracted:
                return FallbackResult(
                    success=True,
                    data=extracted,
                    strategy_used="regex"
                )

            return FallbackResult(
                success=False,
                data=None,
                strategy_used="regex",
                error="No fields extracted"
            )
        except Exception as e:
            return FallbackResult(
                success=False,
                data=None,
                strategy_used="regex",
                error=str(e)
            )

    def _get_safe_default(
        self, schema: dict[str, Any] | None
    ) -> FallbackResult:
        """策略 4: 返回安全默认值。"""
        default_data: dict[str, Any] = {}

        if schema and "properties" in schema:
            for field_name, field_schema in schema["properties"].items():
                field_type = field_schema.get("type", "string")
                if field_type == "string":
                    default_data[field_name] = ""
                elif field_type == "array":
                    default_data[field_name] = []
                elif field_type == "object":
                    default_data[field_name] = {}
                elif field_type == "number":
                    default_data[field_name] = 0
                elif field_type == "boolean":
                    default_data[field_name] = False

        return FallbackResult(
            success=True,
            data=default_data,
            strategy_used="safe_default",
            error=None
        )


class SmallModelOptimizer:
    """
    小模型优化器

    整合所有小模型适配策略。
    """

    def __init__(self, llm_call: Callable[[str], str]):
        self.cot = ChainOfThoughtPrompts()
        self.fallback = FallbackStrategy(llm_call)
        self.validator = OutputValidator()

    def create_task_plan(
        self, task: str, context: str = ""
    ) -> dict[str, Any]:
        """
        创建任务计划（带 CoT 优化）。

        Args:
            task: 任务描述
            context: 项目上下文

        Returns:
            解析后的计划数据
        """
        prompt = f"""{self.cot.TASK_DECOMPOSITION_EXAMPLES}

## 任务
{task}

{self.cot.TOOL_SELECTION_EXAMPLES}

{self.cot.ERROR_RECOVERY_EXAMPLES}

现在分析任务并输出 JSON："""

        if context:
            prompt += f"\n\n## 当前项目状态\n{context}"

        result = self.fallback.execute_with_fallback(
            prompt,
            schema={
                "type": "object",
                "properties": {
                    "analysis": {"type": "string"},
                    "subtasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "description": {"type": "string"},
                                "dependencies": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    }
                }
            }
        )

        if result.success and result.data:
            return result.data

        # 返回默认计划
        return {
            "analysis": "使用默认计划",
            "subtasks": [
                {"id": "task_1", "description": task, "dependencies": []}
            ]
        }

    def generate_action(
        self,
        task_description: str,
        execution_summary: str = ""
    ) -> dict[str, Any]:
        """
        生成操作指令（带 CoT 优化）。

        Args:
            task_description: 任务描述
            execution_summary: 已完成的执行历史

        Returns:
            操作参数字典
        """
        prompt = f"""你是一个编程助手。

## 当前任务
{task_description}

## 已完成的任务
{execution_summary or "无"}

## 规则
1. 必须使用 write 或 edit 命令
2. 禁止使用 finish 或 debug 命令
3. 必须包含具体的文件内容

## 输出格式
返回 JSON:
{{"command": "write", "path": "文件名.py", "content": "文件内容"}}
"""

        result = self.fallback.execute_with_fallback(
            prompt,
            schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                }
            }
        )

        if result.success and result.data:
            return result.data

        # 返回默认操作
        return {"command": "debug", "content": "无法生成有效操作"}

    def get_strategy_report(self) -> str:
        """获取策略使用报告。"""
        lines = ["## 降级策略使用报告\n"]

        strategies = self.fallback.strategy_history
        if not strategies:
            return "暂无策略使用记录"

        from collections import Counter
        counter = Counter(strategies)

        lines.append(f"总调用次数: {len(strategies)}\n")
        lines.append("策略使用统计:")
        for strategy, count in counter.most_common():
            lines.append(f"  - {strategy}: {count} ({count/len(strategies)*100:.1f}%)")

        return "\n".join(lines)
