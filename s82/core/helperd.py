"""
helperd — Cooperative reflex daemon with OODA loop.

OBSERVE → ORIENT → DECIDE → ACT → VERIFY

1. OBSERVE: check proxy health + tmux state + heartbeat
2. ORIENT: escalation level based on attempt history
3. DECIDE: nudge, interrupt, kill, or escalate
4. ACT: execute the action
5. VERIFY: check if agent recovered; if not, try DIFFERENT action
"""
import json, os, subprocess, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(BASE))

from core.config import PROXY_HEALTH, BUS_DIR, STUCK_AFTER, POLL_INTERVAL

LOG_FILE = BASE / "data" / "helperd.log"
PID_FILE = BASE / "data" / "helperd.pid"

# Synthetic agents that should never be monitored
SYNTHETIC_AGENTS = ("agent-", "supervisor-test", "python", "zsh", "git", "[tmux]", "mimo")


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def proxy_agents():
    try:
        data = json.loads(urllib.request.urlopen(PROXY_HEALTH, timeout=5).read())
        return data.get("agents", {})
    except:
        return {}


def tmux_capture(target):
    try:
        r = subprocess.run(["tmux", "capture-pane", "-t", str(target), "-p"],
                          capture_output=True, text=True, timeout=3)
        return r.stdout or ""
    except:
        return ""


def tmux_send(target, keys):
    try:
        subprocess.run(["tmux", "send-keys", "-t", str(target), keys],
                       timeout=2, capture_output=True)
    except:
        pass


def write_bus(target, msg):
    inbox = Path(BUS_DIR) / target / "in"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / f"helperd-{int(time.time()*1000)}").write_text(msg)


