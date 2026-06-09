"""Unit tests for ModelProfile — model size detection and adaptive behavior."""

import pytest
from utils.small_model import ModelProfile, get_model_profile, clear_profile_cache


class TestModelProfileDetection:
    """Test model size detection from name."""

    def test_8b_model_detected(self):
        p = ModelProfile.from_model_name("qwen3.5:8b")
        assert p.size_category == "small"
        assert p.param_billions == 8.0

    def test_9b_model_detected(self):
        p = ModelProfile.from_model_name("gemma3:9b")
        assert p.size_category == "small"
        assert p.param_billions == 9.0

    def test_26b_model_detected(self):
        p = ModelProfile.from_model_name("qwen2.5:26b")
        assert p.size_category == "medium"
        assert p.param_billions == 26.0

    def test_31b_model_detected(self):
        p = ModelProfile.from_model_name("codellama:31b")
        assert p.size_category == "medium"
        assert p.param_billions == 31.0

    def test_70b_model_detected(self):
        p = ModelProfile.from_model_name("llama3:70b")
        assert p.size_category == "large"
        assert p.param_billions == 70.0

    def test_7b_model_detected(self):
        p = ModelProfile.from_model_name("mistral:7b")
        assert p.size_category == "small"
        assert p.param_billions == 7.0

    def test_1b_model_detected(self):
        p = ModelProfile.from_model_name("tiny:1b")
        assert p.size_category == "small"
        assert p.param_billions == 1.0

    def test_3b_model_detected(self):
        p = ModelProfile.from_model_name("phi:3b")
        assert p.size_category == "small"
        assert p.param_billions == 3.0

    def test_unknown_model_defaults_to_medium(self):
        p = ModelProfile.from_model_name("unknown-model")
        assert p.size_category == "medium"

    def test_model_name_with_colon(self):
        p = ModelProfile.from_model_name("qwen3:8b")
        assert p.size_category == "small"
        assert p.param_billions == 8.0

    def test_model_name_with_dash(self):
        p = ModelProfile.from_model_name("deepseek-v2:16b")
        assert p.param_billions == 16.0

    def test_latest_suffix(self):
        p = ModelProfile.from_model_name("gemma4:latest")
        # "latest" has no size, falls back to known_sizes mapping
        assert p.size_category in ("small", "medium", "large")


class TestModelProfileLimits:
    """Test that limits are set correctly per category."""

    def test_small_profile_limits(self):
        p = ModelProfile._small_profile(9)
        assert p.max_context_tokens == 4096
        assert p.max_file_context_files == 10
        assert p.max_prompt_chars == 2000
        assert p.max_history_messages == 5
        assert p.prefer_short_prompts is True

    def test_medium_profile_limits(self):
        p = ModelProfile._medium_profile(26)
        assert p.max_context_tokens == 8192
        assert p.max_file_context_files == 25
        assert p.max_prompt_chars == 4000
        assert p.max_history_messages == 10
        assert p.prefer_short_prompts is False

    def test_large_profile_limits(self):
        p = ModelProfile._large_profile(70)
        assert p.max_context_tokens == 32768
        assert p.max_file_context_files == 50
        assert p.max_prompt_chars == 8000
        assert p.max_history_messages == 20
        assert p.prefer_short_prompts is False

    def test_small_uses_short_prompts(self):
        p = ModelProfile.from_model_name("qwen3:8b")
        assert p.prefer_short_prompts is True

    def test_medium_does_not_use_short_prompts(self):
        p = ModelProfile.from_model_name("qwen2.5:26b")
        assert p.prefer_short_prompts is False

    def test_frozen_dataclass(self):
        p = ModelProfile.from_model_name("qwen3:8b")
        with pytest.raises(AttributeError):
            p.size_category = "large"


class TestModelProfileCache:
    """Test profile caching."""

    def setup_method(self):
        clear_profile_cache()

    def test_cache_returns_same_instance(self):
        p1 = get_model_profile("qwen3:8b")
        p2 = get_model_profile("qwen3:8b")
        assert p1 is p2

    def test_different_models_different_instances(self):
        p1 = get_model_profile("qwen3:8b")
        p2 = get_model_profile("llama3:70b")
        assert p1 is not p2
        assert p1.size_category != p2.size_category

    def test_clear_cache(self):
        p1 = get_model_profile("qwen3:8b")
        clear_profile_cache()
        p2 = get_model_profile("qwen3:8b")
        assert p1 is not p2  # New instance after clear
        assert p1.size_category == p2.size_category  # Same values


class TestExtractParamSize:
    """Test the param size extraction helper."""

    def test_simple_b_suffix(self):
        assert ModelProfile._extract_param_size("8b") == 8.0

    def test_b_with_colon(self):
        assert ModelProfile._extract_param_size("model:9b") == 9.0

    def test_decimal_size(self):
        assert ModelProfile._extract_param_size("1.5b") == 1.5

    def test_no_size_info(self):
        # Should fall back to known_sizes or default
        result = ModelProfile._extract_param_size("gemma")
        assert result == 9  # Known mapping

    def test_known_model_phi(self):
        assert ModelProfile._extract_param_size("phi-3") == 3

    def test_known_model_mistral(self):
        assert ModelProfile._extract_param_size("mistral-instruct") == 7
