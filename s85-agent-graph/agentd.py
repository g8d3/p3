#!/usr/bin/env python3
"""
agentd.py — Watchdog daemon.
Only: heartbeat, health check, spawn workers for tasks, generate curiosity tasks when idle.
"""
import json, os, random, signal, subprocess, sys, time, traceback, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(BASE))
from graph.core import Graph
import needs as needs_mod

DB_PATH = str(BASE / "data" / "agent-graph.db")
POLL_INTERVAL = 30
AGENT_ID = "agentd"


class Watchdog:
    def __init__(self):
        self.g = Graph(DB_PATH)
        self.g.set_agent(AGENT_ID)
        self.cycle = 0
        self.started = datetime.now(timezone.utc)
        self.g.add_node("agent", "agentd",
            {"type": "watchdog", "pid": os.getpid(), "started_at": self.started.isoformat()},
            node_id="agentd", agent_id=AGENT_ID)

    def p(self, msg): print(msg, flush=True)

    def _heartbeat(self):
        hb = {"pid": os.getpid(), "cycle": self.cycle,
              "timestamp": datetime.now(timezone.utc).isoformat(),
              "uptime_s": int((datetime.now(timezone.utc) - self.started).total_seconds())}
        (BASE / "data" / "heartbeat").write_text(json.dumps(hb))

    def cycle_once(self):
        self.cycle += 1
        cid = f"c{self.cycle}"
        self._heartbeat()
        self.p(f"[agentd] cycle {cid}")

        # Resource check
        try:
            mf = needs_mod.write_needs_manifest(needs_mod.check_resources())
        except Exception as e:
            self.p(f"[agentd] needs error: {e}")
            mf = {"critical_count": 0, "needs": []}
        self.g.log("heartbeat", cid)

        if mf.get("critical_count", 0) > 0:
            for n in mf["needs"]:
                if n.get("priority") == "critical":
                    self.p(f"[agentd] CRITICAL: {n['resource']} — {n['message'][:100]}")
                    self.g.add_node("error", f"critical: {n['resource']}", n, agent_id=AGENT_ID)
            return  # don't do anything until critical needs are resolved

        # Hunt hanging registered processes only
        self._hunt_zombies()

        # Pending tasks?
        tasks = self.g.pending_tasks()
        if tasks:
            # Spawn workers for ALL pending tasks (parallel, fire-and-forget)
            for task in tasks[:3]:  # max 3 parallel
                self.p(f"[agentd] spawning worker for: {task['name'][:60]}")
                subprocess.Popen(
                    [sys.executable, str(BASE / "worker.py")],
                    stdout=open(BASE / "data" / f"worker-{task['id'][:8]}.log", "w"),
                    stderr=subprocess.STDOUT,
                )
        else:
            self.p("[agentd] idle — generating curiosity tasks")
            self._curiosity()

    def _hunt_zombies(self):
        """Find and kill hanging operations and zombie processes."""
        hanging = self.g.check_hanging()
        if not hanging:
            return
        import signal as _signal
        self.p(f"[agentd] 🎯 {len(hanging)} hanging ops")
        for h in hanging[:5]:
            name = h.get("name", "?")
            op_id = h["id"]
            pid = h.get("pid") or h.get("properties", {}).get("pid")
            killed = False
            if pid:
                try:
                    os.kill(int(pid), _signal.SIGKILL)
                    self.p(f"  ✕ killed PID {pid} ({name})")
                    killed = True
                except (ProcessLookupError, PermissionError, OSError):
                    pass
            # Mark as killed in graph
            self.g.add_node("error", f"killed: {name}",
                {"op_id": op_id, "pid": pid, "killed": killed, "killed_by": "agentd"},
                agent_id=AGENT_ID)
            self.g.add_edge(op_id, "killed", op_id, {}, agent_id=AGENT_ID)
            self.g.log(AGENT_ID, "zombie_killed", "op", str(op_id),
                       "ok" if killed else "not_found",
                       f"killed PID {pid} ({name})" if killed else f"PID {pid} not found ({name})")
            # Mark ops as killed so check_hanging ignores it next cycle
            try:
                self.g.conn.execute("UPDATE ops SET status='killed' WHERE id=?", (op_id,))
                self.g.conn.commit()
            except Exception as ex:
                self.p(f"  ! ops update failed: {ex}")

    def _curiosity(self):
        """When idle, scan the graph for gaps and generate new tasks."""
        with self.g.op("curiosity", timeout_s=30):
            stats = self.g.stats()
            ideas = []

            # 1. Projects without deep scan?
            projects = self.g.query_nodes("project")
            scanned_projects = set()
            for a in self.g.query_nodes("artifact"):
                parts = a["name"].split("/")
                if parts[0]:
                    scanned_projects.add(parts[0])
            unscanned = [p for p in projects if p["name"] not in scanned_projects]
            if unscanned:
                target = random.choice(unscanned[:5])
                ideas.append(f"Deep scan project {target['name']} for source code and configs")

            # 2. Projects with few connections?
            for p in projects[:20]:
                edges = self.g.get_edges(source_id=p["id"])
                if len(edges) < 3:
                    ideas.append(f"Explore connections for {p['name']} — only {len(edges)} edges")
                    break

            # 3. Any type missing?
            for ntype in ["skill", "decision", "lesson"]:
                if stats["nodes_by_type"].get(ntype, 0) == 0:
                    ideas.append(f"Create {ntype} nodes from existing projects")

            # 4. Propose next project? (check if s86 exists)
            next_dir = Path("/home/vuos/code/p3/s86")
            if not next_dir.exists():
                ideas.append("Propose and create next project (s86) — what should it do?")

            if not ideas:
                ideas.append("Run full system audit and generate improvement suggestions")

            for idea in ideas[:2]:
                self.g.add_node("task", idea, {"source": "curiosity"}, agent_id=AGENT_ID)
                self.p(f"  + {idea[:100]}")

    def run(self):
        self.p(f"[agentd] start (PID={os.getpid()})")
        stale = BASE / "data" / "heartbeat.ts"
        if stale.exists():
            age = time.time() - float(stale.read_text().strip())
            if age > POLL_INTERVAL * 4:
                self.p(f"[agentd] previous instance crash ({age:.0f}s old)")
                self.g.log("stale_heartbeat", f"{age:.0f}s", "warning")
                self.g.add_node("error", "previous daemon crashed",
                    {"age_s": age}, agent_id=AGENT_ID)
        while True:
            try:
                self.cycle_once()
            except Exception as e:
                self.p(f"[agentd] crash: {e}")
                traceback.print_exc()
                self.g.log("crash", str(e)[:100], "error")
            time.sleep(POLL_INTERVAL)


