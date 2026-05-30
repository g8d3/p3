"""Ollama provider — local LLM inference."""

from __future__ import annotations
import json
import time
from urllib.request import Request, urlopen

from ..adapter import AIRequest, AIResponse
from .base import ProviderBase


class OllamaProvider(ProviderBase):
    """Provider for local Ollama inference."""

    name: str = "ollama"

    def __init__(self, api_key: str = "", endpoint: str = "", **kwargs):
        super().__init__(api_key, endpoint)
        if not self.endpoint:
            self.endpoint = "http://localhost:11434"

    async def generate(self, request: AIRequest) -> AIResponse:
        url = f"{self.endpoint}/api/chat"
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        payload = json.dumps({
            "model": request.model or "llama3.2:1b",
            "messages": messages,
            "options": {
                "num_predict": request.max_tokens,
                "temperature": request.temperature,
            },
        }).encode()

        req = Request(url, data=payload, headers={"Content-Type": "application/json"})
        t0 = time.time()
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            r = await loop.run_in_executor(None, lambda: urlopen(req, timeout=60))
            resp = json.loads(r.read())
            t1 = time.time()

            content = resp["message"]["content"]
            usage = resp.get("eval_count", 0)
            elapsed = t1 - t0

            return AIResponse(
                content=content.strip(),
                finish_reason="stop",
                model=request.model,
                provider=self.name,
                latency_ms=elapsed * 1000,
                prompt_tokens=resp.get("prompt_eval_count", 0),
                completion_tokens=usage,
                total_tokens=resp.get("prompt_eval_count", 0) + usage,
                tokens_per_second=round(usage / elapsed, 1) if elapsed > 0 else 0,
            )
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {e}")
