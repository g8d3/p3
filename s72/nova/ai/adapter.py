"""Unified AI Adapter — all providers implement this interface.

Supports cascade (primary → fallback → local),
streaming, caching, and full observability.
"""

from __future__ import annotations
import json
import os
import time
import hashlib
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Callable
from pathlib import Path

from ..core.config import AIProviderConfig, Config
from ..core.logging import VISIBILITY


@dataclass
class AIRequest:
    prompt: str
    system: str = ""
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    stream: bool = False
    trace_id: str = ""


@dataclass
class AIChunk:
    content: str = ""
    finish_reason: str = ""


@dataclass
class AIResponse:
    content: str = ""
    finish_reason: str = ""
    model: str = ""
    provider: str = ""
    latency_ms: float = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tokens_per_second: float = 0
    cached: bool = False
    fallback_used: bool = False
    error: Optional[str] = None


@dataclass
class ModerationResult:
    flagged: bool = False
    categories: dict = field(default_factory=dict)
    scores: dict = field(default_factory=dict)


class AIAdapter:
    """Unified AI adapter with provider cascade, caching, and observability."""

    def __init__(self, config: Config, providers: dict[str, "ProviderBase"] = None):
        self.config = config
        self._providers = providers or {}
        self._cache_dir = Path(config.data_dir) / "ai_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._callbacks: list[Callable] = []

    def register_provider(self, name: str, provider: "ProviderBase"):
        self._providers[name] = provider

    def on_call(self, cb: Callable):
        """Register callback called after every AI call (for observability)."""
        self._callbacks.append(cb)
        return cb

    def _cache_key(self, request: AIRequest) -> str:
        raw = f"{request.system}|{request.prompt}|{request.model}|{request.max_tokens}|{request.temperature}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def _check_cache(self, key: str) -> Optional[AIResponse]:
        cached_path = self._cache_dir / f"{key}.json"
        if cached_path.exists():
            age = time.time() - cached_path.stat().st_mtime
            if age < self.config.ai.cache_ttl:
                data = json.loads(cached_path.read_text())
                resp = AIResponse(**data)
                resp.cached = True
                return resp
        return None

    def _save_cache(self, key: str, response: AIResponse):
        cached_path = self._cache_dir / f"{key}.json"
        cached_path.write_text(json.dumps({
            "content": response.content,
            "finish_reason": response.finish_reason,
            "model": response.model,
            "provider": response.provider,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
        }))

    async def generate(self, request: AIRequest) -> AIResponse:
        """Generate with cascade: primary → fallback → local."""
        t0 = time.time()

        # Check cache
        cache_key = self._cache_key(request)
        if not request.stream:
            cached = self._check_cache(cache_key)
            if cached:
                VISIBILITY.log("DEBUG", "ai.cache", f"Cache hit for {request.model}", {
                    "cache_key": cache_key,
                    "age_s": time.time() - (self._cache_dir / f"{cache_key}.json").stat().st_mtime,
                })
                return cached

        # Cascade through providers
        cascade = [
            ("primary", self.config.ai.primary),
            ("fallback", self.config.ai.fallback),
            ("local", self.config.ai.local),
        ]

        last_error = None
        for name, provider_cfg in cascade:
            if provider_cfg is None:
                continue
            if name not in self._providers:
                continue

            provider = self._providers[name]
            try:
                request.model = provider_cfg.model or request.model
                response = await provider.generate(request)

                # Add metadata
                response.provider = name
                response.model = provider_cfg.model
                response.latency_ms = (time.time() - t0) * 1000
                if name != "primary":
                    response.fallback_used = True
                    VISIBILITY.log("WARN", "ai.cascade",
                                   f"Used {name} provider (primary failed: {last_error})")

                # Save to cache
                if not request.stream and response.content:
                    self._save_cache(cache_key, response)

                # Callbacks
                for cb in self._callbacks:
                    try:
                        cb(response)
                    except Exception:
                        pass

                return response

            except Exception as e:
                last_error = str(e)
                VISIBILITY.log("WARN", "ai.provider",
                               f"{name} failed: {e}", {"provider": name})
                continue

        # All providers failed
        resp = AIResponse(
            error=f"All providers failed. Last error: {last_error}",
            latency_ms=(time.time() - t0) * 1000,
        )
        for cb in self._callbacks:
            try:
                cb(resp)
            except Exception:
                pass
        return resp

    async def stream(self, request: AIRequest) -> AsyncIterator[AIChunk]:
        """Stream from primary provider."""
        provider_name = "primary"
        provider_cfg = self.config.ai.primary
        if provider_name in self._providers:
            request.model = provider_cfg.model
            async for chunk in self._providers[provider_name].stream(request):
                yield chunk

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings."""
        # Use primary provider that supports embeddings
        for name in ["primary", "fallback"]:
            provider_cfg = getattr(self.config.ai, name, None)
            if provider_cfg and name in self._providers:
                try:
                    return await self._providers[name].embed(texts)
                except Exception:
                    continue
        return [[0.0] * 256 for _ in texts]

    async def moderate(self, content: str) -> ModerationResult:
        """Content moderation."""
        for name in ["primary", "fallback"]:
            provider_cfg = getattr(self.config.ai, name, None)
            if provider_cfg and name in self._providers:
                try:
                    return await self._providers[name].moderate(content)
                except Exception:
                    continue
        return ModerationResult()
