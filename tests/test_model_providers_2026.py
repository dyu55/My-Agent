"""Tests for 2026 model providers and profile configurations."""

from utils.model_provider import (
    ModelManager,
    ModelProviderFactory,
    OpenAIProvider,
    AnthropicProvider,
    DeepSeekProvider,
    GeminiProvider,
    OllamaProvider,
)
from utils.small_model import ModelProfile, get_model_profile


def test_2026_model_profiles():
    # Frontier models -> large profile
    p_opus = get_model_profile("claude-opus-5-latest")
    assert p_opus.size_category == "large"
    assert p_opus.max_context_tokens >= 32768

    p_sol = get_model_profile("gpt-5.6-sol")
    assert p_sol.size_category == "large"

    p_gemini = get_model_profile("gemini-3.1-pro")
    assert p_gemini.size_category == "large"

    # 26B-31B local models -> medium profile
    p_gemma = get_model_profile("gemma-4-31b-it")
    assert p_gemma.size_category == "medium"
    assert p_gemma.param_billions == 31.0

    p_qwen = get_model_profile("qwen3.6-27b")
    assert p_qwen.size_category == "medium"
    assert p_qwen.param_billions == 27.0


def test_provider_model_lists():
    # OpenAI
    openai_p = OpenAIProvider(api_key="mock")
    openai_models = [m.name for m in openai_p.list_models()]
    assert "gpt-5.6-sol" in openai_models
    assert "o3-mini" in openai_models

    # Anthropic
    anthropic_p = AnthropicProvider(api_key="mock")
    anthropic_models = [m.name for m in anthropic_p.list_models()]
    assert "claude-opus-5-latest" in anthropic_models
    assert "claude-3-7-sonnet-latest" in anthropic_models

    # DeepSeek
    deepseek_p = DeepSeekProvider(api_key="mock")
    deepseek_models = [m.name for m in deepseek_p.list_models()]
    assert "deepseek-v4-pro" in deepseek_models
    assert "deepseek-v4-flash" in deepseek_models

    # Gemini
    gemini_p = GeminiProvider(api_key="mock")
    gemini_models = [m.name for m in gemini_p.list_models()]
    assert "gemini-3.1-pro" in gemini_models
    assert "gemma-4-31b-it" in gemini_models


def test_model_manager_defaults():
    manager = ModelManager()
    assert manager.get_last_reasoning() is None
