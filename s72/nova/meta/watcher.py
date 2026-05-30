"""Spec Watcher — watches spec file for changes and triggers regeneration."""

from __future__ import annotations
import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional

from .spec import Spec, parse_spec
from .codegen import CodeGenerator
from ..core.logging import VISIBILITY


class SpecWatcher:
    """Watches app.yaml for changes, re-parses, and triggers codegen."""

    def __init__(self, spec_path: str, output_dir: str = "generated",
                 on_change: Optional[Callable[[Spec], None]] = None):
        self.spec_path = Path(spec_path)
        self.output_dir = output_dir
        self._on_change = on_change
        self._last_mtime: float = 0
        self._last_spec: Optional[Spec] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.codegen = CodeGenerator(output_dir)

    def start(self, poll_interval: float = 2.0, auto_generate: bool = True):
        """Start watching the spec file."""
        if not self.spec_path.exists():
            VISIBILITY.log("WARN", "spec.watcher",
                           f"Spec not found: {self.spec_path}")
            return

        self._last_mtime = self.spec_path.stat().st_mtime
        self._last_spec = parse_spec(str(self.spec_path))
        VISIBILITY.action("spec.loaded", f"Loaded spec '{self._last_spec.name}' v{self._last_spec.version}",
                          {"models": len(self._last_spec.models),
                           "routes": len(self._last_spec.routes)})

        if auto_generate:
            self._generate()

        self._running = True
        self._thread = threading.Thread(
            target=self._poll_loop,
            args=(poll_interval,),
            daemon=True,
        )
        self._thread.start()

    def _poll_loop(self, interval: float):
        while self._running:
            try:
                mtime = self.spec_path.stat().st_mtime
                if mtime != self._last_mtime:
                    self._last_mtime = mtime
                    VISIBILITY.action("spec.changed", "Spec file changed, re-generating...")
                    try:
                        self._last_spec = parse_spec(str(self._spec_path))
                        self._generate()
                        if self._on_change:
                            self._on_change(self._last_spec)
                    except Exception as e:
                        VISIBILITY.log("ERROR", "spec.watcher", f"Re-generation failed: {e}")
            except Exception:
                pass
            time.sleep(interval)

    def _generate(self):
        if self._last_spec:
            written = self.codegen.write_all(self._last_spec, self.output_dir)
            VISIBILITY.action("codegen.complete",
                              f"Generated {len(written)} files in {self.output_dir}/")

    @property
    def spec(self) -> Optional[Spec]:
        return self._last_spec

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def regenerate(self):
        """Force re-generation."""
        if self.spec_path.exists():
            self._last_spec = parse_spec(str(self.spec_path))
            self._generate()
