"""Data source connectors registry."""
from __future__ import annotations
from typing import Dict

from .base import SourceConnector
from .github import GitHubConnector
from .huggingface import HuggingFaceConnector
from .pixabay import PixabayConnector
from .x_com import XComConnector
from .youtube import YouTubeConnector
from .tiktok import TikTokConnector

from ..config import CONFIG


def get_all_connectors() -> Dict[str, SourceConnector]:
    """Instantiate all connectors based on current config."""
    cfg = CONFIG.sources
    return {
        "github": GitHubConnector(
            api_key=cfg["github"].api_key,
            enabled=cfg["github"].enabled,
        ),
        "huggingface": HuggingFaceConnector(
            api_key=cfg["huggingface"].api_key,
            enabled=cfg["huggingface"].enabled,
        ),
        "pixabay": PixabayConnector(
            api_key=cfg["pixabay"].api_key,
            enabled=cfg["pixabay"].enabled,
        ),
        "x_com": XComConnector(
            api_key=cfg["x_com"].api_key,
            enabled=cfg["x_com"].enabled,
        ),
        "youtube": YouTubeConnector(
            api_key=cfg["youtube"].api_key,
            enabled=cfg["youtube"].enabled,
        ),
        "tiktok": TikTokConnector(
            api_key=cfg["tiktok"].api_key,
            enabled=cfg["tiktok"].enabled,
        ),
    }


def get_status_all() -> Dict:
    """Get status of all connectors."""
    return {name: conn.status() for name, conn in get_all_connectors().items()}
