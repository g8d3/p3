"""Gemini provider — uses Google's Gemini API."""

from __future__ import annotations
import json
import time
from urllib.request import Request, urlopen

from ..adapter import AIRequest, AIResponse
from .base import ProviderBase


class GeminiProvider(ProviderBase):
    """Provider for Google Gemini API."""

    name: str = "gemini"

    def __init__(self, api_key: str = "", endpoint: str = "", **kwargs):
        super().__init__(api_key, endpoint)
        if not self.endpoint:
            self.endpoint = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(self, request: AIRequest) -> AIResponse:
        model = request.model or "gemini-2.5-pro"
        url = f"{self.endpoint}/models/{model}:generateContent?key={self.api_key}"

        contents = []
        if request.system:
            contents.append({"role": "user", "parts": [{"text": request.system + "\n\n" + request.prompt}]})
        else:
            contents.append({"role": "user", "parts": [{"text": request.prompt}]})

        payload = json.dumps({
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": request.max_tokens,
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

            candidate = resp["candidates"][0]
            content = candidate["content"]["parts"][0]["text"]
            usage = resp.get("usageMetadata", {})

            comp_tok = usage.get("candidatesTokenCount", 0)
            elapsed = t1 - t0

            return AIResponse(
                content=content.strip(),
                finish_reason=candidate.get("finishReason", "STOP"),
                model=model,
                provider=self.name,
                latency_ms=elapsed * 1000,
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=comp_tok,
                total_tokens=comp_tok + usage.get("promptTokenCount", 0),
                tokens_per_second=round(comp_tok / elapsed, 1) if elapsed > 0 else 0,
            )
        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}")
