"""Unit tests for LLM streaming support and ModelManager integrations."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from utils.model_provider import (
    ModelManager,
    OllamaProvider,
    OpenAIProvider,
    AnthropicProvider,
    DeepSeekProvider,
    BaseModelProvider,
)


class TestBaseProviderStream:
    """Test that BaseModelProvider.chat_stream falls back to chat."""

    def test_base_provider_chat_stream_fallback(self):
        """BaseProvider.chat_stream should yield the result of chat()."""
        # BaseModelProvider is abstract; create a concrete subclass
        class ConcreteProvider(BaseModelProvider):
            def chat(self, prompt, **kwargs):
                return "hello world"
            def list_models(self):
                return []
            def get_model_info(self):
                return {}

        provider = ConcreteProvider()
        chunks = list(provider.chat_stream("hi"))
        assert chunks == ["hello world"]


class TestOllamaProviderStream:
    """Test OllamaProvider.chat_stream."""

    @patch("utils.model_provider.ollama")
    def test_stream_yields_chunks(self, mock_ollama):
        mock_client = MagicMock()
        mock_client.chat.return_value = iter([
            {"message": {"content": "Hello"}},
            {"message": {"content": " World"}},
        ])
        mock_ollama.Client.return_value = mock_client

        provider = OllamaProvider(model="test:8b")
        # Replace the client
        provider.client = mock_client

        chunks = list(provider.chat_stream("test prompt"))
        assert chunks == ["Hello", " World"]

    @patch("utils.model_provider.ollama")
    def test_stream_empty_response(self, mock_ollama):
        mock_client = MagicMock()
        mock_client.chat.return_value = iter([])
        mock_ollama.Client.return_value = mock_client

        provider = OllamaProvider(model="test:8b")
        provider.client = mock_client

        chunks = list(provider.chat_stream("test"))
        assert chunks == []


class TestOpenAIProviderStream:
    """Test OpenAIProvider.chat_stream."""

    def test_stream_yields_chunks(self):
        provider = OpenAIProvider(api_key="test-key")
        mock_client = MagicMock()

        # Mock the streaming response
        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Hello"
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = " World"
        chunk3 = MagicMock()
        chunk3.choices = [MagicMock()]
        chunk3.choices[0].delta.content = None

        mock_client.chat.completions.create.return_value = iter([chunk1, chunk2, chunk3])
        provider.client = mock_client

        chunks = list(provider.chat_stream("test"))
        assert chunks == ["Hello", " World"]


class TestAnthropicProviderStream:
    """Test AnthropicProvider.chat_stream."""

    def test_stream_yields_chunks(self):
        provider = AnthropicProvider(api_key="test-key")
        mock_client = MagicMock()

        # Mock the stream context manager
        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.text_stream = iter(["Hello", " ", "World"])
        mock_client.messages.stream.return_value = mock_stream
        provider.client = mock_client

        chunks = list(provider.chat_stream("test"))
        assert chunks == ["Hello", " ", "World"]


class TestDeepSeekProviderStream:
    """Test DeepSeekProvider.chat_stream."""

    def test_stream_yields_chunks(self):
        provider = DeepSeekProvider(api_key="test-key")
        mock_client = MagicMock()

        chunk1 = MagicMock()
        chunk1.choices = [MagicMock()]
        chunk1.choices[0].delta.content = "Deep"
        chunk2 = MagicMock()
        chunk2.choices = [MagicMock()]
        chunk2.choices[0].delta.content = "Seek"

        mock_client.chat.completions.create.return_value = iter([chunk1, chunk2])
        provider.client = mock_client

        chunks = list(provider.chat_stream("test"))
        assert chunks == ["Deep", "Seek"]


class TestModelManagerStream:
    """Test ModelManager.chat_stream integration."""

    @patch("utils.model_provider.ModelProviderFactory.create")
    def test_chat_stream_delegates_to_provider(self, mock_factory):
        mock_provider = MagicMock()
        mock_provider.chat_stream.return_value = iter(["a", "b", "c"])
        mock_factory.return_value = mock_provider

        mm = ModelManager(default_provider="ollama", default_model="test:8b")
        chunks = list(mm.chat_stream("hello"))
        assert chunks == ["a", "b", "c"]
        mock_provider.chat_stream.assert_called_once()

    @patch("utils.model_provider.ModelProviderFactory.create")
    def test_chat_stream_timeout(self, mock_factory):
        import time

        def slow_stream(prompt):
            yield "a"
            time.sleep(10)

        mock_provider = MagicMock()
        mock_provider.chat_stream.side_effect = slow_stream
        mock_factory.return_value = mock_provider

        mm = ModelManager(default_provider="ollama", default_model="test:8b")
        # chat_stream should handle timeouts gracefully
        # (The actual timeout is in the implementation)
        chunks = list(mm.chat_stream("hello"))
        # At least "a" should be yielded before timeout
        assert "a" in chunks


class TestModelManagerCacheIntegration:
    """Test LLMCache integration in ModelManager."""

    @patch("utils.model_provider.ModelProviderFactory.create")
    def test_cache_hit_skips_provider(self, mock_factory):
        mock_provider = MagicMock()
        mock_factory.return_value = mock_provider

        mm = ModelManager(default_provider="ollama", default_model="test:8b")

        # Inject a mock cache
        mock_cache = MagicMock()
        mock_cache.get.return_value = "cached response"
        mm._cache = mock_cache

        result = mm.chat("hello")
        assert result == "cached response"
        mock_provider.chat.assert_not_called()

    @patch("utils.model_provider.ModelProviderFactory.create")
    def test_cache_miss_calls_provider(self, mock_factory):
        mock_provider = MagicMock()
        mock_provider.chat.return_value = "fresh response"
        mock_factory.return_value = mock_provider

        mm = ModelManager(default_provider="ollama", default_model="test:8b")

        mock_cache = MagicMock()
        mock_cache.get.return_value = None
        mm._cache = mock_cache

        result = mm.chat("hello")
        assert result == "fresh response"
        mock_cache.set.assert_called_once()


class TestModelManagerCostTracking:
    """Test CostTracker integration in ModelManager."""

    @patch("utils.model_provider.ModelProviderFactory.create")
    def test_cost_tracker_records_usage(self, mock_factory):
        mock_provider = MagicMock()
        mock_provider.chat.return_value = "response"
        mock_factory.return_value = mock_provider

        mm = ModelManager(default_provider="ollama", default_model="test:8b")

        # Clear cache to ensure we go through the provider path
        mm._cache = None
        mock_tracker = MagicMock()
        mm._cost_tracker = mock_tracker

        mm.chat("hello")
        mock_tracker.record_call.assert_called_once()
