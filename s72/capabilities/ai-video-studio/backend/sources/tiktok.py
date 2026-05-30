"""TikTok connector — requires business API."""
from __future__ import annotations
from typing import Any, Dict, List
from .base import SourceConnector


class TikTokConnector(SourceConnector):
    """TikTok trending videos and sounds.

    NOTE: Requires TikTok Business API or Scraper.
    Free tier is very limited. For production, use:
    - TikTok Business API (requires approved app)
    - Or scraper approaches (brittle)
    """

    name = "tiktok"

    def _do_fetch(self) -> List[Dict[str, Any]]:
        return [{
            "source": "tiktok",
            "title": "Requiere TikTok Business API",
            "description": (
                "TikTok no tiene API pública gratuita. "
                "Para integrar: solicitar acceso a TikTok Business API "
                "(revisión de 2-4 semanas) o usar scraper."
            ),
            "url": "https://developers.tiktok.com",
            "type": "placeholder",
        }]
