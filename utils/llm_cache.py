"""LLM Cache - Caching for LLM responses to reduce costs and improve speed."""

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CacheEntry:
    """A cached LLM response."""
    prompt_hash: str
    response: str
    model: str
    provider: str
    created_at: float
    hit_count: int = 0
    last_accessed: float = 0.0
    latency_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_hash": self.prompt_hash,
            "response": self.response,
            "model": self.model,
            "provider": self.provider,
            "created_at": self.created_at,
            "hit_count": self.hit_count,
            "last_accessed": self.last_accessed,
            "latency_ms": self.latency_ms,
        }


@dataclass
class CacheStats:
    """Cache statistics."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    tokens_saved: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

    @property
    def time_saved_ms(self) -> float:
        # Estimate ~50ms per cached request vs full LLM call
        return self.cache_hits * 50.0


class LLMCache:
    """
    LLM response cache with hash-based lookup.

    Caches LLM responses to reduce API calls, costs, and latency.
    Uses SHA-256 hash of prompt for cache keys.
    """

    def __init__(
        self,
        cache_dir: str | None = None,
        max_entries: int = 1000,
        ttl_seconds: int = 86400 * 7,  # 7 days default
    ):
        if cache_dir is None:
            cache_dir = "memory/llm_cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_file = self.cache_dir / "cache.json"
        self.stats_file = self.cache_dir / "stats.json"

        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds

        self._cache: dict[str, CacheEntry] = {}
        self._stats = CacheStats()

        self._load_cache()
        self._load_stats()

    def _load_cache(self) -> None:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for key, value in data.items():
                    entry = CacheEntry(**value)
                    # Check TTL
                    if time.time() - entry.created_at < self.ttl_seconds:
                        self._cache[key] = entry

            except (json.JSONDecodeError, KeyError, TypeError):
                pass

    def _save_cache(self) -> None:
        """Save cache to disk."""
        # Limit entries
        if len(self._cache) > self.max_entries:
            # Remove oldest entries
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: x[1].created_at,
            )
            for key, _ in sorted_entries[:len(self._cache) - self.max_entries]:
                del self._cache[key]

        data = {k: v.to_dict() for k, v in self._cache.items()}

        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_stats(self) -> None:
        """Load statistics from disk."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._stats = CacheStats(**data)
            except (json.JSONDecodeError, KeyError, TypeError):
                pass

    def _save_stats(self) -> None:
        """Save statistics to disk."""
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(self._stats.__dict__, f, indent=2)

    def _hash_prompt(self, prompt: str, model: str, provider: str) -> str:
        """Generate cache key from prompt and model."""
        content = f"{provider}:{model}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()

    def get(
        self,
        prompt: str,
        model: str,
        provider: str = "ollama",
    ) -> str | None:
        """
        Get cached response if available.

        Args:
            prompt: The prompt to look up
            model: Model name
            provider: Provider name

        Returns:
            Cached response or None if not found
        """
        self._stats.total_requests += 1

        cache_key = self._hash_prompt(prompt, model, provider)
        entry = self._cache.get(cache_key)

        if entry is None:
            self._stats.cache_misses += 1
            self._save_stats()
            return None

        # Check TTL
        if time.time() - entry.created_at >= self.ttl_seconds:
            del self._cache[cache_key]
            self._stats.cache_misses += 1
            self._save_stats()
            return None

        # Update access stats
        entry.hit_count += 1
        entry.last_accessed = time.time()
        self._stats.cache_hits += 1

        self._save_stats()
        self._save_cache()

        return entry.response

    def set(
        self,
        prompt: str,
        response: str,
        model: str,
        provider: str = "ollama",
        latency_ms: float | None = None,
    ) -> None:
        """
        Cache a response.

        Args:
            prompt: The prompt that generated the response
            response: The LLM response
            model: Model name
            provider: Provider name
            latency_ms: Response latency in milliseconds
        """
        cache_key = self._hash_prompt(prompt, model, provider)

        entry = CacheEntry(
            prompt_hash=cache_key,
            response=response,
            model=model,
            provider=provider,
            created_at=time.time(),
            last_accessed=time.time(),
            latency_ms=latency_ms,
        )

        self._cache[cache_key] = entry
        self._save_cache()

    def invalidate(
        self,
        prompt: str | None = None,
        model: str | None = None,
        provider: str | None = None,
    ) -> int:
        """
        Invalidate cache entries.

        Args:
            prompt: Specific prompt to invalidate
            model: Invalidate all entries for this model
            provider: Invalidate all entries for this provider

        Returns:
            Number of entries invalidated
        """
        count = 0

        if prompt:
            # Invalidate specific prompt across all models
            for key, entry in list(self._cache.items()):
                if entry.prompt_hash == hashlib.sha256(prompt.encode()).hexdigest():
                    del self._cache[key]
                    count += 1
        else:
            # Invalidate by model/provider
            to_remove = []
            for key, entry in self._cache.items():
                if model and entry.model != model:
                    continue
                if provider and entry.provider != provider:
                    continue
                to_remove.append(key)

            for key in to_remove:
                del self._cache[key]
                count += 1

        if count > 0:
            self._save_cache()

        return count

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        self._save_cache()
        return count

    def stats(self) -> CacheStats:
        """Get cache statistics."""
        # Update from loaded cache
        self._stats.cache_hits = sum(e.hit_count for e in self._cache.values())
        self._stats.total_latency_ms = sum(
            e.latency_ms or 0 for e in self._cache.values() if e.latency_ms
        )

        return self._stats

    def get_stats_summary(self) -> str:
        """Get a human-readable stats summary."""
        stats = self.stats()

        return f"""LLM Cache Statistics:
  Total requests: {stats.total_requests}
  Cache hits: {stats.cache_hits}
  Cache misses: {stats.cache_misses}
  Hit rate: {stats.hit_rate * 100:.1f}%
  Estimated time saved: {stats.time_saved_ms / 1000:.1f}s
  Cached entries: {len(self._cache)}"""


def cached_llm_call(
    llm_func,
    cache: LLMCache,
    prompt: str,
    model: str,
    provider: str = "ollama",
):
    """
    Wrapper for LLM calls with caching.

    Args:
        llm_func: The LLM chat function
        cache: LLMCache instance
        prompt: The prompt
        model: Model name
        provider: Provider name

    Returns:
        LLM response (cached or fresh)
    """
    # Check cache first
    cached = cache.get(prompt, model, provider)
    if cached is not None:
        return cached

    # Call LLM
    start = time.time()
    response = llm_func(prompt)
    latency_ms = (time.time() - start) * 1000

    # Cache response
    cache.set(prompt, response, model, provider, latency_ms)

    return response


# Global cache instance
_global_cache: LLMCache | None = None


def get_global_cache(cache_dir: str | None = None) -> LLMCache:
    """Get or create the global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = LLMCache(cache_dir=cache_dir)
    return _global_cache


def cached_chat(prompt: str, model: str, provider: str = "ollama") -> str:
    """
    Cached chat function for use with ModelProvider.

    Returns cached response if available, otherwise calls the LLM.
    """
    cache = get_global_cache()
    cached = cache.get(prompt, model, provider)

    if cached is not None:
        return cached

    # Import here to avoid circular imports
    from utils.model_provider import ModelManager

    manager = ModelManager()
    response = manager.chat(prompt)

    cache.set(prompt, response, model, provider)

    return response
