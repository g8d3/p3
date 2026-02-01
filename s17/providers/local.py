"""Local/custom provider implementation."""

import json
import time
import subprocess
import os
from typing import Dict, List, Optional, Any, Iterator

from providers.base import Provider


class LocalProvider(Provider):
    """Local model provider (via vLLM, llama.cpp, etc.)."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._models_cache = None
    
    def chat(self, messages: List[Dict[str, str]], model_id: Optional[str] = None) -> tuple[str, Dict]:
        """Send chat message to local model."""
        if not model_id:
            model_id = "local-model"
        
        url = f"{self.base_url}/v1/chat/completions"
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        data = {
            "model": model_id,
            "messages": messages,
            "max_tokens": 4096,
        }
        
        import httpx
        with httpx.Client(timeout=300.0) as client:
            start_time = time.time()
            
            response = client.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            
            return content, {
                "tokens_in": usage.get("prompt_tokens", 0),
                "tokens_out": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
    
    def stream_chat(self, messages: List[Dict[str, str]], model_id: Optional[str] = None) -> Iterator[str]:
        """Stream chat response from local model."""
        if not model_id:
            model_id = "local-model"
        
        url = f"{self.base_url}/v1/chat/completions"
        
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        data = {
            "model": model_id,
            "messages": messages,
            "stream": True,
            "max_tokens": 4096,
        }
        
        import httpx
        with httpx.Client(timeout=300.0) as client:
            with client.stream("POST", url, headers=headers, json=data) as response:
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
        """Get list of available local models."""
        if self._models_cache:
            return self._models_cache
        
        try:
            url = f"{self.base_url}/v1/models"
            import httpx
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    result = response.json()
                    model_ids = [m["id"] for m in result.get("data", [])]
                    self._models_cache = model_ids
                    return model_ids
        except Exception:
            pass
        
        return ["local-model"]
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a specific local model."""
        return {
            "id": model_id,
            "provider": "local",
            "context_window": 32768,
            "max_tokens": 4096
        }
    
    def validate_config(self) -> bool:
        """Validate local provider configuration."""
        return True
    
    def health_check(self) -> bool:
        """Check if local model server is available."""
        try:
            import httpx
            url = f"{self.base_url}/v1/models"
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                return response.status_code == 200
        except Exception:
            return False
