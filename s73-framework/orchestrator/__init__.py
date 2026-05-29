#!/usr/bin/env python3.12
"""Orchestrator — Daemon central del framework multi-agente.

Responsabilidades:
- Gestionar cola de tareas con prioridades y fallbacks
- Comunicación con agentes vía inbox/outbox (JSON sobre archivos)
- Comunicación con UI vía WebSocket
- Persistencia de estado en SQLite
- Health checks y reinicio de agentes
- Hot-reload de config
"""

import asyncio
import json
import logging
import os
import signal
import sqlite3
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

# ── Config ――――――――――――――――――――――――――――――――――――――――――――

DEFAULT_CONFIG = {
    "orchestrator": {
        "host": "0.0.0.0",
        "port": 9876,
        "ws_port": 9877,
        "state_db": "data/state.db",
        "log_retention_days": 7,
        "max_queue_size": 100,
        "poll_interval_ms": 500,
        "cleanup_after_hours": 24,
    },
    "ipc": {
        "inbox_dir": "inbox",
        "outbox_dir": "outbox",
        "shared_dir": "shared",
    },
    "agents": {},
}

CONFIG_PATH = os.environ.get("FRAMEWORK_CONFIG", "config.yaml")
config = dict(DEFAULT_CONFIG)


def load_config():
    global config
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            loaded = yaml.safe_load(f) or {}
            # Deep merge
            for section in ("orchestrator", "ipc", "agents"):
                if section in loaded:
                    config[section].update(loaded[section])
        log("info", "config", f"Loaded config from {CONFIG_PATH}")
    else:
        log("warn", "config", f"No config at {CONFIG_PATH}, using defaults")


# ── Logging ――――――――――――――――――――――――――――――――――――――――――

