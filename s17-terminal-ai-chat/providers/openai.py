"""OpenAI provider implementation."""

import json
import time
import httpx
from typing import Dict, List, Optional, Any, Iterator

from providers.base import Provider


class OpenAIProvider(Provider):
    """OpenAI API provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = httpx.Client(timeout=60.0)
        self._models_cache = None
    
    def chat(self, messages: List[Dict[str, str]], model_id: Optional[str] = None) -> tuple[str, Dict]:
        """Send chat message to OpenAI."""
        if not model_id:
            model_id = "gpt-4o"
        
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        if self.extra.get("organization"):
            headers["OpenAI-Organization"] = self.extra["organization"]
        
        data = {
            "model": model_id,
            "messages": messages,
            "max_tokens": 4096,
        }
        
        start_time = time.time()
        
        response = self.client.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        
        usage = result.get("usage", {})
        content = result["choices"][0]["message"]["content"]
        
        return content, {
            "tokens_in": usage.get("prompt_tokens", 0),
            "tokens_out": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    
    def stream_chat(self, messages: List[Dict[str, str]], model_id: Optional[str] = None) -> Iterator[str]:
        """Stream chat response from OpenAI."""
        if not model_id:
            model_id = "gpt-4o"
        
        url = f"{self.base_url}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": model_id,
            "messages": messages,
            "stream": True,
            "max_tokens": 4096,
        }
        
        with self.client.stream("POST", url, headers=headers, json=data) as response:
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            if "choices" in chunk:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            pass
    
    def get_models(self) -> List[str]:
        """Get list of available OpenAI models."""
        if self._models_cache:
            return self._models_cache
        
        url = f"{self.base_url}/models"
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        response = self.client.get(url, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        model_ids = [m["id"] for m in result.get("data", [])]
        
        self._models_cache = model_ids
        return model_ids
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a specific OpenAI model."""
        models = self.get_models()
        
        if model_id in models:
            return {
                "id": model_id,
                "provider": "openai",
                "context_window": 128000,
                "max_tokens": 16384
            }
        
        raise ValueError(f"Model not found: {model_id}")
    
    def validate_config(self) -> bool:
        """Validate OpenAI configuration."""
        if not self.api_key:
            return False
        
        try:
            self.get_models()
            return True
        except Exception:
            return False
    
    def health_check(self) -> bool:
        """Check if OpenAI API is available."""
        try:
            url = f"{self.base_url}/models"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            response = self.client.get(url, headers=headers, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
