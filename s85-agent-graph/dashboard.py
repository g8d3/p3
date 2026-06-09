#!/usr/bin/env python3
"""
dashboard.py — Web UI using Nimbo models. Auto-CRUD for graph tables + custom routes.
"""
import json, os, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(os.path.dirname(os.path.abspath(__file__)))
NIMBO_PATH = Path("/home/vuos/code/p3/s84/nimbo")
sys.path.insert(0, str(NIMBO_PATH))

from nimbo import App, Response
from graph.core import Graph

DB_PATH = str(BASE / "data" / "agent-graph.db")
g = Graph(DB_PATH)

app = App("agent-dashboard", db_url=f"sqlite:///{DB_PATH}", static_dir=str(BASE / "static"))

# ── Graph tables as Nimbo models → auto CRUD, filters, sort, web UI ──

# Note: nimbo auto-adds 'id' column. Don't declare it in models.
@app.model(table="graph_node")
class Node:
    type: str = ""
    name: str = ""
    properties: str = ""
    created_at: str = ""
    updated_at: str = ""
    agent_id: str = ""

@app.model(table="graph_edge")
class Edge:
    source_id: str = ""
    target_id: str = ""
    type: str = ""
    properties: str = ""
    created_at: str = ""
    agent_id: str = ""

@app.model(table="graph_log")
class AgentLog:
    agent_id: str = ""
    action: str = ""
    target_type: str = ""
    target_id: str = ""
    result: str = "ok"
    detail: str = ""
    created_at: str = ""

# ── Custom routes for system-level features ──

@app.route("/api/stats")
async def stats(req):
    return g.stats()

@app.route("/api/operators")
async def api_operators(req):
    hb_file = BASE / "data" / "heartbeat"
    pid_file = BASE / "data" / "agentd.pid"
    agents = []
    now = datetime.now(timezone.utc)

    # 1. agentd (watchdog daemon)
    daemon_alive = False
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            daemon_alive = Path(f"/proc/{pid}").exists()
        except: pass
    hb_data = {}
    if hb_file.exists():
        try: hb_data = json.loads(hb_file.read_text())
        except: pass
    if daemon_alive:
        agents.append({
            "name": "agentd", "type": "watchdog",
            "pid": hb_data.get("pid", ""), "uptime_s": hb_data.get("uptime_s", 0),
            "cycles": hb_data.get("cycle", 0), "status": "running",
            "task": "monitoring system",
            "last_seen": hb_data.get("timestamp", ""), "stuck": False,
        })

    # 2. Running agents from graph nodes
    for a in g.query_nodes(type="agent"):
        props = a.get("properties", {})
        name = a.get("name", "?")
        if name == "agentd": continue
        pid = props.get("pid", "")
        alive = False
        if pid:
            alive = Path(f"/proc/{pid}").exists()
        agents.append({
            "name": name, "type": props.get("type", "agent"),
            "pid": pid, "uptime_s": props.get("uptime_s", 0),
            "status": "running" if alive else "registered",
            "task": props.get("purpose", ""),
            "last_seen": a.get("created_at", ""),
            "stuck": False,
        })

    # 3. Running OS processes (workers, run.py, etc.)
    for proc_label, proc_pattern in [("worker", "worker.py"), ("run", "run.py")]:
        try:
            r = subprocess.run(["pgrep", "-f", proc_pattern], capture_output=True, text=True, timeout=5)
            for pid in r.stdout.strip().split("\n"):
                if not pid: continue
                # check if already in list
                if any(a.get("pid") == pid for a in agents): continue
                agents.append({
                    "name": proc_label, "type": "process",
                    "pid": pid, "uptime_s": 0, "status": "running",
                    "task": "executing", "last_seen": "", "stuck": False,
                })
        except: pass

    # 4. Me (opencode agent)
    recent_me = g.get_log(limit=5)
    if recent_me:
        last_ts = recent_me[0].get("created_at", "")
        agents.append({
            "name": "opencode-agent", "type": "conversational",
            "pid": os.getpid(), "uptime_s": 0, "status": "active",
            "task": "responding to human", "last_seen": last_ts, "stuck": False,
            "unstuck_method": "send new message or Ctrl+C",
        })

    # 5. Hanging / stuck operations
    hanging = g.check_hanging()
    for h in hanging[:5]:
        for a in agents:
            if a.get("pid") and str(a["pid"]) == str(h.get("pid", "")):
                a["stuck"] = True
                a["stuck_reason"] = f"op '{h['name']}' exceeded timeout"
                a["stuck_since"] = h.get("started_at", "")
        agents.append({
            "name": f"zombie: {h['name']}", "type": "zombie",
            "pid": h.get("pid", ""), "uptime_s": 0, "status": "stuck",
            "task": h.get("name", "?"),
            "last_seen": str(h.get("started_at", "")),
            "stuck": True, "stuck_reason": "timeout exceeded",
            "stuck_since": h.get("started_at", ""),
            "unstuck_method": "SIGKILL (agentd) or manual kill",
        })

    return agents

