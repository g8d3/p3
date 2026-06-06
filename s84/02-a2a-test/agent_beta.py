#!/usr/bin/env python3
"""
Beta Agent — A2A agent that acts as a specialist (code review, quality check).
Runs on port 9002.
Skills: code-review, validate, test, quality-check
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from a2a_server import (
    create_server, TASKS, TASKS_LOCK, TERMINAL_STATES,
    complete_task, fail_task, set_task_state, TaskState,
    get_task_safe
)

AGENT_PORT = 9002
AGENT_NAME = "Beta-Quality"
AGENT_SKILLS = ["code-review", "validate", "test", "quality-check"]

# Keywords that trigger quality rejection
REJECTION_TRIGGERS = ["bug", "error", "wrong", "broken", "fail", "bad code"]


def processor(task: dict):
    """Beta's quality-check processing."""
    msg = task["history"][0]["parts"][0]["text"]
    tid = task["id"]

    print(f"\n  [{AGENT_NAME}] Validating task {tid[:16]}...")
    print(f"  [{AGENT_NAME}] Input: {msg[:100]}")

    time.sleep(0.8)

    # Simulate quality check
    found_triggers = [t for t in REJECTION_TRIGGERS if t in msg.lower()]

    if found_triggers:
        response = (
            f"[{AGENT_NAME}] ❌ Quality check FAILED.\n\n"
            f"### Issues Found\n"
            f"- Problematic keywords detected: {found_triggers}\n"
            f"- No explicit acceptance criteria\n\n"
            f"### Note\n"
            f"A2A protocol has no standard 'quality gate' state.\n"
            f"The task state is still '{TaskState.COMPLETED}' even for rejections.\n"
            f"Quality information is embedded in the artifact text, not in the protocol."
        )
    else:
        response = (
            f"[{AGENT_NAME}] ✅ Quality check PASSED.\n\n"
            f"### Validation Results\n"
            f"- Input format: OK\n"
            f"- No problematic keywords\n"
            f"- Task appears well-formed\n\n"
            f"### A2A Limitation Noted\n"
            f"This check is custom logic. The A2A protocol itself\n"
            f"has no concept of quality gates or acceptance criteria."
        )

    complete_task(tid, response)
    print(f"  [{AGENT_NAME}] Task {tid[:16]} {'rejected' if found_triggers else 'approved'}")


if __name__ == "__main__":
    server = create_server(AGENT_PORT, AGENT_NAME, AGENT_SKILLS,
                           processor=processor)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBeta shutting down...")
        server.shutdown()
