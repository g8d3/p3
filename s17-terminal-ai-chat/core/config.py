"""Configuration management."""

import os
import json
from dataclasses import dataclass, field
from typing import Dict, Optional
from pathlib import Path


@dataclass
class AppConfig:
    """Application configuration."""
    
    default_provider: str = "openai"
    default_model: str = ""
    default_agent: Optional[str] = None
    theme: str = "dark"
    auto_suggest: bool = True
    show_timestamps: bool = True
    max_history_messages: int = 100
    log_dir: str = "~/.config/term-ai/logs"
    database_path: str = "~/.config/term-ai/term-ai.db"
    
    def __post_init__(self):
        self.log_dir = os.path.expanduser(self.log_dir)
        self.database_path = os.path.expanduser(self.database_path)
    
    @classmethod
    def load(cls, path: Optional[str] = None) -> "AppConfig":
        """Load configuration from file."""
        if path is None:
            config_dir = os.path.expanduser("~/.config/term-ai")
            path = os.path.join(config_dir, "config.json")
        
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                return cls(**data)
            except (json.JSONDecodeError, TypeError, KeyError):
                pass
        return cls()
    
    def save(self, path: Optional[str] = None):
        """Save configuration to file."""
        if path is None:
            config_dir = os.path.expanduser("~/.config/term-ai")
            os.makedirs(config_dir, exist_ok=True)
            path = os.path.join(config_dir, "config.json")
        
        config_dict = {
            "default_provider": self.default_provider,
            "default_model": self.default_model,
            "default_agent": self.default_agent,
            "theme": self.theme,
            "auto_suggest": self.auto_suggest,
            "show_timestamps": self.show_timestamps,
            "max_history_messages": self.max_history_messages,
            "log_dir": self.log_dir,
            "database_path": self.database_path
        }
        
        with open(path, 'w') as f:
            json.dump(config_dict, f, indent=2)


@dataclass
class ProviderConfig:
    """Provider configuration."""
    
    name: str
    provider_type: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    enabled: bool = True
    extra: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ProviderConfig":
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "provider_type": self.provider_type,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "enabled": self.enabled,
            "extra": self.extra
        }


@dataclass
class ModelConfig:
    """Model configuration."""
    
    name: str
    provider_name: str
    model_id: str
    context_window: int = 128000
    max_tokens: int = 4096
    cost_per_input: float = 0.0
    cost_per_output: float = 0.0
    is_default: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ModelConfig":
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "provider_name": self.provider_name,
            "model_id": self.model_id,
            "context_window": self.context_window,
            "max_tokens": self.max_tokens,
            "cost_per_input": self.cost_per_input,
            "cost_per_output": self.cost_per_output,
            "is_default": self.is_default
        }
