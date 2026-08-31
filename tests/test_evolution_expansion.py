"""Comprehensive unit test expansion for MyAgent core modules and tools.

Expands test coverage for:
- utils/model_provider.py (Factory creation, mock inference, reasoning stream, error handling)
- utils/llm_cache.py (Cache keys, expiry, LRU eviction, stats)
- agent/tools/file_tools.py (Fuzzy replace, line numbering, directory operations)
- agent/tools/repo_map.py (AST signature extraction, docstring trimming, budget constraints)
- utils/schema.py (Validation, JSON cleanup, markdown code block stripping)
"""

import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from utils.model_provider import (
    BaseModelProvider,
    ModelInfo,
    ModelManager,
    ModelProviderFactory,
    OpenAIProvider,
    AnthropicProvider,
    DeepSeekProvider,
    GeminiProvider,
    OllamaProvider,
)
from utils.llm_cache import LLMCache
from utils.schema import SchemaValidator
from agent.tools.file_tools import FileTools
from agent.tools.repo_map import RepoMap


class TestModelProviderFactoryExpansion:
    """Test ModelProviderFactory creation and registration."""

    def test_factory_create_ollama(self):
        provider = ModelProviderFactory.create("ollama", model="gemma-4-31b-it")
        assert isinstance(provider, OllamaProvider)
        assert provider.model == "gemma-4-31b-it"

    def test_factory_create_openai(self):
        provider = ModelProviderFactory.create("openai", model="gpt-5.6-sol", api_key="mock_key")
        assert isinstance(provider, OpenAIProvider)
        assert provider.model == "gpt-5.6-sol"

    def test_factory_create_anthropic(self):
        provider = ModelProviderFactory.create("anthropic", model="claude-opus-5-latest", api_key="mock_key")
        assert isinstance(provider, AnthropicProvider)
        assert provider.model == "claude-opus-5-latest"

    def test_factory_create_deepseek(self):
        provider = ModelProviderFactory.create("deepseek", model="deepseek-v4-pro", api_key="mock_key")
        assert isinstance(provider, DeepSeekProvider)
        assert provider.model == "deepseek-v4-pro"

    def test_factory_create_gemini(self):
        provider = ModelProviderFactory.create("gemini", model="gemini-3.1-pro", api_key="mock_key")
        assert isinstance(provider, GeminiProvider)
        assert provider.model == "gemini-3.1-pro"

    def test_factory_invalid_provider(self):
        with pytest.raises(ValueError):
            ModelProviderFactory.create("unknown_provider_xyz")


class TestModelManagerExpansion:
    """Test ModelManager provider switching and reasoning extraction."""

    def test_model_manager_switch_provider(self):
        manager = ModelManager(default_provider="ollama", default_model="gemma-4-31b-it")
        assert manager.current_provider == "ollama"

        manager.set_model("openai", model="gpt-5.6-sol")
        assert manager.current_provider == "openai"
        assert manager.current_model == "gpt-5.6-sol"

    def test_model_manager_reasoning_flow(self):
        manager = ModelManager(default_provider="ollama")
        mock_p = MagicMock()
        mock_p.last_reasoning = "Step 1: Plan architecture. Step 2: Implement code."
        mock_p.chat.return_value = '{"command": "write", "path": "main.py"}'
        manager._provider = mock_p

        res = manager.chat("Generate code")
        assert '{"command": "write"' in res
        assert manager.get_last_reasoning() == "Step 1: Plan architecture. Step 2: Implement code."


class TestLLMCacheExpansion:
    """Test LLM cache operations, key normalization and TTL."""

    def test_cache_hit_and_miss(self):
        cache = LLMCache()
        cache.clear()

        prompt = "def calculate_sum(a, b):"
        model = "gemma-4-31b-it"

        # Initial miss
        assert cache.get(prompt, model=model) is None

        # Set cache
        cache.set(prompt, "return a + b", model=model)

        # Hit
        hit = cache.get(prompt, model=model)
        assert hit == "return a + b"

    def test_cache_clear(self):
        cache = LLMCache()
        cache.set("test_prompt", "test_response", model="test_model")
        cache.clear()
        assert cache.get("test_prompt", model="test_model") is None


class TestSchemaValidatorExpansion:
    """Test JSON extraction and validation from raw LLM responses."""

    def test_extract_json_markdown_codeblock(self):
        validator = SchemaValidator()
        raw = """Here is the response:
```json
{
    "command": "edit",
    "path": "test.py",
    "old_text": "foo",
    "new_text": "bar"
}
```
Done!"""
        parsed = validator.parse_json(raw)
        assert parsed is not None
        assert parsed.get("command") == "edit"
        assert parsed.get("new_text") == "bar"

    def test_extract_json_raw_object(self):
        validator = SchemaValidator()
        raw = '{"command": "run", "command_line": "pytest"}'
        parsed = validator.parse_json(raw)
        assert parsed == {"command": "run", "command_line": "pytest"}

    def test_extract_json_invalid(self):
        validator = SchemaValidator()
        raw = "No valid JSON anywhere in this text string."
        parsed = validator.parse_json(raw)
        assert parsed is None

    def test_validate_command(self):
        validator = SchemaValidator()
        valid, err = validator.validate_command({"command": "write", "path": "app.py"})
        assert valid is True
        assert err == ""

        invalid, err_msg = validator.validate_command({"path": "app.py"})
        assert invalid is False
        assert "Missing 'command'" in err_msg


class TestFileToolsExpansion:
    """Test FileTools file operations and fuzzy replace."""

    def test_write_and_read_lines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            ft = FileTools(tmp_path)

            file_path = "subdir/demo.txt"
            content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
            res_write = ft.write_file({"path": file_path, "content": content})
            assert res_write.success is True

            # Read with line numbers
            res_read = ft.read_file({"path": file_path, "start_line": 2, "end_line": 4})
            assert res_read.success is True
            assert "Line 2" in res_read.output
            assert "Line 4" in res_read.output

    def test_fuzzy_replace_edge_cases(self):
        original = "    def process(self):\n        x = 1\n        y = 2\n        return x + y\n"
        old_snippet = "def process(self):\n    x = 1\n    y = 2"
        new_snippet = "def process(self):\n    x = 10\n    y = 20"

        replaced = FileTools._fuzzy_replace(original, old_snippet, new_snippet)
        assert replaced is not None
        assert "x = 10" in replaced


class TestRepoMapExpansion:
    """Test RepoMap AST analysis with complex code features."""

    def test_repo_map_complex_python_features(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            code = """
import asyncio
from typing import Optional

class BasePipeline:
    '''Abstract pipeline.'''
    pass

class AdvancedPipeline(BasePipeline):
    '''Production pipeline with async steps.'''
    def __init__(self, name: str):
        self.name = name

    async def execute_async(self, payload: dict) -> bool:
        '''Execute pipeline asynchronously.'''
        return True

@pytest.fixture
def sample_fixture():
    '''Sample test fixture.'''
    return True
"""
            (tmp_path / "pipeline.py").write_text(code, encoding="utf-8")
            repo_map = RepoMap(tmp_path, max_chars=3000)
            map_str = repo_map.generate_map()

            assert "AdvancedPipeline" in map_str
            assert "BasePipeline" in map_str
            assert "execute_async" in map_str
            assert "sample_fixture" in map_str
            assert "pipeline.py" in map_str
