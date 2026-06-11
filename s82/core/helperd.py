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

        # ── OODA: OBSERVE ──
        # Coordinator heartbeat check
        hb_file = BASE / "data" / "coordinator.heartbeat"
        if hb_file.exists():
            try:
                hb_age = now - hb_file.stat().st_mtime
                if hb_age > 300 and not self._on_cooldown("coordinator"):
                    self.last_help["coordinator"] = now
                    # OODA: OBSERVE → check if coordinator is really stuck
                    pane = tmux_capture(0)
                    stuck_cmd = ""
                    for line in pane.split("\n")[-10:]:
                        s = line.strip()
                        if s and not s.startswith(("┃", "╹", "⬝", "■", "●")):
                            stuck_cmd = s[:120]
                    # OODA: ACT
                    try:
                        subprocess.run(["tmux", "send-keys", "-t", "0", "Escape"],
                                       timeout=2, capture_output=True)
                        subprocess.run(["tmux", "send-keys", "-t", "0",
                                       f"echo '[SISTEMA] Coordinador parece estar trabado ({int(hb_age)}s sin heartbeat). Comando: {stuck_cmd}. Continuando...'",
                                       "Enter"], timeout=2, capture_output=True)
                        append_log({
                            "cycle": self.cycle, "event": "coordinator_unstick",
                            "heartbeat_age_s": int(hb_age), "last_cmd": stuck_cmd,
                        })
                        print(f"[helperd] coordinator unstick (hb_age={int(hb_age)}s cmd={stuck_cmd[:50]})", flush=True)
                    except Exception as e:
                        print(f"[helperd] coordinator unstick failed: {e}", flush=True)
            except Exception:
                pass

        for name, info in agents.items():
            # OODA: OBSERVE — skip synthetic agents that never recover
            if info.get("never_active", True):
                continue
            if name.startswith(("agent-", "supervisor", "supervisor-test", "watcher")):
                continue

            last_s = info.get("last_s", 999)
            is_idle = info.get("idle", False)

            # OODA: ORIENT — check if truly stuck (not just thinking)
            out = tmux_capture(name) if last_s > STUCK_AFTER else ""
            at_prompt = False
            stuck_cmd = ""
            if out:
                for line in out.split("\n")[-8:]:
                    s = line.strip().removeprefix("┃").strip()
                    if s in ("", ">", "$") or s.endswith(("$", "#", ">")):
                        at_prompt = True
                    elif s and not s.startswith(("┃", "╹", "⬝", "■", "●", "Build", "esc")):
                        stuck_cmd = s[:100]
            at_idle_prompt = "::: " in out[-50:] if out else False

            # OODA: DECIDE — skip if agent is just at idle prompt (normal)
            if at_prompt or at_idle_prompt:
                continue

            # OODA: ACT — but only if not recently helped and truly stuck
            if last_s > STUCK_AFTER and not is_idle and not self._on_cooldown(name):
                self._reflex_ooda(name, agents, "stuck", last_s, stuck_cmd)

        # OODA: VERIFY — check if previous helps resolved
        self._check_resolved_helps(agents)

    def _reflex_ooda(self, stuck_name: str, agents: dict, reason: str, last_s: int, stuck_cmd: str = ""):
        """
        OODA loop for unsticking agents:
        1. OBSERVE: already done (cycle_once checks state)
        2. ORIENT: determine escalation level
        3. DECIDE: what action to take
        4. ACT: execute the action
        5. VERIFY: next cycle will check if resolved
        """
        # ORIENT: how many times have we tried to help this agent?
        history = self.help_history.get(stuck_name, [])
        recent_attempts = [h for h in history if not h.get("resolved")]
        attempt_count = len(recent_attempts)

        # ESCALATION: different actions based on attempt count
        if attempt_count == 0:
            # Level 1: Nudge — send a gentle check message
            peer = find_peer_to_help(stuck_name, agents)
            if not peer:
                return
            action = f"ask {peer} to check"
            msg = f"[HELPERD] {stuck_name} seems stuck ({last_s}s). Can you check on them?"
            write_bus_message(peer, msg, trace_id=f"help-{int(time.time())}")
            print(f"[helperd] L1: asked {peer} to check {stuck_name}", flush=True)

        elif attempt_count == 1:
            # Level 2: Direct interrupt
            action = "tmux send-keys Escape"
            try:
                subprocess.run(["tmux", "send-keys", "-t", stuck_name, "Escape"],
                               timeout=2, capture_output=True)
            except: pass
            print(f"[helperd] L2: sent Escape to {stuck_name}", flush=True)

        elif attempt_count == 2:
            # Level 3: Kill stuck command + fresh prompt
            action = "interrupt + new prompt"
            try:
                subprocess.run(["tmux", "send-keys", "-t", stuck_name, "Escape"],
                               timeout=2, capture_output=True)
                time.sleep(0.5)
                subprocess.run(["tmux", "send-keys", "-t", stuck_name, "echo '💥 Comando interrumpido. Continúa con tu tarea.'", "Enter"],
                               timeout=2, capture_output=True)
            except: pass
            print(f"[helperd] L3: interrupt + fresh prompt to {stuck_name}", flush=True)

        else:
            # Level 4+: Escalate to system — log and skip (avoid infinite spam)
            action = f"escalated (>{attempt_count} attempts)"
            append_log({"cycle": self.cycle, "event": "escalated",
                        "stuck": stuck_name, "attempts": attempt_count})
            print(f"[helperd] L4: {stuck_name} escalated after {attempt_count} attempts", flush=True)
            self.last_help[stuck_name] = time.time() + 3600  # don't retry for an hour
            return

        # Record the attempt
        help_id = f"help-{int(time.time())}"
        if stuck_name not in self.help_history:
            self.help_history[stuck_name] = []
        self.help_history[stuck_name].append({
            "help_id": help_id,
            "action": action,
            "reason": reason,
            "last_s": last_s,
            "stuck_cmd": stuck_cmd[:100],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resolved": False,
        })
        self.last_help[stuck_name] = time.time()
        self._save_acks()

        append_log({"cycle": self.cycle, "event": "ooda_act",
                    "help_id": help_id, "stuck": stuck_name,
                    "action": action, "level": attempt_count + 1})

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
