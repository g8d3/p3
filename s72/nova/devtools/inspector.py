"""State Inspector — introspects runtime state for DevTools."""

from __future__ import annotations
import sys
import time
from typing import Any, Optional
from dataclasses import dataclass, field

from ..core import Runtime, Config, VISIBILITY
from ..ipc import IPCBus


@dataclass
class StateSnapshot:
    """Snapshot of all system state at a point in time."""
    timestamp: float = 0.0
    app: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)
    visibility: dict = field(default_factory=dict)
    system: dict = field(default_factory=dict)
    routes: list = field(default_factory=list)
    tasks: list = field(default_factory=list)


class StateInspector:
    """Introspects all layers for DevTools display."""

    def __init__(self, runtime: Runtime, config: Config, ipc_bus: Optional[IPCBus] = None):
        self.runtime = runtime
        self.config = config
        self.ipc_bus = ipc_bus
        self._snapshots: list[StateSnapshot] = []
        self._max_snapshots = 100

    def snapshot(self) -> StateSnapshot:
        """Take a state snapshot."""
        snap = StateSnapshot(timestamp=time.time())
        snap.app = {
            "name": self.config.name,
            "version": self.config.version,
            "uptime_s": self.runtime.uptime,
            "is_running": self.runtime.is_running,
        }
        snap.config = self.config.dict()
        snap.visibility = VISIBILITY.get_status()
        snap.system = {
            "python": sys.version,
            "platform": sys.platform,
        }
        if self.ipc_bus:
            snap.tasks = self.ipc_bus.status()

        self._snapshots.append(snap)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]
        return snap

    def get_history(self, n: int = 10) -> list[StateSnapshot]:
        return self._snapshots[-n:]

    def get_summary(self) -> dict:
        snap = self.snapshot()
        return {
            "app": snap.app,
            "visibility": snap.visibility,
            "system": snap.system,
        }
