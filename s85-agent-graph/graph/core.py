"""
agent-graph — Knowledge Graph for agent orchestration.
SQLite-backed, minimal API, agent-friendly.
"""
import json
import os
import sqlite3
import time as _time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional
from .models import Node, Edge


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS nodes (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    name        TEXT NOT NULL,
    properties  TEXT DEFAULT '{}',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    agent_id    TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS edges (
    id          TEXT PRIMARY KEY,
    source_id   TEXT NOT NULL REFERENCES nodes(id),
    target_id   TEXT NOT NULL REFERENCES nodes(id),
    type        TEXT NOT NULL,
    properties  TEXT DEFAULT '{}',
    created_at  TEXT NOT NULL,
    agent_id    TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS agent_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id    TEXT NOT NULL,
    action      TEXT NOT NULL,
    target_type TEXT DEFAULT '',
    target_id   TEXT DEFAULT '',
    result      TEXT DEFAULT 'ok',
    detail      TEXT DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(type);
CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
CREATE INDEX IF NOT EXISTS idx_agent_log_agent ON agent_log(agent_id);

CREATE TABLE IF NOT EXISTS ops (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    agent_id    TEXT DEFAULT '',
    pid         INTEGER DEFAULT 0,
    timeout_s   REAL DEFAULT 30,
    started_at  REAL NOT NULL,
    ended_at    REAL,
    duration_s  REAL,
    status      TEXT DEFAULT 'running',  -- running, ok, timeout, error, killed
    error       TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_ops_status ON ops(status);
"""


class Graph:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        # Migration: add pid column to ops if missing
        try:
            self.conn.execute("ALTER TABLE ops ADD COLUMN pid INTEGER DEFAULT 0")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists
        self.agent_id = ""

    def set_agent(self, agent_id: str):
        self.agent_id = agent_id

    def _ts(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Nodes ──

    def add_node(self, type: str, name: str, properties: dict = None,
                 node_id: str = "", agent_id: str = "") -> str:
        n = Node(type=type, name=name, properties=properties or {},
                 id=node_id, agent_id=agent_id or self.agent_id)
        props_json = json.dumps(n.properties)
        self.conn.execute(
            "INSERT OR REPLACE INTO nodes (id,type,name,properties,created_at,updated_at,agent_id) "
            "VALUES (?,?,?,?,?,?,?)",
            (n.id, n.type, n.name, props_json, n.created_at, n.updated_at, n.agent_id)
        )
        self.conn.commit()
        self.log(n.agent_id, "add_node", "node", n.id)
        return n.id

    def get_node(self, node_id: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["properties"] = json.loads(d["properties"])
        return d

    def update_node(self, node_id: str, properties: dict = None,
                    name: str = None, agent_id: str = ""):
        existing = self.get_node(node_id)
        if not existing:
            return
        new_props = existing["properties"]
        if properties:
            new_props.update(properties)
        new_name = name or existing["name"]
        aid = agent_id or self.agent_id
        self.conn.execute(
            "UPDATE nodes SET name=?, properties=?, updated_at=?, agent_id=? WHERE id=?",
            (new_name, json.dumps(new_props), self._ts(), aid, node_id)
        )
        self.conn.commit()
        self.log(aid, "update_node", "node", node_id)

    def delete_node(self, node_id: str):
        self.conn.execute("DELETE FROM nodes WHERE id=?", (node_id,))
        self.conn.execute("DELETE FROM edges WHERE source_id=? OR target_id=?", (node_id, node_id))
        self.conn.commit()
        self.log(self.agent_id, "delete_node", "node", node_id)

    def query_nodes(self, type: str = None, **filters) -> list[dict]:
        sql = "SELECT * FROM nodes WHERE 1=1"
        params = []
        if type:
            sql += " AND type=?"
            params.append(type)
        for key, val in filters.items():
            if key in ("name", "agent_id"):
                sql += f" AND {key}=?"
                params.append(val)
            else:
                sql += f" AND json_extract(properties,'$.{key}')=?"
                params.append(val)
        sql += " ORDER BY created_at DESC"
        rows = self.conn.execute(sql, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["properties"] = json.loads(d["properties"])
            results.append(d)
        return results

    def search_nodes(self, text: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM nodes WHERE name LIKE ? OR properties LIKE ?",
            (f"%{text}%", f"%{text}%")
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["properties"] = json.loads(d["properties"])
            results.append(d)
        return results

    def count_nodes(self, type: str = None) -> int:
        if type:
            return self.conn.execute("SELECT COUNT(*) FROM nodes WHERE type=?", (type,)).fetchone()[0]
        return self.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]

    # ── Edges ──

    def add_edge(self, source_id: str, type: str, target_id: str,
                 properties: dict = None, agent_id: str = "") -> str:
        e = Edge(source_id=source_id, type=type, target_id=target_id,
                 properties=properties or {}, agent_id=agent_id or self.agent_id)
        props_json = json.dumps(e.properties)
        self.conn.execute(
            "INSERT OR REPLACE INTO edges (id,source_id,target_id,type,properties,created_at,agent_id) "
            "VALUES (?,?,?,?,?,?,?)",
            (e.id, e.source_id, e.target_id, e.type, props_json, e.created_at, e.agent_id)
        )
        self.conn.commit()
        self.log(e.agent_id, "add_edge", "edge", e.id)
        return e.id

    def get_edges(self, type: str = None, source_id: str = None,
                  target_id: str = None) -> list[dict]:
        sql = "SELECT * FROM edges WHERE 1=1"
        params = []
        if type:
            sql += " AND type=?"
            params.append(type)
        if source_id:
            sql += " AND source_id=?"
            params.append(source_id)
        if target_id:
            sql += " AND target_id=?"
            params.append(target_id)
        sql += " ORDER BY created_at DESC"
        rows = self.conn.execute(sql, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["properties"] = json.loads(d["properties"])
            results.append(d)
        return results

    def get_children(self, node_id: str, edge_type: str = None) -> list[dict]:
        return self.get_edges(source_id=node_id, type=edge_type)

    def get_parents(self, node_id: str, edge_type: str = None) -> list[dict]:
        return self.get_edges(target_id=node_id, type=edge_type)

    def delete_edge(self, edge_id: str):
        self.conn.execute("DELETE FROM edges WHERE id=?", (edge_id,))
        self.conn.commit()

    # ── Subgraph ──

    def get_subgraph(self, node_id: str, depth: int = 1, visited: set = None) -> dict:
        if visited is None:
            visited = set()
        if node_id in visited or depth < 0:
            return {}
        visited.add(node_id)
        node = self.get_node(node_id)
        if not node:
            return {}
        result = {"node": node, "edges": [], "children": []}
        for e in self.get_edges(source_id=node_id):
            result["edges"].append(e)
            child = self.get_subgraph(e["target_id"], depth - 1, visited)
            if child:
                result["children"].append(child)
        return result

    # ── Agent Log ──

    def log(self, agent_id: str, action: str, target_type: str = "",
            target_id: str = "", result: str = "ok", detail: str = ""):
        self.conn.execute(
            "INSERT INTO agent_log (agent_id,action,target_type,target_id,result,detail,created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (agent_id or self.agent_id, action, target_type, target_id, result, detail, self._ts())
        )
        self.conn.commit()

    def get_log(self, agent_id: str = None, limit: int = 50) -> list[dict]:
        if agent_id:
            rows = self.conn.execute(
                "SELECT * FROM agent_log WHERE agent_id=? ORDER BY created_at DESC LIMIT ?",
                (agent_id, limit)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM agent_log ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def pending_tasks(self) -> list[dict]:
        """Find nodes marked as goal or task with no outgoing 'next_step' or 'completed' edge."""
        rows = self.conn.execute("""
            SELECT n.* FROM nodes n
            WHERE n.type IN ('goal','task')
            AND n.id NOT IN (
                SELECT e.source_id FROM edges e
                WHERE e.type IN ('next_step','completed','cancelled')
            )
            ORDER BY n.created_at ASC
        """).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["properties"] = json.loads(d["properties"])
            results.append(d)
        return results

    def stats(self) -> dict:
        return {
            "nodes": self.count_nodes(),
            "nodes_by_type": {
                r["type"]: r["cnt"] for r in
                self.conn.execute("SELECT type, COUNT(*) as cnt FROM nodes GROUP BY type").fetchall()
            },
            "edges": self.conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0],
            "agents": self.conn.execute(
                "SELECT COUNT(DISTINCT agent_id) FROM agent_log"
            ).fetchone()[0],
            "pending_tasks": len(self.pending_tasks()),
        }

    # ── Operations with Time Awareness ──

    @contextmanager
    def op(self, name: str, timeout_s: float = 30, agent_id: str = "", pid: int = 0):
        """Context manager: auto-logs operation with timing.
        Usage: with graph.op("scan_project", timeout_s=60) as op:
                   do_work()
        """
        import os as _os
        aid = agent_id or self.agent_id
        now = _time.time()
        pid = pid or _os.getpid()
        cur = self.conn.execute(
            "INSERT INTO ops (name,agent_id,pid,timeout_s,started_at,status) VALUES (?,?,?,?,?,'running')",
            (name, aid, pid, timeout_s, now)
        )
        op_id = cur.lastrowid
        self.conn.commit()
        try:
            yield {"id": op_id, "name": name}
            ended = _time.time()
            duration = ended - now
            if duration > timeout_s:
                self.conn.execute(
                    "UPDATE ops SET ended_at=?, duration_s=?, status='timeout' WHERE id=?",
                    (ended, duration, op_id)
                )
            else:
                self.conn.execute(
                    "UPDATE ops SET ended_at=?, duration_s=?, status='ok' WHERE id=?",
                    (ended, duration, op_id)
                )
            self.conn.commit()
        except Exception as e:
            ended = _time.time()
            self.conn.execute(
                "UPDATE ops SET ended_at=?, duration_s=?, status='error', error=? WHERE id=?",
                (ended, ended - now, str(e)[:200], op_id)
            )
            self.conn.commit()
            raise

    def check_hanging(self) -> list[dict]:
        """Find operations that are still 'running' past their timeout."""
        now = _time.time()
        rows = self.conn.execute(
            "SELECT * FROM ops WHERE status='running' AND (? - started_at) > timeout_s",
            (now,)
        ).fetchall()
        return [dict(r) for r in rows]

    def recent_ops(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM ops ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Agent Relationships ──

    def register_agent(self, agent_id: str, props: dict = None) -> str:
        """Register or heartbeat an agent node. Creates if not exists."""
        existing = self.get_node(agent_id)
        now = self._ts()
        if existing:
            props = props or {}
            props["last_seen"] = now
            self.update_node(agent_id, props)
        else:
            p = props or {}
            p.setdefault("last_seen", now)
            p.setdefault("registered_at", now)
            self.add_node("agent", agent_id, p, node_id=agent_id)
        return agent_id

    def add_relationship(self, source_agent: str, rel_type: str,
                         target_agent: str, props: dict = None) -> str:
        """Record a relationship action between two agents.
        rel_type: helped, observed, interrupted, communicated, ignored, trusts
        """
        eid = self.add_edge(
            source_id=source_agent,
            type=rel_type,
            target_id=target_agent,
            properties=props or {},
            agent_id=source_agent,
        )
        self.log(source_agent, rel_type, "agent", target_agent,
                 "ok", (props or {}).get("note", ""))
        return eid

    def get_relationships(self, agent_id: str, rel_type: str = None,
                          direction: str = "both") -> list[dict]:
        """Get relationships for an agent. direction: both, outgoing, incoming."""
        results = []
        if direction in ("both", "outgoing"):
            results.extend(self.get_edges(source_id=agent_id, type=rel_type))
        if direction in ("both", "incoming"):
            results.extend(self.get_edges(target_id=agent_id, type=rel_type))
        return results

    def relationship_summary(self, agent_id: str) -> dict:
        """Summarize all relationships for an agent into readable stats."""
        rels = self.get_relationships(agent_id)
        summary = {
            "agent_id": agent_id,
            "total_interactions": len(rels),
            "by_type": {},
            "by_agent": {},
            "last_interaction": None,
            "trust_score": 0.5,
        }
        for r in rels:
            t = r["type"]
            summary["by_type"][t] = summary["by_type"].get(t, 0) + 1
            peer = r["source_id"] if r["target_id"] == agent_id else r["target_id"]
            if peer not in summary["by_agent"]:
                summary["by_agent"][peer] = {"outgoing": 0, "incoming": 0, "types": {}}
            direction = "incoming" if r["target_id"] == agent_id else "outgoing"
            summary["by_agent"][peer][direction] += 1
            summary["by_agent"][peer]["types"][t] = summary["by_agent"][peer]["types"].get(t, 0) + 1
            if summary["last_interaction"] is None or r["created_at"] > summary["last_interaction"]:
                summary["last_interaction"] = r["created_at"]
        # Trust heuristic
        helped = summary["by_type"].get("helped", 0)
        interrupted = summary["by_type"].get("interrupted", 0)
        if helped + interrupted > 0:
            summary["trust_score"] = round(helped / (helped + interrupted), 2)
        return summary

    def get_agent_context(self, agent_id: str, for_agent: str = None) -> dict:
        """Full context about an agent for another agent to reason about."""
        node = self.get_node(agent_id)
        if not node:
            return {"error": f"agent {agent_id} not found"}
        context = {
            "agent": {k: v for k, v in node.items() if k != "properties"},
            "properties": node["properties"],
            "log": self.get_log(agent_id=agent_id, limit=10),
            "relationships": {},
            "pending_tasks": [],
        }
        if for_agent:
            rels = self.get_relationships(agent_id, direction="both")
            between = [
                r for r in rels
                if (r["source_id"] == for_agent or r["target_id"] == for_agent)
            ]
            context["relationships"]["with"] = for_agent
            context["relationships"]["interactions"] = between
            context["relationships"]["summary"] = self.relationship_summary(agent_id)
        context["pending_tasks"] = self.pending_tasks()
        return context

    def close(self):
        self.conn.close()
