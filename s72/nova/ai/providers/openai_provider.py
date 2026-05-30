"""OpenAI-compatible provider (works with any OpenAI-like API)."""

from __future__ import annotations
import json
import time
from urllib.request import Request, urlopen

from ..adapter import AIRequest, AIResponse, AIChunk
from .base import ProviderBase


class OpenAIProvider(ProviderBase):
    """Provider for OpenAI-compatible APIs."""

    name: str = "openai"

    def __init__(self, api_key: str = "", endpoint: str = "", **kwargs):
        super().__init__(api_key, endpoint)
        if not self.endpoint:
            self.endpoint = "https://api.openai.com/v1/chat/completions"

    async def generate(self, request: AIRequest) -> AIResponse:
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        payload = json.dumps({
            "model": request.model or "gpt-4o",
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }).encode()

        req = Request(self.endpoint, data=payload, headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })

        t0 = time.time()
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            r = await loop.run_in_executor(None, lambda: urlopen(req, timeout=120))
            resp = json.loads(r.read())
            t1 = time.time()

            choice = resp["choices"][0]
            usage = resp.get("usage", {})
            content = choice["message"]["content"]
            elapsed = t1 - t0
            comp_tok = usage.get("completion_tokens", 0)

            return AIResponse(
                content=content.strip(),
                finish_reason=choice.get("finish_reason", "stop"),
                model=request.model,
                provider=self.name,
                latency_ms=elapsed * 1000,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=comp_tok,
                total_tokens=usage.get("total_tokens", 0),
                tokens_per_second=round(comp_tok / elapsed, 1) if elapsed > 0 else 0,
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        payload = json.dumps({
            "model": "text-embedding-3-small",
            "input": texts,
        }).encode()
        req = Request("https://api.openai.com/v1/embeddings", data=payload, headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        loop = asyncio.get_running_loop()
        r = await loop.run_in_executor(None, lambda: urlopen(req, timeout=30))
        resp = json.loads(r.read())
        return [item["embedding"] for item in resp["data"]]
