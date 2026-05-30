"""Base class for all AI providers."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncIterator

from ..adapter import AIRequest, AIResponse, AIChunk, ModerationResult


class ProviderBase(ABC):
    """Abstract base for AI providers."""

    name: str = "base"
    supports_streaming: bool = False
    supports_embeddings: bool = False
    supports_moderation: bool = False

    def __init__(self, api_key: str = "", endpoint: str = "", **kwargs):
        self.api_key = api_key
        self.endpoint = endpoint

    @abstractmethod
    async def generate(self, request: AIRequest) -> AIResponse:
        """Non-streaming generation."""
        ...

    async def stream(self, request: AIRequest) -> AsyncIterator[AIChunk]:
        """Streaming generation (optional)."""
        raise NotImplementedError(f"{self.name} does not support streaming")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embedding (optional)."""
        raise NotImplementedError(f"{self.name} does not support embeddings")

    async def moderate(self, content: str) -> ModerationResult:
        """Content moderation (optional)."""
        raise NotImplementedError(f"{self.name} does not support moderation")
