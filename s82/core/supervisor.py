#!/usr/bin/env python3
"""
supervisor.py — Autonomous supervisor agent.

Runs every 5s, monitors system, takes corrective action.
Uses deterministic rules for common cases (idle→task, stuck→help).
Only calls LLM for novel situations to save tokens.

Capabilities:
  - Assign tasks to idle workers (no more wasted capacity)
  - Restart dead components
  - Detect stuck agents and coordinate peer help
  - Track system state and report to graph DB

Usage:
  python3 core/supervisor.py           # normal mode (5s loop)
  python3 core/supervisor.py --once    # single cycle
"""
import json, os, subprocess, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(BASE))

from core.graph import Graph
from core.config import PROXY_HEALTH, BUS_DIR, STUCK_AFTER

LLM_ENDPOINT = "http://localhost:9098/v1/chat/completions"
MODEL = os.environ.get("OPENCODE_GO_MODEL", "deepseek-v4-flash")

PID_FILE = BASE / "data" / "supervisor.pid"
LOG_FILE = BASE / "data" / "supervisor.log"
CYCLE_INTERVAL = 5

# Track state changes to avoid redundant LLM calls
_last_agent_state = ""
_llm_call_cycle = 0


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def proxy_agents() -> dict:
    try:
        data = json.loads(urllib.request.urlopen(PROXY_HEALTH, timeout=5).read())
        return data.get("agents", {})
    except Exception as e:
        log(f"Proxy: {e}")
        return {}


def pid_alive(pidfile: str) -> bool:
    pf = Path(pidfile)
    if not pf.exists():
        return False
    try:
        pid = int(pf.read_text().strip())
        return Path(f"/proc/{pid}").exists()
    except (ValueError, OSError):
        return False


BUS_SCRIPT = str(Path(os.environ.get("AGENTS_DIR", "~/.agents")) / "skills/orquestar-agentes/scripts/busd")

def write_bus_message(target: str, msg: str):
    inbox = Path(BUS_DIR) / target / "in"
    inbox.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    fname = inbox / f"supervisor-{ts}"
    fname.write_text(msg)
    # Also try direct tmux delivery as fallback
    try:
        subprocess.run(["tmux", "send-keys", "-t", target, "Escape"],
                       timeout=2, capture_output=True)
        subprocess.run(["tmux", "send-keys", "-t", target, msg, "Enter"],
                       timeout=2, capture_output=True)
    except Exception:
        pass

_busd_started = False

def ensure_busd():
    """Start busd once. Only one attempt."""
    global _busd_started
    if _busd_started:
        return
    # Check existing PID
    busd_pid_file = Path(BUS_DIR) / "busd.pid"
    if busd_pid_file.exists():
        try:
            pid = int(busd_pid_file.read_text().strip())
            if pid > 0 and Path(f"/proc/{pid}").exists():
                _busd_started = True
                return
        except (ValueError, OSError):
            pass
    busd_script = Path(os.path.expanduser("~/.agents/skills/orquestar-agentes/scripts/busd"))
    if not busd_script.exists():
        log("busd script not found")
        _busd_started = True  # don't keep trying
        return
    try:
        p = subprocess.Popen(
            ["bash", str(busd_script)],
            stdout=open(Path(BUS_DIR) / "busd-out.log", "w"),
            stderr=subprocess.STDOUT,
        )
        busd_pid_file.write_text(str(p.pid))
        _busd_started = True
        log(f"busd started (PID={p.pid})")
    except Exception as e:
        log(f"busd start failed: {e}")
        _busd_started = True


def call_llm(prompt: str) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You manage a multi-agent system. Respond with ACTION: <action>. Keep it short."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 512,
        "temperature": 0.1,
    }
    try:
        api_key = os.environ.get("OPENCODE_GO_API_KEY", "")
        req = urllib.request.Request(
            LLM_ENDPOINT, data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "s82-supervisor/1.0",
                "X-Agent-ID": "supervisor",
            },
        )
        r = urllib.request.urlopen(req, timeout=30)
        data = json.loads(r.read())
        content = data["choices"][0]["message"].get("content", "")
        if not content:
            content = data["choices"][0]["message"].get("reasoning_content", "")
        return content
    except Exception as e:
        log(f"LLM error: {e}")
        return ""


def extract_action(text: str) -> str:
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("ACTION:"):
            return line.replace("ACTION:", "").strip()
    return ""


