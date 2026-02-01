"""Anthropic provider implementation."""

import json
import time
import httpx
from typing import Dict, List, Optional, Any, Iterator

from providers.base import Provider


class AnthropicProvider(Provider):
    """Anthropic API provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = httpx.Client(timeout=120.0)
        self._models_cache = None
    
    def chat(self, messages: List[Dict[str, str]], model_id: Optional[str] = None) -> tuple[str, Dict]:
        """Send chat message to Anthropic."""
        if not model_id:
            model_id = "claude-3-5-sonnet-20241022"
        
        url = f"{self.base_url}/v1/messages"
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        
        if self.extra.get("organization"):
            headers["organization"] = self.extra["organization"]
        
        system_message = None
        formatted_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                formatted_messages.append(msg)
        
        data = {
            "model": model_id,
            "max_tokens": 8192,
            "messages": formatted_messages,
        }
        
        if system_message:
            data["system"] = system_message
        
        start_time = time.time()
        
        response = self.client.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        
        content = result["content"][0]["text"]
        
        usage = result.get("usage", {})
        
        return content, {
            "tokens_in": usage.get("input_tokens", 0),
            "tokens_out": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        }
    
    def stream_chat(self, messages: List[Dict[str, str]], model_id: Optional[str] = None) -> Iterator[str]:
        """Stream chat response from Anthropic."""
        if not model_id:
            model_id = "claude-3-5-sonnet-20241022"
        
        url = f"{self.base_url}/v1/messages"
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        
        system_message = None
        formatted_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                formatted_messages.append(msg)
        
        data = {
            "model": model_id,
            "max_tokens": 8192,
            "messages": formatted_messages,
            "stream": True,
        }
        
        if system_message:
            data["system"] = system_message
        
        with self.client.stream("POST", url, headers=headers, json=data) as response:
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line == "event: ping":
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            chunk = json.loads(data_str)
                            if chunk.get("type") == "content_block_delta":
                                delta = chunk.get("delta", {})
                                content = delta.get("text", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            pass
    
    def get_models(self) -> List[str]:
        """Get list of available Anthropic models."""
        if self._models_cache:
            return self._models_cache
        
        model_ids = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]
        
        self._models_cache = model_ids
        return model_ids
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a specific Anthropic model."""
        models = {
            "claude-3-5-sonnet-20241022": {"context_window": 200000, "max_tokens": 8192},
            "claude-3-5-sonnet-20240620": {"context_window": 200000, "max_tokens": 8192},
            "claude-3-opus-20240229": {"context_window": 200000, "max_tokens": 4096},
            "claude-3-haiku-20240307": {"context_window": 200000, "max_tokens": 4096},
            "claude-2.1": {"context_window": 200000, "max_tokens": 4096},
            "claude-2.0": {"context_window": 100000, "max_tokens": 4096},
            "claude-instant-1.2": {"context_window": 100000, "max_tokens": 4096}
        }
        
        if model_id in models:
            return {
                "id": model_id,
                "provider": "anthropic",
                **models[model_id]
            }
        
        raise ValueError(f"Model not found: {model_id}")
    
    def validate_config(self) -> bool:
        """Validate Anthropic configuration."""
        if not self.api_key:
            return False
        return True
    
    def health_check(self) -> bool:
        """Check if Anthropic API is available."""
        try:
            url = f"{self.base_url}/v1/messages"
            headers = {
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01",
            }
            
            response = self.client.head(url, headers=headers, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
