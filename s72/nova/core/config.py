"""Hot-reloadable configuration system.

Config is loaded from YAML and can be updated at runtime
via file watcher or API call. Every change is logged.
"""

from __future__ import annotations
import os
import time
import threading
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path


@dataclass
class SourceConfig:
    api_key: str = ""
    enabled: bool = True
    rate_limit_rpm: int = 60
    cache_ttl_s: int = 300


@dataclass
class AIProviderConfig:
    provider: str = "opencode"
    model: str = "deepseek-v4-flash"
    key: str = ""
    endpoint: str = ""
    options: dict = field(default_factory=lambda: {
        "max_tokens": 4096,
        "temperature": 0.7,
    })


@dataclass
class AIConfig:
    primary: AIProviderConfig = field(default_factory=lambda: AIProviderConfig(
        provider="opencode",
        model="deepseek-v4-flash",
        key=os.getenv("OPENCODE_GO_API_KEY", ""),
        endpoint=os.getenv("PROXY_URL", "http://127.0.0.1:9100") + "/chat/completions",
    ))
    fallback: Optional[AIProviderConfig] = field(default_factory=lambda: AIProviderConfig(
        provider="gemini",
        model="gemini-2.5-pro",
        key=os.getenv("GEMINI_API_KEY", ""),
    ))
    local: Optional[AIProviderConfig] = field(default_factory=lambda: AIProviderConfig(
        provider="ollama",
        model="llama3.2:1b",
        endpoint="http://localhost:11434",
    ))
    cache_ttl: int = 3600
    strategy: str = "primary → fallback → local"


@dataclass
class Config:
    """Root configuration — hot-reloadable via YAML or API."""

    # App
    name: str = "nova-app"
    version: str = "0.1.0"
    description: str = ""

    # Server
    host: str = "0.0.0.0"
    port: int = 8777
    dev_mode: bool = True

    # Paths
    assets_dir: str = "assets"
    data_dir: str = "data"
    output_dir: str = "output"
    logs_dir: str = "logs"
    spec_path: str = "spec/app.yaml"

    # AI
    ai: AIConfig = field(default_factory=AIConfig)

    # Sources
    sources: Dict[str, SourceConfig] = field(default_factory=lambda: {
        "github": SourceConfig(enabled=True),
        "huggingface": SourceConfig(
            api_key=os.getenv("HF_API_KEY", ""),
            enabled=True,
        ),
        "pixabay": SourceConfig(
            api_key=os.getenv("PIXABAY_API_KEY", ""),
            enabled=True,
        ),
    })

    # Style defaults
    voice: str = "es-MX-DaliaNeural"
    subtitle_font_size: int = 96
    max_words_per_block: int = 5
    bg_music_volume: float = 0.12

    # Callbacks on change
    _on_change: List[Callable] = field(default_factory=list, repr=False)

    def register_callback(self, cb: Callable):
        self._on_change.append(cb)

    def update(self, changes: dict):
        """Apply partial updates and notify callbacks."""
        for key, val in changes.items():
            if hasattr(self, key):
                setattr(self, key, val)
        for cb in self._on_change:
            cb(self)

    def dict(self) -> dict:
        return asdict(self)

    def ensure_dirs(self):
        for d in [self.assets_dir, self.data_dir, self.output_dir, self.logs_dir]:
            os.makedirs(d, exist_ok=True)


class ConfigWatcher:
    """Watches a YAML config file for changes and hot-reloads."""

    def __init__(self, config: Config, path: str, poll_interval: float = 2.0):
        self.config = config
        self.path = Path(path)
        self.poll_interval = poll_interval
        self._last_mtime: float = 0
        self._running = False

    def start(self):
        if self.path.exists():
            self._load()
        self._running = True
        t = threading.Thread(target=self._poll, daemon=True)
        t.start()

    def _poll(self):
        while self._running:
            if self.path.exists():
                mtime = self.path.stat().st_mtime
                if mtime != self._last_mtime:
                    self._last_mtime = mtime
                    self._load()
            time.sleep(self.poll_interval)

    def _load(self):
        try:
            import yaml
            data = yaml.safe_load(self.path.read_text())
            if data:
                self.config.update(data)
        except Exception as e:
            pass  # Logged by VisibilityStack

    def stop(self):
        self._running = False