class Supervisor:
    def __init__(self):
        self.cycle = 0
        self.g = Graph()
        self.g.set_agent("supervisor")
        self.g.register_agent("supervisor", {"type": "daemon", "purpose": "supervisor"})
        log("Started")

    def restart_component(self, name: str):
        scripts = {
            "helperd": (["python3", str(BASE / "core/helperd.py"), "foreground"],
                        str(BASE / "data/helperd.pid")),
            "dashboard": (["python3", str(BASE / "web/server.py")],
                          str(BASE / "data/dashboard.pid")),
            "proxy": (["python3", str(BASE / "../s84/proxy/proxy_watchdog.py")],
                      str(BASE / "data/proxy.pid")),
        }
        if name not in scripts:
            return
        cmd, pf = scripts[name]
        log(f"Restarting {name}...")
        try:
            out = BASE / "data" / f"{name}-out.log"
            p = subprocess.Popen(cmd, stdout=open(out, "w"), stderr=subprocess.STDOUT)
            Path(pf).write_text(str(p.pid))
            log(f"{name} restarted (PID={p.pid})")
        except Exception as e:
            log(f"{name} restart failed: {e}")

    def pending_messages(self, target: str) -> bool:
        inbox = Path(BUS_DIR) / target / "in"
        if not inbox.exists():
            return False
        return len(list(inbox.glob("supervisor-*"))) > 0

    def assign_task(self, worker: str):
        if self.pending_messages(worker):
            return
        tasks = [
            "Run `ls -R /home/vuos/code/p3/s82/` and report back what files exist in the system.",
            "Check the proxy health at http://localhost:9098/health and summarize what agents are active.",
            "Run `tail -20 /home/vuos/code/p3/s82/data/supervisor.log` and tell me what the supervisor has been doing.",
            "Read LEARNINGS.md in s82 and suggest one improvement to the system.",
            "Check if there are any hanging processes with `ps aux | grep defunct`.",
        ]
        task = tasks[self.cycle % len(tasks)]
        msg = f"[TASK] {task}\n\nWhen done, say 'done' and I'll get you another task."
        write_bus_message(worker, msg)
        log(f"Task → {worker}: {task[:80]}...")

    def cycle_once(self):
        global _last_agent_state, _llm_call_cycle
        self.cycle += 1

        # Ensure inbox dirs exist (so busd can watch them)
        for agent in ["worker-1", "worker-2", "watcher", "a1", "a2", "a3"]:
            (Path(BUS_DIR) / agent / "in").mkdir(parents=True, exist_ok=True)

        ensure_busd()

        agents = proxy_agents()
        if not agents:
            return

        # ── 1. Health checks (always) ──
        if not pid_alive(str(BASE / "data/helperd.pid")):
            self.restart_component("helperd")
        if not pid_alive(str(BASE / "data/dashboard.pid")):
            self.restart_component("dashboard")

        # ── 2. Categorize agents ──
        workers = []
        stuck = []
        idle = []
        for name, info in agents.items():
            if info.get("never_active", True):
                continue
            last_s = info.get("last_s", 999)
            if last_s > 120 and name.startswith("worker-"):
                idle.append(name)
            elif last_s > STUCK_AFTER:
                stuck.append(name)
            else:
                workers.append(name)

        # ── 3. Rule-based actions ──

        # 3a. Assign tasks to idle workers
        for w in idle:
            self.assign_task(w)

        # 3b. Help stuck agents via peer (only real worker agents, not daemons)
        real_agents = [n for n in agents
                       if not n.startswith(("agent-", "supervisor"))
                       and not agents[n].get("never_active", True)]
        for s in stuck:
            if s.startswith(("agent-", "supervisor")):
                continue  # skip synthetic/detected agents
            peers = [p for p in real_agents if p != s and not self.pending_messages(p)]
            if peers:
                write_bus_message(peers[0],
                    f"[HELPERD] {s} seems stuck ({agents[s].get('last_s',0)}s). Can you check?"
                )
                log(f"Help: {peers[0]} → {s}")

        # ── 4. LLM for novel situations (every 10 cycles = 50s) ──
        state_sig = json.dumps(
            {k: {"s": v.get("status"), "l": v.get("last_s"),
                 "n": v.get("never_active")}
             for k, v in sorted(agents.items())},
            sort_keys=True
        )
        state_changed = state_sig != _last_agent_state
        _last_agent_state = state_sig

        if state_changed and self.cycle - _llm_call_cycle >= 30:
            _llm_call_cycle = self.cycle
            prompt = (
                "System state:\n" + json.dumps({
                    "agents": {k: {"last_s": v.get("last_s"), "idle": v.get("idle"),
                                   "never_active": v.get("never_active")}
                               for k, v in agents.items()},
                }, indent=2) + "\n\n"
                "Rules I already handle automatically: idle workers get tasks, stuck agents get peer help.\n"
                "What else should I do? Options:\n"
                "- 'ok' — nothing unusual\n"
                "- 'explore <project>' — investigate a project\n"
                "- 'fix <desc>' — something needs fixing\n"
                "- 'note <insight>' — record a finding in LEARNINGS\n"
            )
            decision = call_llm(prompt)
            action = extract_action(decision)
            if action and action != "ok":
                log(f"LLM decided: {action}")
                if action.startswith("fix "):
                    write_bus_message("a1", f"[TASK] Fix: {action[4:]}")
                elif action.startswith("note "):
                    self.g.add_node("note", action[5:], {"source": "supervisor", "cycle": self.cycle})

        self.g.log("supervisor", "cycle", "", str(self.cycle),
                    "ok", f"{len(agents)} agents, {len(idle)} idle, {len(stuck)} stuck")

    def run(self):
        while True:
            try:
                self.cycle_once()
            except Exception as e:
                log(f"Crash: {e}")
                import traceback
                traceback.print_exc(file=open(LOG_FILE, "a"))
            time.sleep(CYCLE_INTERVAL)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "foreground"
    if cmd == "foreground":
        Supervisor().run()
    elif cmd == "--once":
        Supervisor().cycle_once()
    else:
        print("Usage: supervisor.py [foreground|--once]")
