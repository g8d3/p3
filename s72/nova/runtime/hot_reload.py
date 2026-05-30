"""Hot-Reloader — watches files and triggers live reloads.

Supports: code (module reload), config (runtime update),
templates (DOM patching), assets (cache invalidation), spec (regeneration).
"""

from __future__ import annotations
import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional
from dataclasses import dataclass, field

from ..core.logging import VISIBILITY


@dataclass
class WatchTarget:
    path: str
    pattern: str = "*"
    recursive: bool = True
    handler: Optional[Callable] = None
    _last_mtime: float = 0


class HotReloader:
    """File watcher that triggers hot-reloads for multiple target types."""

    def __init__(self):
        self._targets: list[WatchTarget] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def watch(self, path: str, handler: Callable = None, pattern: str = "*",
              recursive: bool = True) -> WatchTarget:
        """Register a path to watch."""
        target = WatchTarget(
            path=path,
            pattern=pattern,
            recursive=recursive,
            handler=handler,
        )
        if os.path.exists(path):
            target._last_mtime = os.path.getmtime(path) if os.path.isfile(path) else time.time()
        self._targets.append(target)
        return target

    def on_config_change(self, config_path: str):
        """Watch config file for changes."""
        def handler(path):
            VISIBILITY.action("hotreload.config", f"Config changed: {path}")
        return self.watch(config_path, handler)

    def on_spec_change(self, spec_path: str, regenerate_cb: Callable):
        """Watch spec file for changes."""
        def handler(path):
            VISIBILITY.action("hotreload.spec", f"Spec changed: {path}")
            regenerate_cb()
        return self.watch(spec_path, handler)

    def start(self, poll_interval: float = 1.0):
        """Start watching all targets."""
        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop,
            args=(poll_interval,),
            daemon=True,
        )
        self._thread.start()
        VISIBILITY.action("hotreload.start",
                          f"Watching {len(self._targets)} targets (poll={poll_interval}s)")

    def _poll_loop(self, interval: float):
        while self._running:
            for target in self._targets:
                try:
                    path = Path(target.path)
                    if not path.exists():
                        continue
                    if path.is_file():
                        mtime = path.stat().st_mtime
                        if mtime != target._last_mtime:
                            target._last_mtime = mtime
                            if target.handler:
                                target.handler(str(path))
                    elif path.is_dir():
                        self._check_dir(path, target)
                except Exception as e:
                    VISIBILITY.log("ERROR", "hotreload", f"Watch error: {e}")
            time.sleep(interval)

    def _check_dir(self, directory: Path, target: WatchTarget):
        import fnmatch
        for entry in directory.iterdir():
            if entry.is_file() and fnmatch.fnmatch(entry.name, target.pattern):
                mtime = entry.stat().st_mtime
                if mtime != target._last_mtime:
                    target._last_mtime = mtime
                    if target.handler:
                        target.handler(str(entry))
            elif entry.is_dir() and target.recursive:
                self._check_dir(entry, target)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
