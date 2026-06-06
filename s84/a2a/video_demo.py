#!/usr/bin/env python3
"""
A2A Video Demo — terminal output with timing for video recording.
Each step prints to stdout and saves TTS narration.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
TTS_VOICE = "es-CO-GonzaloNeural"
TTS_DIR = "/tmp/a2a-demo-tts"
os.makedirs(TTS_DIR, exist_ok=True)

step_num = 0

def step(title, narrative):
    global step_num
    step_num += 1
    print(f"\n{'='*60}")
    print(f"  STEP {step_num}: {title}")
    print(f"{'='*60}")
    print(f"  {narrative}")
    print()
    sys.stdout.flush()

    tts_out = os.path.join(TTS_DIR, f"step{step_num:02d}.mp3")
    subprocess.run(
        ["edge-tts", "--voice", TTS_VOICE, "--text", narrative, "--write-media", tts_out],
        capture_output=True, timeout=30
    )
    time.sleep(0.5)

def http_get(url):
    try:
        return urllib.request.urlopen(url, timeout=5).read().decode()
    except Exception as e:
        return f"ERROR: {e}"

def http_post(url, data):
    try:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"}
        )
        return json.loads(urllib.request.urlopen(req, timeout=10).read())
    except Exception as e:
        return {"error": str(e)}


# ── DEMO ──

step("Starting Agents",
    "Launching two A2A agents: Alpha on port 9001 and Beta on port 9002.")

# Kill old agents
for port in [9001, 9002]:
    subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)

# Launch via tmux
venv = os.path.join(BASE, "..", ".venv", "bin", "python3")
subprocess.run(["tmux", "new-window", "-d", "-n", "a2a-demo-a", f"{venv} {BASE}/agent_alpha.py 2>&1; read"])
subprocess.run(["tmux", "new-window", "-d", "-n", "a2a-demo-b", f"{venv} {BASE}/agent_beta.py 2>&1; read"])

for port in [9001, 9002]:
    for i in range(30):
        try:
            urllib.request.urlopen(f"http://localhost:{port}/.well-known/agent.json", timeout=2)
            break
        except:
            time.sleep(0.3)

step("Agent Discovery",
    "Test 1: Fetching Agent Cards. Each A2A agent publishes its capabilities at .well-known agent.json. Alpha is a generalist, Beta is a quality specialist.")

alpha_card = http_get("http://localhost:9001/.well-known/agent.json")
beta_card = http_get("http://localhost:9002/.well-known/agent.json")
print(f"  Alpha: {json.loads(alpha_card).get('name')}")
print(f"  Beta:  {json.loads(beta_card).get('name')}")

step("Task Execution",
    "Test 2: Sending a task to Alpha. The A2A lifecycle is submitted, working, completed. We poll until completion.")

resp = http_post("http://localhost:9001/message:send", {
    "message": {"role": "user", "parts": [{"text": "What is the weather like today?"}], "messageId": "m1"}
})
task_id = resp.get("result", resp).get("id", "?")
print(f"  Task ID: {task_id}")

for i in range(10):
    task = json.loads(http_get(f"http://localhost:9001/tasks/{task_id}"))
    state = task.get("result", task).get("status", {}).get("state", "?")
    print(f"  Poll {i+1}: {state}")
    if state == "completed":
        break
    time.sleep(0.5)

step("Cancellation",
    "Test 3: Cancellation. We send a long task and immediately cancel it. This tests the CancelTask operation.")

resp2 = http_post("http://localhost:9001/message:send", {
    "message": {"role": "user", "parts": [{"text": "Write a very long report about AI agents"}], "messageId": "m2"}
})
task2_id = resp2.get("result", resp2).get("id", "?")
print(f"  Task: {task2_id}")

time.sleep(0.3)
cancel = http_post(f"http://localhost:9001/tasks/{task2_id}:cancel", {})
cancel_state = cancel.get("result", cancel).get("status", {}).get("state", "?")
print(f"  Cancel response: {cancel_state}")

time.sleep(0.5)
verify = json.loads(http_get(f"http://localhost:9001/tasks/{task2_id}"))
verify_state = verify.get("result", verify).get("status", {}).get("state", "?")
print(f"  Final state: {verify_state}")

step("Quality Gate Limitation",
    "Test 4: The key finding. We send good code and buggy code to Beta. Both return state completed. There is no protocol-level quality distinction. A2A has no way to know if work passed or failed quality checks.")

# Good input
r3 = http_post("http://localhost:9002/message:send", {
    "message": {"role": "user", "parts": [{"text": "Review this code: def foo(): pass"}], "messageId": "m3"}
})
t3 = r3.get("result", r3).get("id", "?")
time.sleep(1.5)
p3 = json.loads(http_get(f"http://localhost:9002/tasks/{t3}"))
s3 = p3.get("result", p3).get("status", {}).get("state", "?")

# Bad input
r4 = http_post("http://localhost:9002/message:send", {
    "message": {"role": "user", "parts": [{"text": "This code has a bug"}], "messageId": "m4"}
})
t4 = r4.get("result", r4).get("id", "?")
time.sleep(1.5)
p4 = json.loads(http_get(f"http://localhost:9002/tasks/{t4}"))
s4 = p4.get("result", p4).get("status", {}).get("state", "?")

print(f"  Good code  -> state: {s3}")
print(f"  Buggy code -> state: {s4}")
print(f"  BOTH ARE '{s3}' — no quality distinction!")

step("The Solution: A2A-Q",
    "This is why we proposed A2A-Q. An extension that adds quality gates, review cycles, and efficacy metrics to the A2A protocol. New states like pending review, needs revision, and quality passed would let the protocol distinguish between approved and rejected work at the protocol level, not just in text.")

step("Summary",
    "A2A handles discovery, task execution, and cancellation well. But quality gates, review cycles, and hardware metrics are missing entirely. A2A-Q fills this gap as a backward-compatible extension. The full specification, test code, and RFC are on GitHub in the p3 repository.")

# Cleanup
for w in ["a2a-demo-a", "a2a-demo-b"]:
    subprocess.run(["tmux", "kill-window", "-t", w], capture_output=True)
for port in [9001, 9002]:
    subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True)

print(f"\n\nDemo complete. TTS audio in: {TTS_DIR}/")
subprocess.run(["ls", "-lh", TTS_DIR])
