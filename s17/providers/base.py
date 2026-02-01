"""Base provider class."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Iterator


class Provider(ABC):
    """Abstract base class for AI providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.name = config.get("name", "unknown")
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "")
        self.extra = config.get("extra", {})
    
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], model_id: Optional[str] = None) -> tuple[str, Dict]:
        """
        Send a chat message and get response.
        
        Returns:
            Tuple of (response_text, usage_info)
        """
        pass
    
    @abstractmethod
    def stream_chat(self, messages: List[Dict[str, str]], model_id: Optional[str] = None) -> Iterator[str]:
        """
        Stream a chat response.
        
        Yields:
            Chunks of response text
        """
        pass
    
    @abstractmethod
    def get_models(self) -> List[str]:
        """Get list of available models."""
        pass
    
    @abstractmethod
    def get_model_info(self, model_id: str) -> Dict[str, Any]:
        """Get information about a specific model."""
        pass
    
    def validate_config(self) -> bool:
        """Validate provider configuration."""
        return True
    
    def health_check(self) -> bool:
        """Check if provider is available."""
        try:
            self.get_models()
            return True
        except Exception:
            return False
