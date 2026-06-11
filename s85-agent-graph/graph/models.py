from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    import uuid
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass
class Node:
    type: str  # agent, project, task, artifact, decision, lesson, error, goal, skill
    name: str
    properties: dict = field(default_factory=dict)
    id: str = ""
    created_at: str = ""
    updated_at: str = ""
    agent_id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = _new_id(self.type[:3])
        if not self.created_at:
            self.created_at = _now()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class Edge:
    source_id: str
    type: str  # executed, produced, depends_on, learned, relates_to, contains, next_step, blocked_by, has_capability, based_on,
               # helped, observed, interrupted, communicated, trusts
    target_id: str
    properties: dict = field(default_factory=dict)
    id: str = ""
    created_at: str = ""
    agent_id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = _new_id("e")
        if not self.created_at:
            self.created_at = _now()


RELATIONSHIP_TYPES = {
    "helped":       "A helped B (unstuck, provided info, etc.)",
    "observed":     "A observed B's state/output",
    "interrupted":  "A interrupted B's command (Escape/Ctrl-C)",
    "communicated": "A sent a message to B",
    "ignored":      "A ignored B's state (decision not to intervene)",
    "trusts":       "A trusts B (score 0-1 in properties)",
}
