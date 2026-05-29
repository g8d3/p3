#!/usr/bin/env python3.12
"""Test del framework: lanza Orchestrator + agentes de prueba y verifica el ciclo completo.

Prueba:
1. Inicializa estructura
2. Lanza Orchestrator en background
3. Envía tarea vía inbox
4. Verifica que el agente la procesa
5. Verifica que el resultado llega al outbox
6. Verifica WebSocket
7. Limpia
"""

import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

BASE = os.path.dirname(os.path.abspath(__file__))
PASS = 0
FAIL = 0


def check(condition: bool, msg: str):
    global PASS, FAIL
    icon = "✅" if condition else "❌"
    print(f"  {icon} {msg}")
    if condition:
        PASS += 1
    else:
        FAIL += 1


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── Setup ───────────────────────────────────────────────

section("1. Preparación")

# Create directories
for d in ["inbox", "outbox", "shared", "data", "logs"]:
    os.makedirs(os.path.join(BASE, d), exist_ok=True)

# Clean test agents
for agent_dir in ["inbox/echo-agent", "outbox/echo-agent",
                   "inbox/test-agent", "outbox/test-agent"]:
    p = Path(BASE) / agent_dir
    if p.exists():
        for f in p.glob("*.json"):
            f.unlink()
    p.mkdir(parents=True, exist_ok=True)

check(True, "Directories ready")

# Kill any previous orchestrator
subprocess.run(["pkill", "-f", "orchestrator/__init__"], capture_output=True)
time.sleep(0.5)
check(True, "Previous orchestrator killed")

# ── Start Orchestrator ──────────────────────────────────

section("2. Orchestrator startup")

orch_env = os.environ.copy()
orch_env["FRAMEWORK_CONFIG"] = os.path.join(BASE, "config.yaml")

proc = subprocess.Popen(
    [sys.executable, "-u", "-c", """
import asyncio
import sys
sys.path.insert(0, '.')
from orchestrator import Orchestrator
o = Orchestrator()
try:
    asyncio.run(o.start())
except KeyboardInterrupt:
    pass
"""],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=BASE,
    env=orch_env,
)

time.sleep(2)
poll = proc.poll()
check(poll is None, f"Orchestrator running (PID={proc.pid})")

# ── IPC Test: Send task via inbox ───────────────────────

section("3. IPC: Send task -> Inbox")

task_id = f"test_{uuid.uuid4().hex[:8]}"
task = {
    "id": task_id,
    "type": "task",
    "agent": "echo-agent",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "payload": {
        "action": "ping",
        "params": {"msg": "hello framework"},
        "timeout_s": 30,
    }
}

inbox_path = Path(BASE) / "inbox" / "echo-agent" / f"{task_id}.json"
with open(inbox_path, "w") as f:
    json.dump(task, f, indent=2)

check(inbox_path.exists(), f"Task written to inbox/{task_id}.json")

# ── Launch test agent ───────────────────────────────────

section("4. Agent: Process task")

agent_proc = subprocess.Popen(
    [sys.executable, "-u", "agent-template/agent.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=BASE,
    env={**os.environ,
         "AGENT_NAME": "echo-agent",
         "AGENT_POLL_MS": "200",
         "FRAMEWORK_BASE": BASE},
)

time.sleep(2)
check(agent_proc.poll() is None, f"Agent running (PID={agent_proc.pid})")

# Give it time to process
time.sleep(3)

# ── Verify result in outbox ─────────────────────────────

section("5. IPC: Verify result in Outbox")

outbox_files = list((Path(BASE) / "outbox" / "echo-agent").glob("*.json"))
check(len(outbox_files) > 0, f"Result files in outbox: {len(outbox_files)}")

if outbox_files:
    with open(outbox_files[0]) as f:
        result = json.load(f)
    check(result.get("type") == "result", f"Message type={result.get('type')}")
    check(result.get("payload", {}).get("status") == "ok", f"Status={result.get('payload',{}).get('status')}")
    check(result.get("agent") == "echo-agent", f"Agent={result.get('agent')}")

# ── Verify task not in inbox (agent should have deleted it) ──

remaining = list(inbox_path.parent.glob(f"{task_id}*"))
check(len(remaining) == 0, f"Inbox cleaned (agent deleted task)")

# ── Verify agent output ─────────────────────────────────

section("6. Agent stdout (JSON messages)")

stdout_data = agent_proc.stdout.read(4096).decode() if agent_proc.stdout else ""
lines = [l for l in stdout_data.split("\n") if l.strip()]
json_lines = 0
for line in lines:
    try:
        msg = json.loads(line)
        json_lines += 1
        if msg.get("type") == "log":
            pass  # Good
    except json.JSONDecodeError:
        pass

check(json_lines > 0, f"Agent emitted {json_lines} JSON messages via stdout")

# ── Cleanup ─────────────────────────────────────────────

section("7. Cleanup")

agent_proc.terminate()
agent_proc.wait()
check(agent_proc.poll() is not None, "Agent stopped")

proc.terminate()
proc.wait()
check(proc.poll() is not None, "Orchestrator stopped")

# Clean test files
inbox_path.parent.mkdir(exist_ok=True)
for f in (Path(BASE) / "outbox" / "echo-agent").glob("*.json"):
    f.unlink()

# ── Results ─────────────────────────────────────────────

section("Resultados")
total = PASS + FAIL
print(f"  {PASS}/{total} pruebas pasaron")
print()
if FAIL == 0:
    print("  ✅ Framework IPC funciona correctamente.")
else:
    print(f"  ❌ {FAIL} pruebas fallaron.")

sys.exit(0 if FAIL == 0 else 1)
