"""IPC Message Protocol — universal message contract for all agents."""

from __future__ import annotations
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


class MessageType(str, Enum):
    TASK = "task"
    RESULT = "result"
    LOG = "log"
    ERROR = "error"
    PING = "ping"
    CONFIG = "config"
    EVENT = "event"


@dataclass
class Message:
    """Universal message format for all IPC communication."""
    id: str = ""
    type: MessageType = MessageType.TASK
    agent: str = ""
    version: str = "0.1"
    timestamp: str = ""
    ttl_s: int = 120
    trace_id: str = ""
    payload: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = f"msg_{uuid.uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def to_json(self) -> str:
        d = asdict(self)
        d["type"] = self.type.value
        return json.dumps(d, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "Message":
        d = json.loads(text)
        d["type"] = MessageType(d["type"])
        return cls(**d)

    def is_expired(self) -> bool:
        created = time.mktime(time.strptime(self.timestamp,
                              "%Y-%m-%dT%H:%M:%SZ"))
        return time.time() - created > self.ttl_s


@dataclass
class TaskMessage(Message):
    type: MessageType = MessageType.TASK

    @property
    def action(self) -> str:
        return self.payload.get("action", "")

    @property
    def params(self) -> dict:
        return self.payload.get("params", {})

    @property
    def depends_on(self) -> list:
        return self.payload.get("depends_on", [])

    @property
    def retry(self) -> int:
        return self.payload.get("retry", 0)

    @property
    def fallback_action(self) -> Optional[str]:
        fb = self.payload.get("fallback", {})
        return fb.get("action") if fb else None


@dataclass
class ResultMessage(Message):
    type: MessageType = MessageType.RESULT

    @property
    def status(self) -> str:
        return self.payload.get("status", "ok")

    @property
    def output(self) -> Any:
        return self.payload.get("output")

    @property
    def error(self) -> Optional[str]:
        return self.payload.get("error")

    @property
    def duration_ms(self) -> int:
        return self.payload.get("duration_ms", 0)

    @property
    def tokens_used(self) -> int:
        return self.payload.get("tokens_used", 0)


@dataclass
class LogMessage(Message):
    type: MessageType = MessageType.LOG

    @property
    def level(self) -> str:
        return self.payload.get("level", "info")
