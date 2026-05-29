"""Pixabay connector — stock videos and music."""
from __future__ import annotations
import json
import urllib.request
import urllib.parse
from typing import Any, Dict, List
from .base import SourceConnector


class PixabayConnector(SourceConnector):
    """Fetches free stock videos and music from Pixabay.

    API key: https://pixabay.com/api/docs/
    """

    name = "pixabay"
    BASE = "https://pixabay.com/api/videos/"

    def _do_fetch(self, query: str = "technology nature") -> List[Dict[str, Any]]:
        if not self.api_key:
            self._last_error = "No API key configured for Pixabay"
            return []

        params = urllib.parse.urlencode({
            "key": self.api_key,
            "q": query,
            "per_page": 10,
            "safesearch": "true",
        })
        url = f"{self.BASE}?{params}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ai-video-studio/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())

            items = []
            for hit in data.get("hits", []):
                videos = hit.get("videos", {})
                # Prefer small (640px) for speed
                medium = videos.get("medium", {})
                small = videos.get("small", {})
                video_url = medium.get("url") or small.get("url", "")
                items.append({
                    "source": "pixabay",
                    "type": "video",
                    "title": hit.get("tags", ""),
                    "url": video_url,
                    "page_url": hit.get("pageURL", ""),
                    "duration": hit.get("duration", 0),
                    "width": medium.get("width", 0),
                    "height": medium.get("height", 0),
                    "user": hit.get("user", ""),
                    "downloads": hit.get("downloads", 0),
                })
            return items
        except Exception as e:
            self._last_error = str(e)
            return []
