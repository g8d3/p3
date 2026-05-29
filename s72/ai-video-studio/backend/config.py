"""Configuration for AI Video Studio."""
import os
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class SourceConfig:
    api_key: str = ""
    enabled: bool = True
    rate_limit_rpm: int = 60  # requests per minute
    cache_ttl_s: int = 300    # 5 min cache


@dataclass
class AppConfig:
    # Paths
    assets_dir: str = os.path.join(os.path.dirname(__file__), "..", "assets")
    logs_dir: str = os.path.join(os.path.dirname(__file__), "..", "logs")
    output_dir: str = os.path.join(os.path.dirname(__file__), "..", "output")
    data_dir: str = os.path.join(os.path.dirname(__file__), "..", "data")

    # Sources
    sources: Dict[str, SourceConfig] = field(default_factory=lambda: {
        "github": SourceConfig(enabled=True, rate_limit_rpm=60),
        "huggingface": SourceConfig(
            api_key=os.getenv("HF_API_KEY", ""),
            enabled=True, rate_limit_rpm=30,
        ),
        "pixabay": SourceConfig(
            api_key=os.getenv("PIXABAY_API_KEY", ""),
            enabled=True, rate_limit_rpm=30,
        ),
        "x_com": SourceConfig(
            api_key=os.getenv("X_API_KEY", ""),
            enabled=False, rate_limit_rpm=15,
        ),
        "youtube": SourceConfig(
            api_key=os.getenv("YOUTUBE_API_KEY", ""),
            enabled=False, rate_limit_rpm=30,
        ),
        "tiktok": SourceConfig(
            api_key=os.getenv("TIKTOK_API_KEY", ""),
            enabled=False, rate_limit_rpm=10,
        ),
    })

    # TTS
    default_voice: str = "es-MX-DaliaNeural"

    # Templates
    subtitle_font_size: int = 96
    subtitle_stroke_width: float = 3.0
    max_words_per_block: int = 5
    bg_music_volume: float = 0.12

    # Server
    host: str = "0.0.0.0"
    port: int = 8777


CONFIG = AppConfig()
os.makedirs(CONFIG.assets_dir, exist_ok=True)
os.makedirs(CONFIG.logs_dir, exist_ok=True)
os.makedirs(CONFIG.output_dir, exist_ok=True)
os.makedirs(CONFIG.data_dir, exist_ok=True)
