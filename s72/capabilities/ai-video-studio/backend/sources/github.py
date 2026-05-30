"""GitHub trending repositories connector."""
from __future__ import annotations
from typing import Any, Dict, List
from .base import SourceConnector


class GitHubConnector(SourceConnector):
    """Fetches trending AI/ML repositories from GitHub.

    Uses the public GitHub Search API (no key needed for read-only,
    but higher rate limit with a token).
    """

    name = "github"

    def _do_fetch(self) -> List[Dict[str, Any]]:
        import urllib.request, json

        # Search for trending AI repos this week
        url = (
            "https://api.github.com/search/repositories"
            "?q=artificial-intelligence+created:>2026-05-01"
            "&sort=stars&order=desc&per_page=10"
        )
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ai-video-studio/1.0",
        })
        if self.api_key:
            req.add_header("Authorization", f"token {self.api_key}")

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            self._rate_remaining = int(resp.headers.get("X-RateLimit-Remaining", 60))

        items = []
        for repo in data.get("items", []):
            items.append({
                "source": "github",
                "title": repo["full_name"],
                "description": repo.get("description", "") or "",
                "url": repo["html_url"],
                "stars": repo["stargazers_count"],
                "language": repo.get("language") or "",
                "topics": repo.get("topics", []),
                "created": repo.get("created_at", ""),
            })
        return items
