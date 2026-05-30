"""DevTools Panel — integrates all dev tools into a cohesive panel."""

from __future__ import annotations
from ..core import Config, VISIBILITY
from .inspector import StateInspector


class DevToolsPanel:
    """Aggregates all DevTools information."""

    def __init__(self, inspector: StateInspector, config: Config):
        self.inspector = inspector
        self.config = config

    def get_dashboard(self) -> dict:
        """Get all data for the DevTools dashboard."""
        snap = self.inspector.snapshot()
        return {
            "app": snap.app,
            "config": snap.config,
            "visibility": {
                "status": snap.visibility,
                "actions": VISIBILITY.get_actions(20),
                "errors": [
                    {"ts": e.ts, "level": e.level, "source": e.source, "message": e.message}
                    for e in VISIBILITY.get_errors(20)
                ],
            },
            "system": snap.system,
        }

    def get_ai_insights(self) -> dict:
        """Get AI-specific observability data."""
        return {
            "total_calls": 0,  # Populated by AI adapter callbacks
            "calls_by_provider": {},
            "average_latency_ms": 0,
            "total_tokens": 0,
            "cache_hits": 0,
            "errors": 0,
        }