@app.route("/api/processes")
async def api_processes(req):
    """Return info about processes being watched."""
    import subprocess as _sp
    try:
        r = _sp.run(["ps", "-eo", "pid,ppid,cmd,etime:1", "--sort=start_time"],
                    capture_output=True, text=True, timeout=10)
        lines = r.stdout.strip().split("\n")[1:]
        procs = []
        for line in lines:
            parts = line.strip().split(None, 3)
            if len(parts) < 4: continue
            pid, ppid, cmd, etime = parts
            procs.append({"pid": pid, "ppid": ppid, "cmd": cmd[:80], "etime": etime,
                          "watched": True})
        return procs
    except Exception as e:
        return {"error": str(e)}

@app.route("/api/log")
async def api_log(req):
    return g.get_log(limit=50)

@app.route("/api/ops")
async def api_ops(req):
    return g.recent_ops(limit=30)

@app.route("/api/tasks")
async def tasks(req):
    return g.pending_tasks()

@app.route("/api/needs")
async def needs(req):
    nf = BASE / "needs.json"
    if nf.exists():
        return json.loads(nf.read_text())
    return {"error": "needs.json not found"}

@app.route("/api/health")
async def health(req):
    hb_file = BASE / "data" / "heartbeat"
    hb_data = {}
    if hb_file.exists():
        try: hb_data = json.loads(hb_file.read_text())
        except: pass
    pid_file = BASE / "data" / "agentd.pid"
    daemon = False
    if pid_file.exists():
        try:
            daemon = Path(f"/proc/{pid_file.read_text().strip()}").exists()
        except: pass
    return {"daemon_alive": daemon, "heartbeat": hb_data, "stats": g.stats()}

@app.route("/api/timeline")
async def timeline(req):
    ops = g.recent_ops(limit=100)
    points = []
    for i, op in enumerate(reversed(ops)):
        points.append({"nodes": i + 1, "t": str(op.get("started_at", ""))[:19]})
    return {"points": points, "current": g.count_nodes()}

@app.route("/api/graph")
async def graph(req):
    return {"nodes": g.query_nodes(), "edges": g.get_edges()}

@app.route("/api/search")
async def search(req):
    q = req.query.get("q", [""])[0]
    return g.search_nodes(q) if q else []

@app.route("/api/control/add-task", methods=["POST"])
async def add_task(req):
    body = req.json
    name = body.get("name", "task")
    nid = g.add_node("task", name, body.get("properties", {}), agent_id="human")
    return {"ok": True, "id": nid}

@app.route("/api/control/run-worker", methods=["POST"])
async def run_worker(req):
    try:
        r = subprocess.run([sys.executable, str(BASE / "worker.py")],
                          capture_output=True, text=True, timeout=120)
        return {"ok": r.returncode == 0, "exit": r.returncode,
                "stdout": r.stdout[-500:], "stderr": r.stderr[-500:]}
    except subprocess.TimeoutExpired:
        return Response({"error": "timeout"}, 504)

@app.route("/api/control/unstuck", methods=["POST"])
async def unstuck(req):
    """Unstuck an agent by PID. Method depends on agent type."""
    body = req.json
    pid = body.get("pid", "")
    agent_type = body.get("agent_type", "process")
    if not pid:
        return Response({"error": "pid required"}, 400)
    try:
        pid_int = int(pid)
        if agent_type == "conversational":
            # For me (opencode): can't kill via API, but log the request
            g.log("human", "unstuck_request", "agent", str(pid), "info",
                  f"requested unstuck for conversational agent PID {pid}")
            return {"ok": True, "method": "request_sent", "note": "conversational agent needs human interaction (new message or Ctrl+C)"}
        elif agent_type == "watchdog":
            # agentd: SIGTERM (graceful), it will restart via start command
            os.kill(pid_int, 15)
            g.log("human", "unstuck", "agent", str(pid), "ok", f"SIGTERM to watchdog PID {pid}")
            return {"ok": True, "method": "SIGTERM"}
        else:
            # process or zombie: SIGKILL
            try:
                os.kill(pid_int, 9)
                g.log("human", "unstuck", "agent", str(pid), "ok", f"SIGKILL to PID {pid}")
                return {"ok": True, "method": "SIGKILL"}
            except ProcessLookupError:
                return {"ok": True, "method": "already_dead"}
    except Exception as e:
        return Response({"error": str(e)}, 500)

# ── Serve ──

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9092
    print(f"[dashboard] http://localhost:{port}")
    print(f"[dashboard] Nimbo models: node, edge, agent_log (+ custom routes)")
    app.serve(host="0.0.0.0", port=port, system=False)
