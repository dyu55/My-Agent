"""Small model adaptation utilities - Phase 3

Prompt templates and fallback strategies optimized for 8B/9B models.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ModelProfile:
    """
    Model size profile for adaptive behavior.

    Detects model size from name and provides appropriate limits
    for context, prompts, and memory management.
    """

    size_category: str  # "small" (8B/9B), "medium" (26B/31B), "large" (70B+)
    param_billions: float
    max_context_tokens: int
    max_file_context_files: int
    max_prompt_chars: int
    max_history_messages: int
    prefer_short_prompts: bool

    @classmethod
    def from_model_name(cls, model_name: str) -> "ModelProfile":
        """Detect model size from name and create appropriate profile."""
        name_lower = model_name.lower()

        # Extract parameter count from common patterns
        param_b = cls._extract_param_size(name_lower)

        if param_b <= 10:
            return cls._small_profile(param_b)
        elif param_b <= 35:
            return cls._medium_profile(param_b)
        else:
            return cls._large_profile(param_b)

    @staticmethod
    def _extract_param_size(name: str) -> float:
        """Extract parameter size in billions from model name."""
        # Match patterns like "8b", "9b", "26b", "31b", "70b", "7b"
        match = re.search(r"(\d+(?:\.\d+)?)\s*b", name)
        if match:
            return float(match.group(1))

        # Match patterns like "0.5b", "1.5b"
        match = re.search(r"(\d+\.\d+)\s*b", name)
        if match:
            return float(match.group(1))

        # Known model name mappings
        known_sizes = {
            "tiny": 1, "mini": 3, "small": 7,
            "gemma": 9, "qwen": 9, "phi": 3,
            "mistral": 7, "codellama": 7,
            "llama3": 8, "llama-3": 8,
            "deepseek": 16, "yi": 6,
        }
        for key, size in known_sizes.items():
            if key in name:
                return size

        # Default to medium if unknown
        return 14

    @staticmethod
    def _small_profile(param_b: float) -> "ModelProfile":
        """Profile for 8B/9B models."""
        return ModelProfile(
            size_category="small",
            param_billions=param_b,
            max_context_tokens=4096,
            max_file_context_files=10,
            max_prompt_chars=2000,
            max_history_messages=5,
            prefer_short_prompts=True,
        )

    @staticmethod
    def _medium_profile(param_b: float) -> "ModelProfile":
        """Profile for 26B/31B models."""
        return ModelProfile(
            size_category="medium",
            param_billions=param_b,
            max_context_tokens=8192,
            max_file_context_files=25,
            max_prompt_chars=4000,
            max_history_messages=10,
            prefer_short_prompts=False,
        )

    @staticmethod
    def _large_profile(param_b: float) -> "ModelProfile":
        """Profile for 70B+ models."""
        return ModelProfile(
            size_category="large",
            param_billions=param_b,
            max_context_tokens=32768,
            max_file_context_files=50,
            max_prompt_chars=8000,
            max_history_messages=20,
            prefer_short_prompts=False,
        )


# Global cache for model profiles
_profile_cache: dict[str, ModelProfile] = {}


def get_model_profile(model_name: str) -> ModelProfile:
    """Get or create a cached ModelProfile for the given model name."""
    if model_name not in _profile_cache:
        _profile_cache[model_name] = ModelProfile.from_model_name(model_name)
    return _profile_cache[model_name]


def clear_profile_cache() -> None:
    """Clear the profile cache (useful for testing)."""
    _profile_cache.clear()


@dataclass
class FallbackResult:
    """Fallback strategy execution result"""
    success: bool
    data: dict[str, Any] | None
    strategy_used: str
    error: str | None = None


class ChainOfThoughtPrompts:
    """
    Chain-of-Thought prompt template library

    Provides Few-shot examples to improve output quality for small models.
    """

    # Task decomposition Few-shot examples
    TASK_DECOMPOSITION_EXAMPLES = """
## Few-shot Examples

Example 1: Simple Task
Input: "Run tests"
Output:
{
  "analysis": "Simple single-step task",
  "subtasks": [
    {"id": "task_1", "description": "Run pytest tests", "dependencies": []}
  ]
}

Example 2: Complex Task
Input: "Create a user authentication system"
Output:
{
  "analysis": "Need to create a full auth system with frontend and backend",
  "subtasks": [
    {"id": "task_1", "description": "Design database models (user table)", "dependencies": []},
    {"id": "task_2", "description": "Create backend auth API", "dependencies": ["task_1"]},
    {"id": "task_3", "description": "Create frontend login page", "dependencies": []},
    {"id": "task_4", "description": "Integration tests", "dependencies": ["task_2", "task_3"]}
  ]
}