class Helperd:
    def __init__(self):
        self.cycle = 0
        self.attempts = {}  # agent -> list of timestamps and actions
        self.cooldowns = {}  # agent -> timestamp of last action
        log("Helperd started (OODA mode)")

    def _cooldown(self, agent, seconds=180):
        last = self.cooldowns.get(agent, 0)
        return (time.time() - last) < seconds

    def _is_synthetic(self, name):
        return name.startswith(SYNTHETIC_AGENTS)

    def _observe(self, name, info):
        """OBSERVE: gather all data about an agent's state."""
        state = {
            "name": name,
            "never_active": info.get("never_active", True),
            "idle": info.get("idle", False),
            "last_s": info.get("last_s", 999),
            "tmux_output": "",
            "at_prompt": False,
            "has_stuck_cmd": False,
            "stuck_cmd": "",
        }
        if state["never_active"]:
            return state

        # Capture tmux pane for real state
        pane = tmux_capture(name)
        state["tmux_output"] = pane

        if pane:
            lines = pane.split("\n")
            last_lines = [l.strip().removeprefix("┃").strip() for l in lines[-8:]]
            # Check if at prompt
            for line in last_lines:
                if line in ("", ">", "$") or line.endswith(("$", "#", ">")):
                    state["at_prompt"] = True
                    break
            if "::: " in pane[-50:]:
                state["at_prompt"] = True
            # Check for stuck command (not at prompt, idle for a while)
            if not state["at_prompt"] and state["last_s"] > STUCK_AFTER:
                for line in last_lines:
                    if line and not any(c in line for c in ("┃", "╹", "⬝", "■", "●", "Build", "esc", "ctrl+p")):
                        state["has_stuck_cmd"] = True
                        state["stuck_cmd"] = line[:120]
                        break
        return state

    def _verify_recovery(self, name):
        """VERIFY: check if agent recovered after help."""
        info = proxy_agents().get(name, {})
        if not info or info.get("never_active", True):
            return False
        last_s = info.get("last_s", 0)
        # Recovered if active in last 30 seconds
        return last_s < 30

    def _ooda_cycle(self, name, info):
        """Full OODA loop for one agent."""
        # OBSERVE
        state = self._observe(name, info)

        # Skip: synthetic agents, never active, or at prompt (normal state)
        if state["never_active"] or self._is_synthetic(name) or state["at_prompt"]:
            return

        # ORIENT: determine if really stuck
        if not state["has_stuck_cmd"] and state["last_s"] < STUCK_AFTER * 2:
            return  # Not stuck enough to warrant action

        # Check cooldown
        if self._cooldown(name):
            return

        # Get attempt history
        history = self.attempts.get(name, [])
        attempt_count = len([h for h in history if h["resolved"] is False])

        # ORIENT: determine escalation level
        if attempt_count >= 3:
            # ESCALATED: skip to avoid spam, log it
            log(f"ESCALATED {name}: {attempt_count} intentos fallidos")
            self.cooldowns[name] = time.time() + 3600  # 1h cooldown
            return

        # DECIDE + ACT based on level
        help_id = f"h{int(time.time())}"
        action_taken = ""

        if attempt_count == 0:
            # Level 1: gentle nudge via bus message
            log(f"L1 {name}: nudge")
            peers = [k for k, v in proxy_agents().items()
                     if not v.get("never_active", True)
                     and not self._is_synthetic(k)
                     and k != name
                     and not self._cooldown(k)]
            if peers:
                peers.sort(key=lambda n: proxy_agents()[n].get("last_s", 999))
                peer = peers[0]
                write_bus(peer,
                    f"[HELPERD] {name} seems stuck ({state['last_s']}s). "
                    f"Can you check? Window: {name}")
                action_taken = f"asked {peer} to check"
            else:
                # No peer available, send Escape directly
                tmux_send(name, "Escape")
                action_taken = "escape (no peer)"

        elif attempt_count == 1:
            # Level 2: direct Escape + message
            log(f"L2 {name}: interrupt")
            tmux_send(name, "Escape")
            time.sleep(0.3)
            tmux_send(name, Escape)
            action_taken = "escape"

        elif attempt_count == 2:
            # Level 3: kill + fresh prompt
            log(f"L3 {name}: kill command")
            tmux_send(name, "Escape")
            time.sleep(0.5)
            tmux_send(name, "echo '⚠️ Comando interrumpido por timeout. Continua.'")
            tmux_send(name, "Enter")
            action_taken = "kill+prompt"

        # Record attempt
        record = {
            "help_id": help_id,
            "level": attempt_count + 1,
            "action": action_taken,
            "last_s": state["last_s"],
            "stuck_cmd": state["stuck_cmd"][:80],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resolved": False,
        }
        if name not in self.attempts:
            self.attempts[name] = []
        self.attempts[name].append(record)

        # Save to help-acks.json for dashboard
        acks_file = BASE / "data" / "help-acks.json"
        acks = json.loads(acks_file.read_text()) if acks_file.exists() else {}
        if name not in acks:
            acks[name] = []
        acks[name].append(record)
        acks_file.write_text(json.dumps(acks, indent=2))

        self.cooldowns[name] = time.time()
        log(f"HELP {name} L{attempt_count+1}: {action_taken}")

    def _verify_all(self, agents):
        """VERIFY: check all unresolved attempts and mark resolved if recovered."""
        for name, attempts in list(self.attempts.items()):
            unresolved = [a for a in attempts if not a["resolved"]]
            if not unresolved:
                continue
            if self._verify_recovery(name):
                for a in unresolved:
                    a["resolved"] = True
                    a["resolved_at"] = datetime.now(timezone.utc).isoformat()
                log(f"RESOLVED {name}: {len(unresolved)} attempts closed")
                # Also update help-acks.json
                acks_file = BASE / "data" / "help-acks.json"
                if acks_file.exists():
                    acks = json.loads(acks_file.read_text())
                    if name in acks:
                        for a in acks[name]:
                            if not a.get("resolved"):
                                a["resolved"] = True
                                a["resolved_at"] = a["resolved_at"] if "resolved_at" in a else datetime.now(timezone.utc).isoformat()
                        acks_file.write_text(json.dumps(acks, indent=2))

    def run(self):
        while True:
            self.cycle += 1
            agents = proxy_agents()
            if not agents:
                time.sleep(POLL_INTERVAL)
                continue

            # OODA for each agent
            for name, info in sorted(agents.items()):
                try:
                    self._ooda_cycle(name, info)
                except Exception as e:
                    log(f"Error {name}: {e}")

            # VERIFY: check resolutions
            self._verify_all(agents)

            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "foreground"
    if cmd == "foreground":
        Helperd().run()
    elif cmd == "--once":
        h = Helperd()
        agents = proxy_agents()
        if agents:
            for name, info in sorted(agents.items()):
                h._ooda_cycle(name, info)
            h._verify_all(agents)
    else:
        print("Usage: helperd.py [foreground|--once]")
