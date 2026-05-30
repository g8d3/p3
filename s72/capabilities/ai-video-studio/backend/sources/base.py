"""Base class for all data source connectors."""
from __future__ import annotations
import time
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class SourceConnector:
    """Abstract base for a data source.

    Each connector:
    - Fetches **trending / recent** content from its source.
    - Caches results to a JSON file in *data_dir*.
    - Reports its status (connected, last fetch, rate limit remaining).
    """

    name: str = "base"
    cache_ttl_s: int = 300

    def __init__(self, api_key: str = "", data_dir: str = "data", enabled: bool = True):
        self.api_key = api_key
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = enabled
        self._last_fetch: float = 0.0
        self._last_error: str = ""
        self._rate_remaining: int = 60

    # ── Public API ───────────────────────────────────────────

    def fetch(self) -> List[Dict[str, Any]]:
        """Get trending items. Uses cache if fresh, else fetches."""
        cached = self._load_cache()
        if cached and time.time() - cached.get("_ts", 0) < self.cache_ttl_s:
            return cached.get("items", [])
        try:
            items = self._do_fetch()
            self._save_cache(items)
            self._last_error = ""
            return items
        except Exception as e:
            self._last_error = str(e)
            return cached.get("items", []) if cached else []

    def status(self) -> Dict[str, Any]:
        """Connection status dict."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "connected": self._last_error == "" and self.enabled,
            "last_fetch": self._last_fetch,
            "last_error": self._last_error,
            "rate_remaining": self._rate_remaining,
        }

    # ── Subclasses implement this ────────────────────────────

    def _do_fetch(self) -> List[Dict[str, Any]]:
        """Actually fetch from the API. Override in subclass."""
        raise NotImplementedError

    # ── Internal ─────────────────────────────────────────────

    def _save_cache(self, items: List[Dict]) -> None:
        path = self.data_dir / f"{self.name}_cache.json"
        data = {"_ts": time.time(), "items": items}
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        self._last_fetch = time.time()

    def _load_cache(self) -> Optional[Dict]:
        path = self.data_dir / f"{self.name}_cache.json"
        if path.exists():
            return json.loads(path.read_text())
        return None
