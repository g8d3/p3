#!/usr/bin/env python3
"""
Alpha Agent — A2A agent that acts as a research generalist.
Runs on port 9001.
Skills: research, summarize, analyze, delegate to specialists.
"""

import sys
import os
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from a2a_server import (
    create_server, TASKS, TASKS_LOCK, TERMINAL_STATES,
    complete_task, fail_task, set_task_state, TaskState,
    get_task_safe, AGENT_NAME, AGENT_PORT
)

AGENT_PORT = 9001
AGENT_NAME = "Alpha-Generalist"
AGENT_SKILLS = ["research", "summarize", "analyze", "delegate"]

# Simulated context memory (in production would use a DB)
CONTEXT_MEMORY = {}
CONTEXT_LOCK = threading.Lock()


def processor(task: dict):
    """Alpha's task processing logic."""
    msg = task["history"][0]["parts"][0]["text"]
    tid = task["id"]
    ctx_id = task.get("contextId", "")

    print(f"\n  [{AGENT_NAME}] Processing task {tid[:16]}...")
    print(f"  [{AGENT_NAME}] Message: {msg[:100]}")

    # Simulate thinking
    time.sleep(1.5)

    # Check context memory
    remembered = ""
    if ctx_id:
        with CONTEXT_LOCK:
            if ctx_id in CONTEXT_MEMORY:
                remembered = CONTEXT_MEMORY[ctx_id]
                print(f"  [{AGENT_NAME}] Found context: {remembered[:80]}")
            # Store new info (everything before "?")
            if "?" in msg:
                pass  # it's a question, don't store
            elif "my name is" in msg.lower():
                name = msg.lower().split("my name is")[-1].strip().strip(".!?")
                CONTEXT_MEMORY[ctx_id] = f"User's name is {name}"
                print(f"  [{AGENT_NAME}] Stored context: name={name}")
            elif "call me" in msg.lower():
                name = msg.lower().split("call me")[-1].strip().strip(".!?")
                CONTEXT_MEMORY[ctx_id] = f"User's name is {name}"
                print(f"  [{AGENT_NAME}] Stored context: name={name}")

    # Build response
    response_parts = [f"[{AGENT_NAME}] I've analyzed your request."]

    if remembered:
        response_parts.append(f"\n\nI remember: {remembered}")

    response_parts.append(f"\n\n### Research Summary")
    response_parts.append(f"Input: '{msg[:150]}'")
    response_parts.append(f"\nTask: {tid[:16]}")
    response_parts.append(f"\nContext: {ctx_id[:20] if ctx_id else 'none'}")
    response_parts.append("\n\n### Available Actions")
    response_parts.append("- Task lifecycle: submitted → working → completed")
    response_parts.append("- Cancellation supported via POST /tasks/{id}:cancel")
    response_parts.append("- No quality gate in A2A protocol")

    complete_task(tid, "\n".join(response_parts))
    print(f"  [{AGENT_NAME}] Task {tid[:16]} completed")


if __name__ == "__main__":
    server = create_server(AGENT_PORT, AGENT_NAME, AGENT_SKILLS,
                           processor=processor)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nAlpha shutting down...")
        server.shutdown()
