"""NOVA Core Runtime — async foundation with structured concurrency.

Manages the event loop, task groups, health checks, and graceful shutdown.
"""

from __future__ import annotations
import asyncio
import os
import signal
import sys
import time
from typing import Any, Callable, Optional
from dataclasses import dataclass, field

from .config import Config
from .logging import VISIBILITY, Logger


@dataclass
class Runtime:
    """Application runtime — owns the event loop and manages lifecycle."""

    config: Config
    logger: Logger = None
    _tasks: dict[str, asyncio.Task] = field(default_factory=dict)
    _on_startup: list[Callable] = field(default_factory=list)
    _on_shutdown: list[Callable] = field(default_factory=list)
    _running: bool = False
    _start_time: float = 0.0

    def __post_init__(self):
        self.logger = self.logger or VISIBILITY.logger("runtime")
        self.config.ensure_dirs()

    def on_startup(self, fn: Callable):
        """Register a startup handler."""
        self._on_startup.append(fn)
        return fn

    def on_shutdown(self, fn: Callable):
        """Register a shutdown handler."""
        self._on_shutdown.append(fn)
        return fn

    def task(self, name: str) -> Callable:
        """Decorator to register a background task."""
        def decorator(coro_fn):
            self._tasks[name] = None  # placeholder
            return coro_fn
        return decorator

    async def start(self):
        """Start the runtime — run startup hooks, launch tasks."""
        self._running = True
        self._start_time = time.time()

        VISIBILITY.action("runtime.start", f"Starting {self.config.name} v{self.config.version}")

        # Run startup hooks
        for fn in self._on_startup:
            try:
                result = fn()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                self.logger.error("startup", f"Hook failed: {fn.__name__}", {"error": str(e)})

        VISIBILITY.action("runtime.ready", f"Runtime ready in {(time.time() - self._start_time)*1000:.0f}ms")

    async def shutdown(self):
        """Graceful shutdown — run shutdown hooks, cancel tasks."""
        self._running = False
        VISIBILITY.action("runtime.shutdown", "Shutting down")

        # Run shutdown hooks in reverse
        for fn in reversed(self._on_shutdown):
            try:
                result = fn()
                if asyncio.iscoroutine(result):
                    await asyncio.wait_for(result, timeout=10)
            except Exception as e:
                self.logger.error("shutdown", f"Hook failed: {fn.__name__}", {"error": str(e)})

        # Cancel all background tasks
        for name, task in self._tasks.items():
            if task and not task.done():
                task.cancel()

        VISIBILITY.action("runtime.stopped", f"Uptime: {time.time() - self._start_time:.0f}s")

    @property
    def uptime(self) -> float:
        return time.time() - self._start_time if self._start_time else 0

    @property
    def is_running(self) -> bool:
        return self._running