Example 3: Task with Dependencies
Input: "Refactor project and add new features"
Output:
{
  "analysis": "Need to refactor first, then add features",
  "subtasks": [
    {"id": "task_1", "description": "Understand current code structure", "dependencies": []},
    {"id": "task_2", "description": "Refactor code structure", "dependencies": ["task_1"]},
    {"id": "task_3", "description": "Add new features", "dependencies": ["task_2"]},
    {"id": "task_4", "description": "Verify new features", "dependencies": ["task_3"]}
  ]
}
"""

    # Tool selection Few-shot examples
    TOOL_SELECTION_EXAMPLES = """
## Tool Selection Guide

### Create New File
- Use: write command
- Example: {"command": "write", "path": "hello.py", "content": "print('hello')"}

### Modify Existing File
- Use: edit command
- Example: {"command": "edit", "path": "main.py", "old_text": "old code", "content": "new code"}

### Read File
- Use: read command
- Example: {"command": "read", "path": "config.py"}

### Execute Script
- Use: execute command
- Example: {"command": "execute", "script": "python test.py"}

### Search Code
- Use: search command
- Example: {"command": "search", "query": "TODO"}

### List Directory
- Use: list_dir command
- Example: {"command": "list_dir", "path": "."}

### Create Directory
- Use: mkdir command
- Example: {"command": "mkdir", "path": "src/utils"}
"""

    # Error recovery Few-shot examples
    ERROR_RECOVERY_EXAMPLES = """
## Error Recovery Strategies

### Syntax Error
Problem: "SyntaxError" or "IndentationError"
Strategy: Check indentation, fix and retry

### Import Error
Problem: "ModuleNotFoundError"
Strategy: Install dependencies first: {"command": "pip_install", "packages": ["package_name"]}

### File Not Found
Problem: "File not found"
Strategy: Check path, may need to create directory

### Permission Error
Problem: "Permission denied"
Strategy: Use alternative path or command

