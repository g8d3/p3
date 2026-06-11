"""
helperd — Cooperative reflex daemon.

Closes the loop: when agent B is stuck/idle, helperd
automatically asks agent A (nearest active peer) to help.

The reflex:
  1. Poll proxy health → detect stuck/idle agents
  2. Query graph DB → find best peer to help
  3. Write help request to busd inbox → peer agent
  4. Record help event in graph DB
  5. Monitor for resolution → confirm or escalate
"""
import json, os, subprocess, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(BASE))

from core.config import (
    PROXY_HEALTH, BUS_DIR, STUCK_AFTER, IDLE_AFTER,
    POLL_INTERVAL, HELP_COOLDOWN, AGENT_WINDOWS
)


def parse_agent_windows(raw: str) -> dict[int, str]:
    result = {}
    for part in raw.split(","):
        part = part.strip()
        if ":" in part:
            win, name = part.split(":", 1)
            result[int(win.strip())] = name.strip()
    return result


WINDOW_NAMES = parse_agent_windows(AGENT_WINDOWS)


def proxy_agents() -> dict:
    try:
        data = json.loads(urllib.request.urlopen(PROXY_HEALTH, timeout=5).read())
        return data.get("agents", {})
    except Exception as e:
        print(f"[helperd] proxy error: {e}", flush=True)
        return {}


def find_peer_to_help(stuck_name: str, agents: dict) -> str | None:
    candidates = [n for n in agents if n != stuck_name and not agents[n].get("never_active", True)]
    if not candidates:
        return None
    candidates.sort(key=lambda n: agents[n].get("last_s", 999))
    return candidates[0]


def tmux_send(window: int | str, msg: str):
    try:
        subprocess.run(["tmux", "send-keys", "-t", str(window), msg, "Enter"],
                       timeout=5)
    except Exception:
        pass


def tmux_capture(window: int | str) -> str:
    try:
        r = subprocess.run(["tmux", "capture-pane", "-t", str(window), "-p"],
                           capture_output=True, text=True, timeout=3)
        return r.stdout or ""
    except Exception:
        return ""


def write_bus_message(target: str, msg: str, trace_id: str = ""):
    inbox = Path(BUS_DIR) / target / "in"
    inbox.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    fname = f"helperd-{ts}"
    if trace_id:
        fname += f"--{trace_id}"
    (inbox / fname).write_text(msg)


def append_log(entry: dict):
    logfile = BASE / "data" / "helperd.log"
    with open(logfile, "a") as f:
        f.write(json.dumps(entry) + "\n")


class Helperd:
    def __init__(self):
        self.cycle = 0
        self.last_help: dict[str, float] = {}
        self.started = datetime.now(timezone.utc)
        self.help_history: dict[str, list[dict]] = {}
        self.ack_file = BASE / "data" / "help-acks.json"
        self._load_acks()
        print(f"[helperd] start (PID={os.getpid()})", flush=True)

    def _load_acks(self):
        if self.ack_file.exists():
            try:
                self.help_history = json.loads(self.ack_file.read_text())
            except Exception:
                self.help_history = {}

    def _save_acks(self):
        self.ack_file.write_text(json.dumps(self.help_history, indent=2))

    def _on_cooldown(self, agent: str) -> bool:
        last = self.last_help.get(agent, 0)
        return (time.time() - last) < HELP_COOLDOWN

    def cycle_once(self):
        self.cycle += 1
        agents = proxy_agents()
        if not agents:
            return

        now = time.time()

        for name, info in agents.items():
            if info.get("never_active", True):
                continue
            if name.startswith(("agent-", "supervisor", "watcher")):
                continue  # skip synthetic/daemon agents

            last_s = info.get("last_s", 999)
            is_idle = info.get("idle", False)

            if is_idle and last_s > IDLE_AFTER and not self._on_cooldown(name):
                self._reflex_help(name, agents, "idle", last_s)

            if last_s > STUCK_AFTER and not is_idle and not self._on_cooldown(name):
                self._reflex_help(name, agents, "stuck", last_s)

        self._check_resolved_helps(agents)

    def _reflex_help(self, stuck_name: str, agents: dict, reason: str, last_s: int):
        peer = find_peer_to_help(stuck_name, agents)
        if not peer:
            append_log({"cycle": self.cycle, "event": "no_peer",
                        "stuck": stuck_name, "reason": reason})
            return

        help_id = f"help-{int(time.time())}"
        window = None
        for w, n in WINDOW_NAMES.items():
            if n == peer:
                window = w
                break

        context = tmux_capture(window) if window else ""
        last_lines = context.strip().split("\n")[-5:] if context else []
        context_snippet = "; ".join(l.strip() for l in last_lines if l.strip())[:200]

        msg_lines = [
            f"[HELPERD] {stuck_name} seems {reason} ({last_s}s without activity).",
            f"Can you check on them? Window: {stuck_name}",
        ]
        if context_snippet:
            msg_lines.append(f"Recent activity from {peer}: {context_snippet}")
        msg = "\n".join(msg_lines)

        write_bus_message(peer, msg, trace_id=help_id)
        self.last_help[stuck_name] = time.time()

        if stuck_name not in self.help_history:
            self.help_history[stuck_name] = []
        self.help_history[stuck_name].append({
            "help_id": help_id,
            "peer": peer,
            "reason": reason,
            "last_s": last_s,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resolved": False,
        })
        self._save_acks()

        append_log({
            "cycle": self.cycle, "event": "help_sent",
            "help_id": help_id, "stuck": stuck_name,
            "peer": peer, "reason": reason, "last_s": last_s
        })
        print(f"[helperd] {help_id}: asked {peer} to help {stuck_name} ({reason}, {last_s}s)", flush=True)

    def _check_resolved_helps(self, agents: dict):
        for stuck_name, helps in list(self.help_history.items()):
            unresolved = [h for h in helps if not h.get("resolved")]
            if not unresolved:
                continue

            info = agents.get(stuck_name, {})
            last_s = info.get("last_s", 999)
            never = info.get("never_active", True)

            if never or last_s < STUCK_AFTER:
                for h in unresolved:
                    h["resolved"] = True
                    h["resolved_at"] = datetime.now(timezone.utc).isoformat()
                self._save_acks()
                for h in unresolved:
                    append_log({
                        "cycle": self.cycle, "event": "help_resolved",
                        "help_id": h["help_id"],
                        "stuck": stuck_name, "peer": h["peer"]
                    })
                print(f"[helperd] {stuck_name} recovered — marking helps resolved", flush=True)

    def run(self):
        while True:
            try:
                self.cycle_once()
            except Exception as e:
                print(f"[helperd] crash: {e}", flush=True)
                import traceback
                traceback.print_exc()
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "foreground"
    if cmd == "foreground":
        Helperd().run()
    elif cmd == "once":
        Helperd().cycle_once()
    else:
        print("Usage: python3 core/helperd.py [foreground|once]")
