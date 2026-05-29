#!/usr/bin/env python3.12
"""AI Provider Agent — Interfaz unificada para modelos de IA.

Cualquier agente del framework puede enviarle una tarea para obtener
respuestas de modelos LLM, sin necesidad de saber qué proveedor
o API key usar.

Tareas que entiende:
  - action: "chat"       → params: {messages, model?, temperature?}
  - action: "chat_with_vision" → params: {messages, model?, image_url}
  - action: "ping"       → params: {msg} (test)
  - action: "list_models" → sin params
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

# ── Config ──────────────────────────────────────────────

CONFIG_PATH = os.environ.get("AI_PROVIDER_CONFIG",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "ai-provider.yaml"))

# Ensure agent template is importable
import sys
AGENT_TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "agent-template")
if AGENT_TEMPLATE_DIR not in sys.path:
    sys.path.insert(0, AGENT_TEMPLATE_DIR)

from agent import Agent

import yaml


def load_config():
    path = Path(CONFIG_PATH)
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


class AIProviderAgent(Agent):
    """Agente que provee acceso a modelos de IA a otros agentes."""

    def __init__(self, name: str = "ai-provider"):
        super().__init__(name)
        self.cfg = load_config()
        self.provider_name = self.cfg.get("default_provider", "opencode-go")
        self.provider = self.cfg.get("providers", {}).get(self.provider_name, {})
        self.api_base = self.provider.get("api_base", "https://opencode.ai/zen/go/v1/")
        self.api_key = os.environ.get(self.provider.get("api_key_env", "OPENCODE_GO_API_KEY"), "")
        self.default_model = self.provider.get("default_model", "deepseek-v4-flash")
        self.vision_model = self.provider.get("vision_model", "mimo-v2.5")
        self.timeout_s = self.provider.get("timeout_s", 120)

        if not self.api_key:
            self.emit_log("warn", f"No {self.provider.get('api_key_env','OPENCODE_GO_API_KEY')} env var set")
        else:
            self.emit_log("info", f"AI Provider ready: {self.provider_name} ({self.default_model})")

    def execute(self, action: str, params: dict) -> dict:
        if action == "chat":
            return self._chat(params)
        elif action == "chat_with_vision":
            return self._chat_with_vision(params)
        elif action == "ping":
            return {"echo": True, "msg": params.get("msg", ""), "provider": self.provider_name}
        elif action == "list_models":
            return self._list_models()
        else:
            raise ValueError(f"Unknown action: {action}")

    def _chat(self, params: dict) -> dict:
        messages = params.get("messages", [])
        model = params.get("model", self.default_model)
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 2000)

        if not messages:
            return {"error": "No messages provided"}

        self.emit_log("info", f"Calling {model} ({len(messages)} messages)")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        start = time.time()
        try:
            result = self._call_api(payload)
            elapsed = int((time.time() - start) * 1000)
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            return {
                "content": content,
                "model": model,
                "duration_ms": elapsed,
                "tokens": {
                    "prompt": result.get("usage", {}).get("prompt_tokens", 0),
                    "completion": result.get("usage", {}).get("completion_tokens", 0),
                    "total": result.get("usage", {}).get("total_tokens", 0),
                },
            }
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            self.emit_error(f"Chat failed: {e}")
            return {"error": str(e), "duration_ms": elapsed}

    def _chat_with_vision(self, params: dict) -> dict:
        messages = params.get("messages", [])
        model = params.get("model", self.vision_model)
        image_url = params.get("image_url", "")

        # Add image to last user message
        if image_url and messages:
            last = messages[-1]
            if last.get("role") == "user":
                content = last.get("content", "")
                if isinstance(content, str):
                    messages[-1] = {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": content},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }

        return self._chat({"messages": messages, "model": model, **params})

    def _list_models(self) -> dict:
        models = self.provider.get("models", {})
        return {
            "default_model": self.default_model,
            "vision_model": self.vision_model,
            "available": list(models.keys()),
            "details": models,
        }

    def _call_api(self, payload: dict) -> dict:
        """Hace la llamada HTTP a la API compatible con OpenAI."""
        data = json.dumps(payload).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "framework-ai-provider/0.1",
        }
        req = urllib.request.Request(
            f"{self.api_base.rstrip('/')}/chat/completions",
            data=data,
            headers=headers,
            method="POST",
        )
        resp = urllib.request.urlopen(req, timeout=self.timeout_s)
        return json.loads(resp.read())


if __name__ == "__main__":
    agent = AIProviderAgent(name=os.environ.get("AGENT_NAME", "ai-provider"))
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()
        agent.emit_log("info", "AI Provider stopped")
