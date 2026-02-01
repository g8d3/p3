"""Ollama provider implementation."""

import json
import time
import httpx
from typing import Dict, List, Optional, Any, Iterator

from providers.base import Provider


class OllamaProvider(Provider):
    """Ollama local API provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = httpx.Client(timeout=300.0)
        self._models_cache = None
    
    def chat(self, messages: List[Dict[str, str]], model_id: Optional[str] = None) -> tuple[str, Dict]:
        """Send chat message to Ollama."""
        if not model_id:
            model_id = "llama3.2"
        
        url = f"{self.base_url}/api/chat"
        
        data = {
            "model": model_id,
            "messages": messages,
            "stream": False,
        }
        
        start_time = time.time()
        
        response = self.client.post(url, json=data)
        response.raise_for_status()
        
        result = response.json()
        
        content = result["message"]["content"]
        
        return content, {
            "tokens_in": result.get("prompt_eval_count", 0),
            "tokens_out": result.get("eval_count", 0),
            "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0)
        }
    
    def stream_chat(self, messages: List[Dict[str, str]], model_id: Optional[str] = None) -> Iterator[str]:
        """Stream chat response from Ollama."""
        if not model_id:
            model_id = "llama3.2"
        
        url = f"{self.base_url}/api/chat"
        
        data = {
            "model": model_id,
            "messages": messages,
            "stream": True,
        }
        
        with self.client.stream("POST", url, json=data) as response:
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if "message" in chunk:
                            content = chunk["message"].get("content", "")
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        pass
    
    def get_models(self) -> List[str]:
        """Get list of available Ollama models."""
        if self._models_cache:
            return self._models_cache
        
        try:
            url = f"{self.base_url}/api/tags"
            response = self.client.get(url)
            response.raise_for_status()
            
            result = response.json()
            model_ids = [m["name"] for m in result.get("models", [])]
            
            self._models_cache = model_ids
            return model_ids
        except Exception:
            return []
    
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a specific Ollama model."""
        try:
            url = f"{self.base_url}/api/show"
            data = {"name": model_id}
            
            response = self.client.post(url, json=data)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                "id": model_id,
                "provider": "ollama",
                "context_window": result.get("context_size", 4096),
                "max_tokens": 4096,
                "parameters": result.get("parameters", "unknown")
            }
        except Exception:
            return {
                "id": model_id,
                "provider": "ollama",
                "context_window": 4096,
                "max_tokens": 4096
            }
    
    def validate_config(self) -> bool:
        """Validate Ollama configuration."""
        return True
    
    def health_check(self) -> bool:
        """Check if Ollama is available."""
        try:
            url = f"{self.base_url}/api/tags"
            response = self.client.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False
    
    def pull_model(self, model_id: str) -> bool:
        """Pull a model from Ollama registry."""
        try:
            url = f"{self.base_url}/api/pull"
            data = {"name": model_id, "stream": False}
            
            response = self.client.post(url, json=data)
            response.raise_for_status()
            
            return True
        except Exception:
            return False