def log(level: str, source: str, message: str, data: dict | None = None):
    """Log estructurado en JSON a stdout (para que el framework lo capture)."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "source": source,
        "message": message,
        "data": data or {},
    }
    print(json.dumps(entry), flush=True)


# ── State DB ――――――――――――――――――――――――――――――――――――――――

class StateDB:
    """SQLite central — tareas, resultados, logs, config."""

    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                agent TEXT NOT NULL,
                action TEXT NOT NULL,
                params TEXT,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 0,
                created_at TEXT,
                started_at TEXT,
                completed_at TEXT,
                duration_ms INTEGER,
                error TEXT,
                result TEXT,
                fallback_used TEXT,
                parent_task TEXT
            );
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                level TEXT,
                source TEXT,
                message TEXT,
                data TEXT
            );
            CREATE TABLE IF NOT EXISTS agents (
                name TEXT PRIMARY KEY,
                status TEXT DEFAULT 'idle',
                pid INTEGER,
                last_seen TEXT,
                tasks_completed INTEGER DEFAULT 0,
                tasks_failed INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS config_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                config TEXT
            );
        """)
        self.conn.commit()

    def save_task(self, task: dict):
        payload = task.get("payload", {})
        action = payload.get("action", task.get("action", ""))
        self.conn.execute("""
            INSERT OR REPLACE INTO tasks
            (id, agent, action, params, status, priority, created_at, parent_task)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task["id"], task.get("agent", ""), action,
            json.dumps(task.get("params", payload.get("params", {}))), task.get("status", "pending"),
            task.get("priority", 0), task.get("created_at", now_iso()),
            task.get("parent_task", ""),
        ))
        self.conn.commit()

    def update_task(self, task_id: str, **updates):
        fields = ", ".join(f"{k}=?" for k in updates)
        vals = list(updates.values()) + [task_id]
        self.conn.execute(f"UPDATE tasks SET {fields} WHERE id=?", vals)
        self.conn.commit()

    def get_task(self, task_id: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row:
            d = dict(row)
            for f in ("params", "result"):
                if d.get(f):
                    try:
                        d[f] = json.loads(d[f])
                    except (json.JSONDecodeError, TypeError):
                        pass
            return d
        return None

    def get_pending_tasks(self, agent: str = None) -> list[dict]:
        query = "SELECT * FROM tasks WHERE status='pending'"
        params = []
        if agent:
            query += " AND agent=?"
            params.append(agent)
        query += " ORDER BY priority DESC, created_at ASC"
        return [dict(row) for row in self.conn.execute(query, params).fetchall()]

    def get_all_tasks(self, limit: int = 50) -> list[dict]:
        return [dict(row) for row in
                self.conn.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()]

    def log_event(self, level: str, source: str, message: str, data: dict | None = None):
        self.conn.execute(
            "INSERT INTO logs (ts, level, source, message, data) VALUES (?, ?, ?, ?, ?)",
            (now_iso(), level, source, message, json.dumps(data or {})),
        )
        self.conn.commit()

    def get_logs(self, limit: int = 100, level: str = None) -> list[dict]:
        query = "SELECT * FROM logs"
        params = []
        if level:
            query += " WHERE level=?"
            params.append(level)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return [dict(row) for row in self.conn.execute(query, params).fetchall()]

    def upsert_agent(self, name: str, **fields):
        existing = self.conn.execute("SELECT * FROM agents WHERE name=?", (name,)).fetchone()
        if existing:
            sets = ", ".join(f"{k}=?" for k in fields)
            vals = list(fields.values()) + [name]
            self.conn.execute(f"UPDATE agents SET {sets} WHERE name=?", vals)
        else:
            keys = ", ".join(fields.keys())
            placeholders = ", ".join("?" for _ in fields)
            vals = list(fields.values())
            self.conn.execute(f"INSERT INTO agents (name, {keys}) VALUES (?, {placeholders})", [name] + vals)
        self.conn.commit()

    def get_agents(self) -> list[dict]:
        return [dict(row) for row in self.conn.execute("SELECT * FROM agents ORDER BY name").fetchall()]

    def close(self):
        self.conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ── IPC File Bus ―――――――――――――――――――――――――――――――――――

class IPCBus:
    """Maneja inbox/outbox sobre filesystem."""

    def __init__(self, base_dir: str, state: StateDB):
        self.base = Path(base_dir)
        self.inbox_dir = self.base / "inbox"
        self.outbox_dir = self.base / "outbox"
        self.shared_dir = self.base / "shared"
        self.state = state
        for d in [self.inbox_dir, self.outbox_dir, self.shared_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def agent_inbox(self, agent_name: str) -> Path:
        p = self.inbox_dir / agent_name
        p.mkdir(parents=True, exist_ok=True)
        return p

    def agent_outbox(self, agent_name: str) -> Path:
        p = self.outbox_dir / agent_name
        p.mkdir(parents=True, exist_ok=True)
        return p

    def send_task(self, agent_name: str, task: dict):
        """Escribe una tarea en el inbox del agente."""
        inbox = self.agent_inbox(agent_name)
        task_path = inbox / f"{task['id']}.json"
        with open(task_path, "w") as f:
            json.dump(task, f, indent=2)
        self.state.save_task(task)
        log("info", "ipc", f"Task {task['id']} -> {agent_name}", {
            "action": task.get("action"), "agent": agent_name
        })

    def read_results(self, agent_name: str) -> list[dict]:
        """Lee todos los resultados del outbox de un agente."""
        outbox = self.agent_outbox(agent_name)
        results = []
        for fpath in sorted(outbox.glob("*.json"), key=os.path.getmtime):
            try:
                with open(fpath) as f:
                    msg = json.load(f)
                results.append(msg)
                # Clean up after reading
                fpath.unlink()
            except (json.JSONDecodeError, OSError) as e:
                log("error", "ipc", f"Failed to read {fpath.name}: {e}")
        return results

    def read_shared(self, name: str) -> Optional[dict]:
        fpath = self.shared_dir / f"{name}.json"
        if fpath.exists():
            try:
                with open(fpath) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def write_shared(self, name: str, data: dict):
        fpath = self.shared_dir / f"{name}.json"
        with open(fpath, "w") as f:
            json.dump(data, f, indent=2)


# ── Agent Process Manager ――――――――――――――――――――――――――

class AgentManager:
    """Lanza, monitorea, y mata procesos agente."""

    def __init__(self, state: StateDB):
        self.state = state
        self.processes: dict[str, subprocess.Popen] = {}
        self.shutdown_event = asyncio.Event()

    async def start_agent(self, name: str, command: str, env: dict | None = None):
        if name in self.processes and self.processes[name].poll() is None:
            log("warn", "agent", f"{name} already running, skipping")
            return

        log("info", "agent", f"Starting agent {name}: {command}")
        agent_env = os.environ.copy()
        if env:
            agent_env.update(env)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=agent_env,
            )
            self.processes[name] = proc
            self.state.upsert_agent(name, status="running", pid=proc.pid,
                                    last_seen=now_iso())

            # Start stdout/stderr readers
            asyncio.create_task(self._read_stdout(name, proc))
            asyncio.create_task(self._read_stderr(name, proc))

            # Monitor process
            asyncio.create_task(self._monitor(name, proc))
        except Exception as e:
            log("error", "agent", f"Failed to start {name}: {e}")
            self.state.upsert_agent(name, status="error", last_seen=now_iso())

    async def _read_stdout(self, name: str, proc: subprocess.Popen):
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode().strip())
                self._handle_agent_message(name, msg)
            except json.JSONDecodeError:
                log("info", name, line.decode().strip())

    async def _read_stderr(self, name: str, proc: subprocess.Popen):
        while True:
            line = await proc.stderr.readline()
            if not line:
                break
            log("error", name, line.decode().strip())

    def _handle_agent_message(self, agent: str, msg: dict):
        msg_type = msg.get("type", "log")
        payload = msg.get("payload", {})
        if msg_type == "result":
            task_id = msg.get("id", "")
            self.state.update_task(task_id,
                status=payload.get("status", "completed"),
                result=json.dumps(payload.get("output", {})),
                completed_at=now_iso(),
                duration_ms=payload.get("duration_ms"),
                fallback_used=payload.get("fallback_used"),
            )
            if payload.get("status") == "ok":
                self.state.upsert_agent(agent, tasks_completed=1, status="idle",
                                        last_seen=now_iso())
            else:
                self.state.upsert_agent(agent, tasks_failed=1, status="idle",
                                        last_seen=now_iso())
        elif msg_type == "log":
            self.state.log_event(
                payload.get("level", "info"), agent,
                payload.get("message", ""), payload.get("data"),
            )
        elif msg_type == "error":
            self.state.log_event("error", agent,
                payload.get("message", ""), {"stack": payload.get("stack", "")})

    async def _monitor(self, name: str, proc: subprocess.Popen):
        returncode = await proc.wait()
        log("info", "agent", f"{name} exited with code {returncode}")
        self.state.upsert_agent(name, status="stopped" if returncode == 0 else "crashed",
                                pid=None, last_seen=now_iso())
        self.processes.pop(name, None)

    def stop_agent(self, name: str):
        proc = self.processes.get(name)
        if proc:
            proc.terminate()
            log("info", "agent", f"Sent terminate to {name}")

    def stop_all(self):
        for name in list(self.processes.keys()):
            self.stop_agent(name)


# ── Orchestrator ――――――――――――――――――――――――――――――――――――

class Orchestrator:
    """Daemon central que coordina todo."""

    def __init__(self):
        load_config()
        self.state_path = config["orchestrator"]["state_db"]
        self.state = StateDB(self.state_path)
        self.bus = IPCBus(".", self.state)
        self.agents = AgentManager(self.state)
        self.running = True
        self.ws_clients: set = set()
        self.loop = asyncio.get_event_loop()

    async def start(self):
        log("info", "orchestrator", "Starting framework orchestrator",
            {"config": CONFIG_PATH})

        # Start WebSocket server
        ws_port = config["orchestrator"]["ws_port"]
        asyncio.create_task(self._ws_server(ws_port))

        # Start IPC poller
        asyncio.create_task(self._poll_inbox())

        # Start configured agents
        for name, cfg in config.get("agents", {}).items():
            cmd = cfg.get("command", "")
            if cmd:
                asyncio.create_task(self.agents.start_agent(
                    name, cmd, cfg.get("env")))

        # Health check loop
        asyncio.create_task(self._health_loop())

        log("info", "orchestrator", f"Running. WS on :{ws_port}, state in {self.state_path}")

        # Keep alive
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        finally:
            self.cleanup()

    async def _poll_inbox(self):
        """Periodically check for agent results and assign pending tasks."""
        poll_ms = config["orchestrator"]["poll_interval_ms"]
        while self.running:
            # Check all agents' outbox for results
            for agent_name in config.get("agents", {}):
                results = self.bus.read_results(agent_name)
                for result in results:
                    await self._on_agent_result(agent_name, result)

            # Assign pending tasks
            await self._assign_pending()

            # Broadcast state to WS clients
            if self.ws_clients:
                await self._broadcast_state()

            await asyncio.sleep(poll_ms / 1000)

    async def _on_agent_result(self, agent: str, result: dict):
        task_id = result.get("id", "")
        payload = result.get("payload", {})
        status = payload.get("status", "completed")

        log("info", "orchestrator", f"Result from {agent}: task={task_id} status={status}")

        # If task doesn't exist yet (came from direct inbox), create it
        existing = self.state.get_task(task_id)
        if not existing:
            self.state.save_task({
                "id": task_id,
                "agent": agent,
                "status": "assigned",
                "created_at": now_iso(),
                "payload": payload.get("output", {}),
            })

        # Update state
        self.state.update_task(task_id,
            status=status,
            result=json.dumps(payload.get("output")),
            completed_at=now_iso(),
            duration_ms=payload.get("duration_ms"),
        )

        # Notify WS clients
        await self._ws_broadcast({
            "event": "task_completed",
            "task_id": task_id,
            "agent": agent,
            "status": status,
        })

        # Check for fallback needs
        if status == "error" and payload.get("fallback_used"):
            log("info", "orchestrator", f"Fallback was used for {task_id}: {payload['fallback_used']}")

    async def _assign_pending(self):
        """Asigna tareas pendientes a agentes idle."""
        pending = self.state.get_pending_tasks()
        agents_status = {a["name"]: a["status"] for a in self.state.get_agents()}

        for task in pending[:5]:  # Batch de 5
            agent = task.get("agent", "")
            if agents_status.get(agent) in ("idle", None):
                # Send task via inbox
                self.bus.send_task(agent, task)
                self.state.update_task(task["id"],
                    status="assigned", started_at=now_iso())
                agents_status[agent] = "assigned"

                await self._ws_broadcast({
                    "event": "task_assigned",
                    "task_id": task["id"],
                    "agent": agent,
                    "action": task.get("action"),
                })

    # ── WebSocket Server ―――――――――――――――――――――――――

    async def _ws_server(self, port: int):
        try:
            import websockets
            async def handler(ws):
                self.ws_clients.add(ws)
                log("info", "ws", f"Client connected ({len(self.ws_clients)} total)")
                try:
                    # Send initial state
                    await ws.send(json.dumps({
                        "event": "connected",
                        "agents": self.state.get_agents(),
                        "tasks": self.state.get_pending_tasks(),
                    }))
                    async for msg in ws:
                        await self._handle_ws_message(ws, msg)
                except websockets.exceptions.ConnectionClosed:
                    pass
                finally:
                    self.ws_clients.discard(ws)
                    log("info", "ws", f"Client disconnected ({len(self.ws_clients)} total)")

            async with websockets.serve(handler, "0.0.0.0", port):
                log("info", "ws", f"WebSocket server on :{port}")
                await asyncio.Event().wait()
        except ImportError:
            log("warn", "ws", "websockets not installed — WS unavailable")
        except Exception as e:
            log("error", "ws", f"WS server error: {e}")

    async def _handle_ws_message(self, ws, raw: str):
        try:
            msg = json.loads(raw)
            cmd = msg.get("command", "")
            if cmd == "assign_task":
                self.bus.send_task(msg["agent"], {
                    "id": f"task_{uuid.uuid4().hex[:8]}",
                    "type": "task",
                    "agent": msg["agent"],
                    "timestamp": now_iso(),
                    "payload": {
                        "action": msg.get("action", ""),
                        "params": msg.get("params", {}),
                        "timeout_s": msg.get("timeout_s", 60),
                    }
                })
            elif cmd == "update_config":
                config["agents"].update(msg.get("agents", {}))
                log("info", "config", "Config updated via WS")
            elif cmd == "stop_agent":
                self.agents.stop_agent(msg["agent"])
            elif cmd == "start_agent":
                cfg = config["agents"].get(msg["agent"])
                if cfg:
                    await self.agents.start_agent(msg["agent"], cfg["command"], cfg.get("env"))
            elif cmd == "get_state":
                await ws.send(json.dumps({
                    "event": "state",
                    "agents": self.state.get_agents(),
                    "tasks": self.state.get_all_tasks(50),
                    "logs": self.state.get_logs(50),
                }))
            elif cmd == "get_logs":
                await ws.send(json.dumps({
                    "event": "logs",
                    "logs": self.state.get_logs(msg.get("limit", 100)),
                }))
        except json.JSONDecodeError:
            log("error", "ws", f"Invalid JSON from client")

    async def _ws_broadcast(self, data: dict):
        if not self.ws_clients:
            return
        msg = json.dumps(data)
        dead = set()
        for ws in self.ws_clients:
            try:
                await ws.send(msg)
            except Exception:
                dead.add(ws)
        self.ws_clients -= dead

    async def _broadcast_state(self):
        await self._ws_broadcast({
            "event": "heartbeat",
            "ts": now_iso(),
            "agents": self.state.get_agents(),
            "pending_tasks": len(self.state.get_pending_tasks()),
        })

    # ── Health Checks ――――――――――――――――――――――――――――

    async def _health_loop(self):
        while self.running:
            await asyncio.sleep(30)
            for name, proc in list(self.agents.processes.items()):
                if proc.poll() is not None:
                    log("warn", "health", f"{name} died, restarting...")
                    cfg = config["agents"].get(name, {})
                    if cfg.get("command"):
                        await self.agents.start_agent(name, cfg["command"], cfg.get("env"))

    # ── Public API (para usar desde otros módulos) ―――

    def enqueue_task(self, agent: str, action: str, params: dict | None = None,
                     priority: int = 0, parent_task: str = "", timeout_s: int = 60):
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = {
            "id": task_id,
            "type": "task",
            "agent": agent,
            "timestamp": now_iso(),
            "priority": priority,
            "created_at": now_iso(),
            "parent_task": parent_task,
            "payload": {
                "action": action,
                "params": params or {},
                "timeout_s": timeout_s,
            }
        }
        self.bus.send_task(agent, task)
        return task_id

    def cleanup(self):
        self.agents.stop_all()
        self.state.close()
        log("info", "orchestrator", "Shutdown complete")


# ── CLI ――――――――――――――――――――――――――――――――――――――――――

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--init":
        # Generate default config
        if not os.path.exists(CONFIG_PATH):
            os.makedirs(os.path.dirname(CONFIG_PATH) or ".", exist_ok=True)
            with open(CONFIG_PATH, "w") as f:
                f.write(yaml.dump(DEFAULT_CONFIG, default_flow_style=False))
            print(f"Config created at {CONFIG_PATH}")
        else:
            print(f"Config already exists at {CONFIG_PATH}")
        return

    orch = Orchestrator()
    try:
        asyncio.run(orch.start())
    except KeyboardInterrupt:
        log("info", "orchestrator", "Received SIGINT, shutting down...")
        orch.running = False
        orch.cleanup()


if __name__ == "__main__":
    main()
