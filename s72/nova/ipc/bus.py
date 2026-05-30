"""IPC Bus — filesystem-based inbox/outbox message passing.

Agents communicate through the filesystem. One file = one message.
The bus watches inbox dirs and delivers messages to the right agent.
"""

from __future__ import annotations
import json
import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional
from collections import defaultdict

from .protocol import Message, MessageType, TaskMessage, ResultMessage
from ..core.logging import VISIBILITY


class InboxOutbox:
    """Filesystem-based inbox/outbox for a single agent."""

    def __init__(self, base_dir: str, agent_id: str):
        self.agent_id = agent_id
        self.base_dir = Path(base_dir)
        self.inbox_dir = self.base_dir / "inbox" / agent_id
        self.outbox_dir = self.base_dir / "outbox" / agent_id
        self.shared_dir = self.base_dir / "shared"
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        self.shared_dir.mkdir(parents=True, exist_ok=True)

    def write_inbox(self, message: Message) -> str:
        """Write a message to this agent's inbox."""
        path = self.inbox_dir / f"{message.id}.json"
        path.write_text(message.to_json())
        return str(path)

    def read_inbox(self) -> list[Message]:
        """Read all pending messages from inbox."""
        messages = []
        for f in sorted(self.inbox_dir.glob("*.json")):
            try:
                msg = Message.from_json(f.read_text())
                messages.append(msg)
            except Exception as e:
                VISIBILITY.log("ERROR", "ipc", f"Failed to read {f.name}: {e}")
        return messages

    def ack(self, message_id: str):
        """Remove a message from inbox (acknowledge)."""
        path = self.inbox_dir / f"{message_id}.json"
        if path.exists():
            path.unlink()

    def write_outbox(self, message: Message) -> str:
        """Write a message to outbox."""
        path = self.outbox_dir / f"{message.id}.json"
        path.write_text(message.to_json())
        return str(path)

    def read_outbox(self) -> list[Message]:
        """Read all messages from outbox."""
        messages = []
        for f in sorted(self.outbox_dir.glob("*.json")):
            try:
                messages.append(Message.from_json(f.read_text()))
            except Exception:
                pass
        return messages

    def clean_outbox(self, max_age_s: int = 3600):
        """Remove old outbox messages."""
        now = time.time()
        for f in self.outbox_dir.glob("*.json"):
            if now - f.stat().st_mtime > max_age_s:
                f.unlink()

    def write_shared(self, key: str, data: dict) -> str:
        """Write shared data readable by all agents."""
        path = self.shared_dir / f"{key}.json"
        path.write_text(json.dumps(data, ensure_ascii=False))
        return str(path)

    def read_shared(self, key: str) -> Optional[dict]:
        """Read shared data."""
        path = self.shared_dir / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text())
        return None


class IPCBus:
    """Central IPC bus — routes messages between agents.

    Watches inbox/outbox directories and dispatches to handlers.
    """

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._agents: dict[str, InboxOutbox] = {}
        self._handlers: dict[str, list[Callable]] = defaultdict(list)
        self._running = False
        self._watcher_thread: Optional[threading.Thread] = None

    def register_agent(self, agent_id: str) -> InboxOutbox:
        """Register an agent and create its inbox/outbox."""
        io = InboxOutbox(str(self.base_dir), agent_id)
        self._agents[agent_id] = io
        VISIBILITY.action("ipc.register", f"Agent {agent_id} registered")
        return io

    def on_message(self, agent_id: str = "*", handler: Callable = None):
        """Register a handler for messages from a specific agent (or all)."""
        if handler is None:
            def decorator(fn):
                self._handlers[agent_id].append(fn)
                return fn
            return decorator
        self._handlers[agent_id].append(handler)

    def send(self, to_agent: str, message: Message):
        """Send a message to an agent's inbox."""
        if to_agent in self._agents:
            self._agents[to_agent].write_inbox(message)
            VISIBILITY.log("DEBUG", "ipc.send",
                           f"{message.type.value} → {to_agent}: {message.id}")
        else:
            VISIBILITY.log("WARN", "ipc.send",
                           f"Unknown agent: {to_agent}")

    def broadcast(self, message: Message):
        """Send a message to all agents."""
        for agent_id in self._agents:
            self._agents[agent_id].write_inbox(message)

    def start(self, poll_interval: float = 1.0):
        """Start watching all outbox dirs for new messages."""
        self._running = True
        self._watcher_thread = threading.Thread(
            target=self._poll_loop,
            args=(poll_interval,),
            daemon=True,
        )
        self._watcher_thread.start()
        VISIBILITY.action("ipc.start", f"IPC Bus started (poll={poll_interval}s)")

    def _poll_loop(self, interval: float):
        while self._running:
            for agent_id, io in self._agents.items():
                messages = io.read_outbox()
                for msg in messages:
                    self._dispatch(agent_id, msg)
                    io.clean_outbox()
            time.sleep(interval)

    def _dispatch(self, from_agent: str, message: Message):
        """Dispatch a message to registered handlers."""
        # Notify specific agent handlers
        for handler in self._handlers.get(from_agent, []):
            try:
                handler(message)
            except Exception as e:
                VISIBILITY.log("ERROR", "ipc.dispatch",
                               f"Handler error for {from_agent}: {e}")
        # Notify wildcard handlers
        for handler in self._handlers.get("*", []):
            try:
                handler(message)
            except Exception as e:
                VISIBILITY.log("ERROR", "ipc.dispatch",
                               f"Wildcard handler error: {e}")

    def stop(self):
        self._running = False
        if self._watcher_thread:
            self._watcher_thread.join(timeout=5)

    def status(self) -> dict:
        return {
            "agents": list(self._agents.keys()),
            "handlers": {k: len(v) for k, v in self._handlers.items()},
            "running": self._running,
        }
