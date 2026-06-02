#!/usr/bin/env python3
"""
AAN Orchestrator — watches DB for pending tasks, launches agents
in visible tmux windows so the user sees real-time progress.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from version_registry import VersionRegistry

POLL_INTERVAL = 3


def tmux_launch_agent(task, version_id):
    """Launch agent_light.py in a visible tmux window."""
    agent_script = os.path.join(BASE, "agent_light.py")
    out_dir = os.path.join(BASE, "agent-outputs")
    os.makedirs(out_dir, exist_ok=True)
    outfile = os.path.join(out_dir, f"{version_id}.txt")

    # Write task to file to avoid shell escaping issues
    task_file = os.path.join(BASE, "agent-outputs", f"{version_id}.task")
    with open(task_file, "w") as f:
        f.write(task)

    wname = f"aan-{version_id}"
    done_signal = f"aan-{version_id}-done"
    win_cmd = (
        f'export OPENCODE_GO_API_KEY={os.environ.get("OPENCODE_GO_API_KEY","")}; '
        f'export OPENCODE_GO_BASE_URL={os.environ.get("OPENCODE_GO_BASE_URL","")}; '
        f'export OPENCODE_GO_MODEL={os.environ.get("OPENCODE_GO_MODEL","")}; '
        f'export AGENT_SYSTEM_PROMPT={os.environ.get("AGENT_SYSTEM_PROMPT","")}; '
        f'export AGENT_WORK_DIR={BASE}; '
        f'cd {BASE}; '
        f'uv run python3 {agent_script} "{task_file}" "{version_id}" 2>&1 | tee {outfile}; '
        f'echo; touch {outfile}.done; tmux wait-for -S {done_signal}; '
        f'echo "Press any key to close this window..."; read -n1'
    )
    subprocess.run(["tmux", "new-window", "-d", "-n", wname, "bash", "-c", win_cmd])
    return wname


def main():
    db = VersionRegistry()
    running_windows = {}  # version_id -> window_name

    print(f"Orchestrator started. Polling every {POLL_INTERVAL}s")

    while True:
        # Check for completed agents (.done files)
        for vid in list(running_windows.keys()):
            done_file = os.path.join(BASE, "agent-outputs", f"{vid}.txt.done")
            if os.path.exists(done_file):
                db.update_version(vid, status="done")
                db.record_work(vid, "builder", exit_status="done",
                               finished_at=datetime.now().isoformat())
                print(f"  {vid}: done")
                os.remove(done_file)
                del running_windows[vid]

        # Check for pending tasks (versions with status "draft")
        for v in db.list_versions():
            if v["status"] == "draft" and v["id"] not in running_windows:
                task = v.get("message", "")
                if not task:
                    continue
                wname = tmux_launch_agent(task, v["id"])
                db.update_version(v["id"], status="running")
                db.record_work(v["id"], "builder", input_spec=task,
                               exit_status="running",
                               started_at=datetime.now().isoformat())
                running_windows[v["id"]] = wname
                print(f"  {v['id']}: launched in tmux window '{wname}'")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOrchestrator stopped.")