### JSON Parse Failure
Problem: Model output is not valid JSON
Strategy: Simplify prompt, request JSON only
"""


class OutputValidator:
    """
    Output Validator

    Validates LLM output is valid JSON.
    """

    def __init__(self):
        self.validation_history: list[dict[str, Any]] = []

    def validate_json(self, output: str) -> tuple[bool, dict[str, Any] | None, str | None]:
        """
        Validate JSON output.

        Returns:
            (is_valid, parsed_data, error_message)
        """
        # Try direct parse first
        try:
            data = json.loads(output)
            self.validation_history.append({"strategy": "direct", "success": True})
            return True, data, None
        except json.JSONDecodeError:
            pass

        # Try extracting JSON block
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
        """Extract JSON code block from text."""
        # Try ```json ... ```
        match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if match:
            return match.group(1).strip()

        # Try ``` ... ```
        match = re.search(r"```\s*([\s\S]*?)\s*```", text)
        if match:
            content = match.group(1).strip()
            if content.startswith("{") or content.startswith("["):
                return content

        # Try finding from { or [ to last } or ]
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            if start_char in text:
                start_idx = text.index(start_char)
                # Find last match
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
    Fallback strategy

    Backup approach when the primary strategy fails.
    """

    def __init__(self, llm_call: Callable[[str], str]):
        """
        Args:
            llm_call: LLM call function
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
        Execute LLM call with fallback strategies.

        Optimized strategy chain (reduces LLM calls):
        1. Direct call (with JSON format) -> return if success
        2. Regex extract from same response -> return if success (no extra LLM call)
        3. Simplified prompt retry -> return if success
        4. Safe default value

        Args:
            prompt: Original prompt
            schema: Expected JSON schema
            max_retries: Maximum retry count

        Returns:
            FallbackResult
        """
        # Strategy 1: Direct call
        self.strategy_history.append("direct")
        result = self._try_direct_call(prompt, schema)
        if result.success:
            return result

        # Strategy 2: Regex extract from same response (no extra LLM call)
        self.strategy_history.append("regex")
        raw_response = result.error or ""
        regex_result = self._try_regex_from_response(raw_response, schema)
        if regex_result.success:
            return regex_result

        # Strategy 3: Simplified prompt retry
        self.strategy_history.append("simplified")
        result = self._try_simplified_prompt(prompt, schema)
        if result.success:
            return result

        # Strategy 4: Safe default value
        self.strategy_history.append("safe_default")
        return self._get_safe_default(schema)

    def _try_direct_call(
        self, prompt: str, schema: dict[str, Any] | None
    ) -> FallbackResult:
        """Strategy 1: Direct call."""
        try:
            # Simplify schema to string description
            schema_hint = ""
            if schema:
                schema_hint = f"\n\nExpected JSON structure: {json.dumps(schema, ensure_ascii=False)}"

            enhanced_prompt = f"""{prompt}{schema_hint}

Important: You must return valid JSON only, no other text."""

            response = self.llm_call(enhanced_prompt)

            validator = OutputValidator()
            is_valid, data, error = validator.validate_json(response)

            if is_valid and data:
                return FallbackResult(
                    success=True,
                    data=data,
                    strategy_used="direct"
                )
            # Store raw response in error field for regex fallback reuse
            return FallbackResult(
                success=False,
                data=None,
                strategy_used="direct",
                error=response,  # raw response for _try_regex_from_response
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
        """Strategy 2: Simplified prompt, request JSON only."""
        try:
            # Build simplest JSON format requirement
            required_fields = []
            if schema and "properties" in schema:
                required_fields = list(schema["properties"].keys())

            fields_hint = ""
            if required_fields:
                fields_hint = f"\n\nRequired fields: {', '.join(required_fields)}"

            simplified_prompt = f"""{prompt}{fields_hint}

Return JSON only, no explanation. Use this format:
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

    def _try_regex_from_response(
        self, raw_response: str, schema: dict[str, Any] | None
    ) -> FallbackResult:
        """Strategy 2: Extract JSON from existing response (no extra LLM call)."""
        if not raw_response:
            return FallbackResult(
                success=False, data=None, strategy_used="regex",
                error="No response to extract from"
            )

        validator = OutputValidator()
        is_valid, data, _ = validator.validate_json(raw_response)
        if is_valid and data:
            return FallbackResult(success=True, data=data, strategy_used="regex")

        # Try regex field extraction
        extracted: dict[str, Any] = {}
        patterns = {
            "analysis": r"(?:分析|analysis)[:：]?\s*(.+?)(?:\n|$)",
            "description": r"(?:描述|description)[:：]?\s*(.+?)(?:\n|$)",
            "suggestion": r"(?:建议|suggestion)[:：]?\s*(.+?)(?:\n|$)",
            "id": r"(?:id|ID)[:：]?\s*([a-zA-Z0-9_]+)",
            "status": r"(?:status|状态)[:：]?\s*([a-zA-Z_]+)",
        }
        for key, pattern in patterns.items():
            match = re.search(pattern, raw_response, re.IGNORECASE)
            if match:
                extracted[key] = match.group(1).strip()

        if extracted:
            return FallbackResult(success=True, data=extracted, strategy_used="regex")

        return FallbackResult(
            success=False, data=None, strategy_used="regex",
            error="No fields extracted"
        )

    def _try_regex_extraction(
        self, prompt: str, schema: dict[str, Any] | None
    ) -> FallbackResult:
        """Strategy 3: Re-call LLM and regex extract (only when first two steps fail)."""
        try:
            response = self.llm_call(prompt + "\n\nBe concise.")
            return self._try_regex_from_response(response, schema)
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
        """Strategy 4: Return safe default value."""
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
    Small Model Optimizer

    Integrates all small model adaptation strategies.
    """

    def __init__(self, llm_call: Callable[[str], str]):
        self.cot = ChainOfThoughtPrompts()
        self.fallback = FallbackStrategy(llm_call)
        self.validator = OutputValidator()

    def create_task_plan(
        self, task: str, context: str = ""
    ) -> dict[str, Any]:
        """
        Create task plan (with CoT optimization).

        Args:
            task: Task description
            context: Project context

        Returns:
            Parsed plan data
        """
        prompt = f"""{self.cot.TASK_DECOMPOSITION_EXAMPLES}

## Task
{task}

{self.cot.TOOL_SELECTION_EXAMPLES}

{self.cot.ERROR_RECOVERY_EXAMPLES}

Now analyze the task and output JSON:"""

        if context:
            prompt += f"\n\n## Current Project State\n{context}"

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

        # Return default plan
        return {
            "analysis": "Using default plan",
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
        Generate action command (with CoT optimization).

        Args:
            task_description: Task description
            execution_summary: Completed execution history

        Returns:
            Action parameter dictionary
        """
        prompt = f"""You are a programming assistant.

## Current Task
{task_description}

## Completed Tasks
{execution_summary or "None"}

## Rules
1. Must use write or edit commands
2. Do NOT use finish or debug commands
3. Must include concrete file content

## Output Format
Return JSON:
{{"command": "write", "path": "filename.py", "content": "file content"}}
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

        # Return default action
        return {"command": "debug", "content": "Unable to generate valid action"}

    def get_strategy_report(self) -> str:
        """Get strategy usage report."""
        lines = ["## Fallback Strategy Report\n"]

        strategies = self.fallback.strategy_history
        if not strategies:
            return "No strategy usage recorded"

        from collections import Counter
        counter = Counter(strategies)

        lines.append(f"Total calls: {len(strategies)}\n")
        lines.append("Strategy usage statistics:")
        for strategy, count in counter.most_common():
            lines.append(f"  - {strategy}: {count} ({count/len(strategies)*100:.1f}%)")

        return "\n".join(lines)
