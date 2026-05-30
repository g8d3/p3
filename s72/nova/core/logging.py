"""Structured logging with total visibility.

Every log entry is structured JSON. The VisibilityStack collects
logs from all layers and exposes them for DevTools + AI agents.
"""

from __future__ import annotations
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Optional
from collections import deque
from dataclasses import dataclass, field, asdict


@dataclass
class LogEntry:
    ts: str = ""
    level: str = "INFO"
    source: str = "system"
    message: str = ""
    trace_id: str = ""
    span_id: str = ""
    data: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.ts:
            self.ts = time.strftime("%H:%M:%S.%f")[:12]


class Logger:
    """Logger that writes structured JSON to file + stderr."""

    def __init__(self, log_dir: str = "logs", max_entries: int = 10000):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"nova_{time.strftime('%Y%m%d')}.log"
        self.max_entries = max_entries
        self._entries: deque[LogEntry] = deque(maxlen=max_entries)

    def log(self, level: str, source: str, message: str, data: Any = None,
            trace_id: str = "", span_id: str = "") -> LogEntry:
        entry = LogEntry(
            level=level.upper(),
            source=source,
            message=message,
            trace_id=trace_id or "",
            span_id=span_id or "",
            data=data if isinstance(data, dict) else {"_raw": str(data)[:500]} if data else {},
        )
        self._entries.append(entry)
        line = json.dumps(asdict(entry), ensure_ascii=False)
        with open(self.log_file, "a") as f:
            f.write(line + "\n")
        print(f"[{entry.ts}] {entry.level} {entry.source}: {entry.message}",
              file=sys.stderr)
        return entry

    def info(self, source: str, message: str, **data):
        return self.log("INFO", source, message, data)

    def warn(self, source: str, message: str, **data):
        return self.log("WARN", source, message, data)

    def error(self, source: str, message: str, **data):
        return self.log("ERROR", source, message, data)

    def debug(self, source: str, message: str, **data):
        return self.log("DEBUG", source, message, data)

    def recent(self, n: int = 50) -> list[LogEntry]:
        return list(self._entries)[-n:]

    def flush(self):
        pass  # Entries written immediately


class VisibilityStack:
    """Collects logs from all layers — DevTools and AI agents read from here."""

    _instance: Optional["VisibilityStack"] = None

    def __init__(self):
        self.loggers: dict[str, Logger] = {}
        self._errors: deque[LogEntry] = deque(maxlen=500)
        self._actions: deque[dict] = deque(maxlen=200)

    @classmethod
    def instance(cls) -> "VisibilityStack":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def logger(self, name: str = "default", log_dir: str = "logs") -> Logger:
        if name not in self.loggers:
            self.loggers[name] = Logger(log_dir)
        return self.loggers[name]

    def log(self, level: str, source: str, message: str, data=None) -> LogEntry:
        entry = self.logger().log(level, source, message, data)
        if level.upper() in ("ERROR", "CRITICAL"):
            self._errors.append(entry)
        return entry

    def action(self, kind: str, detail: str, data: dict = None) -> None:
        entry = {
            "ts": time.strftime("%H:%M:%S"),
            "kind": kind,
            "detail": detail,
            "data": data or {},
        }
        self._actions.append(entry)
        self.log("INFO", "action", f"{kind}: {detail}", data)

    def get_errors(self, n: int = 20) -> list[LogEntry]:
        return list(self._errors)[-n:]

    def get_actions(self, n: int = 20) -> list[dict]:
        return list(reversed(self._actions))[:n]

    def get_status(self) -> dict:
        return {
            "total_logs": sum(len(l._entries) for l in self.loggers.values()),
            "errors": len(self._errors),
            "actions": len(self._actions),
            "loggers": list(self.loggers.keys()),
        }


# Global visibility stack
VISIBILITY = VisibilityStack.instance()
log = VISIBILITY.log
action = VISIBILITY.action
