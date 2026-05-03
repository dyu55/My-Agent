"""Model Provider - Unified model selection and management.

支持多种 LLM 后端:
- Ollama (本地小模型)
- OpenAI API
- Anthropic API
- Google AI (Gemini)
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import ollama


@dataclass
class ModelInfo:
    """Model information."""
    name: str
    provider: str
    size: str | None = None
    modified: str | None = None
    description: str | None = None


class BaseModelProvider(ABC):
    """Base class for model providers."""

    @abstractmethod
    def chat(self, prompt: str, **kwargs) -> str:
        """Send a chat request."""
        pass

    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        """List available models."""
        pass

    def health_check(self) -> bool:
        """Check if provider is healthy. Override in subclasses."""
        return True


class OllamaProvider(BaseModelProvider):
    """Ollama provider for local/remote models and Ollama Cloud.

    Supports:
    - Local Ollama (http://localhost:11434)
    - Remote Ollama server (e.g., http://192.168.0.124:11434)
    - Ollama Cloud (https://cloud.ollama.ai with API key)
    """

    def __init__(
        self,
        model: str = "gemma4:latest",
        base_url: str = "http://localhost:11434",
        timeout: int = 600,  # 10 minutes default for slow remote servers
        api_key: str | None = None,  # For Ollama Cloud authentication
    ):
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.api_key = api_key or os.getenv("OLLAMA_API_KEY")

        # Create client with auth headers if API key provided (for Ollama Cloud)
        if self.api_key:
            self.client = ollama.Client(
                host=base_url,
                timeout=timeout,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        else:
            self.client = ollama.Client(host=base_url, timeout=timeout)

    def chat(self, prompt: str, **kwargs) -> str:
        """Send a chat request to Ollama."""
        messages = [{"role": "user", "content": prompt}]

        kwargs.setdefault("model", self.model)
        kwargs.setdefault("messages", messages)

        # Don't force JSON format - let model respond naturally
        # kwargs.setdefault("format", "json")

        if "options" not in kwargs:
            kwargs["options"] = {
                "temperature": kwargs.pop("temperature", 0.1),
            }

        response = self.client.chat(**kwargs)
        return response["message"]["content"]

    def list_models(self) -> list[ModelInfo]:
        """List installed Ollama models."""
        models = []
        try:
            response = self.client.list()
            # Handle both dict and ListResponse object formats
            model_list = response.models if hasattr(response, 'models') else response.get("models", [])
            for model in model_list:
                # Handle both dict and Model object formats
                name = model.model if hasattr(model, 'model') else model.get("name")
                size = model.size if hasattr(model, 'size') else model.get("size")
                modified = model.modified_at if hasattr(model, 'modified_at') else model.get("modified_at")
                models.append(ModelInfo(
                    name=name,
                    provider="ollama",
                    size=size,
                    modified=modified,
                ))
        except Exception as e:
            print(f"Error listing models: {e}")
        return models

    def pull_model(self, model_name: str) -> bool:
        """Pull a new model from Ollama registry."""
        try:
            for progress in self.client.pull(model_name, stream=True):
                if progress.get("status") == "success":
                    return True
            return True
        except Exception:
            return False


class OpenAIProvider(BaseModelProvider):
    """OpenAI API provider."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url

        from openai import OpenAI
        self.client = OpenAI(base_url=base_url, api_key=self.api_key)

    def chat(self, prompt: str, **kwargs) -> str:
        """Send a chat request to OpenAI."""
        messages = [{"role": "user", "content": prompt}]

        kwargs.setdefault("model", self.model)
        kwargs.setdefault("messages", messages)
        kwargs.setdefault("response_format", {"type": "json_object"})

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or "{}"

    def list_models(self) -> list[ModelInfo]:
        """List available OpenAI models (returns common models)."""
        return [
            ModelInfo(name="gpt-4o", provider="openai", description="Most capable model"),
            ModelInfo(name="gpt-4o-mini", provider="openai", description="Fast, cheap"),
            ModelInfo(name="gpt-4-turbo", provider="openai", description="Fast GPT-4"),
            ModelInfo(name="o1-preview", provider="openai", description="Reasoning model"),
            ModelInfo(name="o1-mini", provider="openai", description="Fast reasoning"),
        ]


class AnthropicProvider(BaseModelProvider):
    """Anthropic API provider."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

        import anthropic
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def chat(self, prompt: str, **kwargs) -> str:
        """Send a chat request to Anthropic."""
        kwargs.setdefault("model", self.model)
        kwargs.setdefault("messages", [{"role": "user", "content": prompt}])
        kwargs.setdefault("max_tokens", 1024)

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def list_models(self) -> list[ModelInfo]:
        """List available Anthropic models."""
        return [
            ModelInfo(name="claude-opus-4-20250514", provider="anthropic", description="Most capable"),
            ModelInfo(name="claude-sonnet-4-20250514", provider="anthropic", description="Balanced"),
            ModelInfo(name="claude-haiku-4-20250514", provider="anthropic", description="Fast, cheap"),
        ]


class ModelProviderFactory:
    """Factory for creating model providers."""

    _providers: dict[str, type[BaseModelProvider]] = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }

    @classmethod
    def create(cls, provider: str, **kwargs) -> BaseModelProvider:
        """Create a model provider."""
        provider = provider.lower()
        if provider not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")

        return cls._providers[provider](**kwargs)

    @classmethod
    def register(cls, name: str, provider_class: type[BaseModelProvider]) -> None:
        """Register a new provider."""
        cls._providers[name.lower()] = provider_class

    @classmethod
    def list_providers(cls) -> list[str]:
        """List available provider names."""
        return list(cls._providers.keys())


class ModelManager:
    """
    Manages model selection and switching.

    Usage:
        manager = ModelManager()
        manager.set_model("ollama", "gemma4:latest")

        # Use anywhere
        response = manager.chat("Hello!")

        # List available models
        models = manager.list_available_models()
    """

    def __init__(
        self,
        default_provider: str = "ollama",
        default_model: str = "gemma4:latest",
        base_url: str | None = None,
    ):
        self.current_provider = default_provider
        self.current_model = default_model
        self.base_url = base_url
        self._provider: BaseModelProvider | None = None
        self._init_provider()

    def _init_provider(self) -> None:
        """Initialize the current provider."""
        # Get API key for Ollama Cloud
        ollama_api_key = os.getenv("OLLAMA_API_KEY")

        provider_config = {
            "ollama": {
                "model": self.current_model,
                "base_url": self.base_url or os.getenv("OLLAMA_HOST", "http://192.168.0.124:11434"),
                "api_key": ollama_api_key,
            },
            "openai": {"model": os.getenv("OPENAI_MODEL", "gpt-4o-mini")},
            "anthropic": {"model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")},
        }

        kwargs = provider_config.get(self.current_provider, {})
        self._provider = ModelProviderFactory.create(self.current_provider, **kwargs)

    def set_model(self, provider: str, model: str | None = None) -> bool:
        """
        Switch to a different model.

        Args:
            provider: Provider name (ollama, openai, anthropic)
            model: Model name (optional, uses default if not specified)

        Returns:
            True if successful
        """
        try:
            self.current_provider = provider.lower()

            if model:
                self.current_model = model
            else:
                # Use default model for provider
                defaults = {
                    "ollama": "gemma4:latest",
                    "openai": "gpt-4o-mini",
                    "anthropic": "claude-sonnet-4-20250514",
                }
                self.current_model = defaults.get(self.current_provider, "gemma4:latest")

            self._init_provider()
            return True
        except Exception:
            return False

    def chat(self, prompt: str, **kwargs) -> str:
        """
        Send a chat request to the current model.

        Args:
            prompt: The prompt to send
            **kwargs: Additional parameters (temperature, etc.)

        Returns:
            Model response as string
        """
        if self._provider is None:
            self._init_provider()

        return self._provider.chat(prompt, **kwargs)

    def list_available_models(self) -> list[ModelInfo]:
        """
        List all available models from current provider.

        Returns:
            List of ModelInfo objects
        """
        if self._provider is None:
            self._init_provider()

        return self._provider.list_models()

    @property
    def current_info(self) -> ModelInfo:
        """Get current model information."""
        return ModelInfo(
            name=self.current_model,
            provider=self.current_provider,
        )

    def get_status(self) -> str:
        """Get current model status as string."""
        return f"{self.current_provider}/{self.current_model}"

    def health_check(self) -> bool:
        """Check if the current provider is healthy and accessible."""
        try:
            if self._provider is None:
                self._init_provider()

            if isinstance(self._provider, OllamaProvider):
                # Ollama: check if server is reachable
                import urllib.request
                import json
                url = f"{self._provider.base_url}/api/tags"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=5) as response:
                    return response.status == 200
            elif isinstance(self._provider, OpenAIProvider):
                # OpenAI: try a simple models list
                self._provider.client.models.list()
                return True
            elif isinstance(self._provider, AnthropicProvider):
                # Anthropic: try a simple message
                self._provider.client.messages.create(
                    model=self._provider.model,
                    max_tokens=1,
                    messages=[{"role": "user", "content": "hi"}]
                )
                return True
            return False
        except Exception:
            return False
