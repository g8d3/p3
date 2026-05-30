"""OpenCode provider — uses the opencode.ai API (deepseek-v4-flash)."""

from __future__ import annotations
import json
import time
from urllib.request import Request, urlopen

from ..adapter import AIRequest, AIResponse, AIChunk
from .base import ProviderBase


class OpenCodeProvider(ProviderBase):
    """Provider for opencode.ai API (deepseek-v4-flash)."""

    name: str = "opencode"

    def __init__(self, api_key: str = "", endpoint: str = "", **kwargs):
        super().__init__(api_key, endpoint)
        if not self.endpoint:
            self.endpoint = "https://opencode.ai/zen/go/v1/chat/completions"

    async def generate(self, request: AIRequest) -> AIResponse:
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        payload = json.dumps({
            "model": request.model or "deepseek-v4-flash",
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
            msg = choice.get("message", {})

            content = msg.get("content", "")
            reasoning = msg.get("reasoning_content", "")
            if not content.strip() and reasoning:
                content = reasoning

            completion_tokens = usage.get("completion_tokens", 0)
            elapsed = t1 - t0

            return AIResponse(
                content=content.strip(),
                finish_reason=choice.get("finish_reason", "stop"),
                model=request.model,
                provider=self.name,
                latency_ms=elapsed * 1000,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=completion_tokens,
                total_tokens=usage.get("total_tokens", 0),
                tokens_per_second=round(completion_tokens / elapsed, 1) if elapsed > 0 else 0,
            )
        except Exception as e:
            raise RuntimeError(f"OpenCode API error: {e}")
