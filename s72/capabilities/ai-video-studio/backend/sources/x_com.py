"""X.com (Twitter) connector — requires paid API."""
from __future__ import annotations
from typing import Any, Dict, List
from .base import SourceConnector


class XComConnector(SourceConnector):
    """X/Twitter trending topics and posts.

    NOTE: Requires a paid X API (Basic or Pro) — $100-$5000/mo.
    Without it, returns a placeholder.
    """

    name = "x_com"

    def _do_fetch(self) -> List[Dict[str, Any]]:
        if not self.api_key:
            return [{
                "source": "x_com",
                "title": "API key required",
                "description": (
                    "X API requires a paid subscription (Basic $100/mo or Pro $5000/mo). "
                    "Configure X_API_KEY environment variable."
                ),
                "url": "https://developer.x.com",
                "type": "placeholder",
            }]
        # TODO: implement when API key is available
        return [{
            "source": "x_com",
            "title": "X API - Not implemented",
            "description": "Connector ready - implement when API key is configured.",
            "url": "",
            "type": "placeholder",
        }]
