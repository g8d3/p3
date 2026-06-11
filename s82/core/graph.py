"""
core/graph.py — Knowledge Graph for agent orchestration.
SQLite-backed, minimal API, agent-friendly.
Adapted from s85-agent-graph.
"""
import json, os, sqlite3, time as _time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path

BASE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = str(BASE / "data" / "agent-graph.db")

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
    status      TEXT DEFAULT 'running',
    error       TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_ops_status ON ops(status);
"""


class Graph:
    def __init__(self, path: str = DB_PATH):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)
        try:
            self.conn.execute("ALTER TABLE ops ADD COLUMN pid INTEGER DEFAULT 0")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass
        self.agent_id = ""

    def set_agent(self, agent_id: str):
        self.agent_id = agent_id

    def _ts(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def add_node(self, type: str, name: str, properties: dict = None,
                 node_id: str = "", agent_id: str = "") -> str:
        nid = node_id or f"{type}-{int(_time.time()*1000)}"
        props = properties or {}
        aid = agent_id or self.agent_id
        ts = self._ts()
        self.conn.execute(
            "INSERT OR REPLACE INTO nodes (id,type,name,properties,created_at,updated_at,agent_id) "
            "VALUES (?,?,?,?,?,?,?)",
            (nid, type, name, json.dumps(props), ts, ts, aid)
        )
        self.conn.commit()
        self.log(aid, "add_node", "node", nid)
        return nid

    def get_node(self, node_id: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["properties"] = json.loads(d["properties"])
        return d

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
        return [{**dict(r), "properties": json.loads(r["properties"])} for r in rows]

    def add_edge(self, source_id: str, type: str, target_id: str,
                 properties: dict = None, agent_id: str = "") -> str:
        eid = f"e-{source_id[:8]}-{target_id[:8]}-{int(_time.time()*1000)}"
        props = properties or {}
        aid = agent_id or self.agent_id
        self.conn.execute(
            "INSERT OR REPLACE INTO edges (id,source_id,target_id,type,properties,created_at,agent_id) "
            "VALUES (?,?,?,?,?,?,?)",
            (eid, source_id, target_id, type, json.dumps(props), self._ts(), aid)
        )
        self.conn.commit()
        self.log(aid, "add_edge", "edge", eid)
        return eid

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
        return [{**dict(r), "properties": json.loads(r["properties"])} for r in rows]

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
        rows = self.conn.execute("""
            SELECT n.* FROM nodes n
            WHERE n.type IN ('goal','task')
            AND n.id NOT IN (
                SELECT e.source_id FROM edges e
                WHERE e.type IN ('next_step','completed','cancelled')
            )
            ORDER BY n.created_at ASC
        """).fetchall()
        return [{**dict(r), "properties": json.loads(r["properties"])} for r in rows]

    def stats(self) -> dict:
        return {
            "nodes": self.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0],
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

    def register_agent(self, agent_id: str, props: dict = None) -> str:
        existing = self.get_node(agent_id)
        now = self._ts()
        if existing:
            p = props or {}
            p["last_seen"] = now
            ts = self._ts()
            self.conn.execute(
                "UPDATE nodes SET properties=?, updated_at=?, agent_id=? WHERE id=?",
                (json.dumps({**existing["properties"], **p}), ts, agent_id, agent_id)
            )
            self.conn.commit()
        else:
            p = props or {}
            p.setdefault("last_seen", now)
            p.setdefault("registered_at", now)
            self.add_node("agent", agent_id, p, node_id=agent_id)
        return agent_id

    def add_relationship(self, source_agent: str, rel_type: str,
                         target_agent: str, props: dict = None) -> str:
        eid = self.add_edge(
            source_id=source_agent, type=rel_type,
            target_id=target_agent, properties=props or {},
            agent_id=source_agent,
        )
        self.log(source_agent, rel_type, "agent", target_agent,
                 "ok", (props or {}).get("note", ""))
        return eid

    def delete_node(self, node_id: str):
        self.conn.execute("DELETE FROM nodes WHERE id=?", (node_id,))
        self.conn.execute("DELETE FROM edges WHERE source_id=? OR target_id=?", (node_id, node_id))
        self.conn.commit()

    def delete_edge(self, edge_id: str):
        self.conn.execute("DELETE FROM edges WHERE id=?", (edge_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
