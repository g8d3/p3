"""YouTube connector — search and trending."""
from __future__ import annotations
from typing import Any, Dict, List
from .base import SourceConnector


class YouTubeConnector(SourceConnector):
    """YouTube search and trending.

    Requires YouTube Data API v3 key.
    https://console.cloud.google.com/apis/library/youtube.googleapis.com
    """

    name = "youtube"
    BASE = "https://www.googleapis.com/youtube/v3"

    def _do_fetch(self) -> List[Dict[str, Any]]:
        if not self.api_key:
            return [{
                "source": "youtube",
                "title": "API key required",
                "description": (
                    "YouTube Data API v3 key required. "
                    "Configure YOUTUBE_API_KEY environment variable."
                ),
                "url": "https://console.cloud.google.com",
                "type": "placeholder",
            }]
        # TODO: implement full YouTube search
        import urllib.request, json, urllib.parse
        params = urllib.parse.urlencode({
            "part": "snippet",
            "q": "inteligencia artificial 2026",
            "maxResults": 5,
            "order": "date",
            "type": "video",
            "key": self.api_key,
        })
        url = f"{self.BASE}/search?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ai-video-studio/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
            items = []
            for v in data.get("items", []):
                sid = v.get("id", {}).get("videoId", "")
                items.append({
                    "source": "youtube",
                    "type": "video",
                    "title": v.get("snippet", {}).get("title", ""),
                    "description": v.get("snippet", {}).get("description", "")[:200],
                    "url": f"https://youtube.com/watch?v={sid}",
                    "channel": v.get("snippet", {}).get("channelTitle", ""),
                    "published": v.get("snippet", {}).get("publishedAt", ""),
                })
            return items
        except Exception as e:
            self._last_error = str(e)
            return []