# ── Control ──
PID_FILE = BASE / "data" / "agentd.pid"
LOG_FILE = BASE / "data" / "agentd.log"

def start():
    if PID_FILE.exists():
        pid = PID_FILE.read_text().strip()
        if Path(f"/proc/{pid}").exists():
            print(f"agentd ya corre (PID={pid})"); return
        PID_FILE.unlink()
    pid = os.fork()
    if pid == 0:
        os.setsid()
        sys.stdout = open(LOG_FILE, "w"); sys.stderr = sys.stdout
        Watchdog().run()
    else:
        PID_FILE.write_text(str(pid))
        print(f"agentd started (PID={pid})")

def stop():
    if not PID_FILE.exists(): print("agentd not running"); return
    try:
        os.kill(int(PID_FILE.read_text()), 15); PID_FILE.unlink(); print("agentd stopped")
    except: PID_FILE.unlink(); print("agentd stopped (stale)")

def status():
    alive = PID_FILE.exists() and Path(f"/proc/{PID_FILE.read_text().strip()}").exists()
    print(f"agentd: {'🟢 VIVO' if alive else '🔴 MUERTO'}")
    hf = BASE / "data" / "heartbeat"
    if hf.exists():
        hd = json.loads(hf.read_text())
        print(f"  ciclos: {hd['cycle']}, uptime: {hd['uptime_s']}s")
    nf = BASE / "needs.json"
    if nf.exists():
        d = json.loads(nf.read_text())
        print(d["summary"])

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "once"
    {
        "start": start, "stop": stop, "status": status,
        "once": lambda: Watchdog().cycle_once(),
        "foreground": lambda: Watchdog().run(),
    }.get(cmd, lambda: print("start|stop|status|once|foreground"))()
