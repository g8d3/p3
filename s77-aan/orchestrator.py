#!/usr/bin/env python3
"""
AAN Orchestrator — launches independent agent processes, watches for
pending tasks in the DB, tracks results. Runs continuously as a daemon.
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

POLL_INTERVAL = 3  # check for pending tasks every 3 seconds
MAX_AGENTS = 5     # max concurrent agents


def launch_agent_process(task, version_id):
    """Launch an agent_light.py process. Returns the subprocess PID."""
    agent_script = os.path.join(BASE, "agent_light.py")
    outfile = os.path.join(BASE, "agent-outputs", f"{version_id}.txt")
    os.makedirs(os.path.join(BASE, "agent-outputs"), exist_ok=True)

    # Explicitly set env vars from known paths
    env = os.environ.copy()
    secrets_file = os.path.expanduser("~/.secrets/.env")
    if os.path.exists(secrets_file):
        with open(secrets_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("export OPENCODE_GO_"):
                    parts = line.replace("export ", "", 1).split("=", 1)
                    if len(parts) == 2:
                        key, val = parts
                        val = val.strip("'\"")
                        env[key] = val

    log = open(outfile, "w")
    proc = subprocess.Popen(
        ["uv", "run", "python3", agent_script, task],
        stdout=log, stderr=subprocess.STDOUT,
        cwd=BASE, env=env,
    )
    return proc, outfile  # return process object, not just PID


def main():
    db = VersionRegistry()
    running = {}  # version_id -> (process, outfile, start_time)

    # Recover: mark any stuck "running" agents as "failed"
    for v in db.list_versions():
        work = db.get_version_work(v["id"])
        for w in work:
            if w.get("exit_status") == "running":
                db.update_version(v["id"], status="failed")
                print(f"  Recovered stuck: {v['id']}")

    print(f"Orchestrator started. Polling every {POLL_INTERVAL}s")
    print(f"Max concurrent agents: {MAX_AGENTS}")

    while True:
        # Check running agents
        for vid in list(running.keys()):
            proc_obj, outfile, start = running[vid]
            ret = proc_obj.poll()
            if ret is not None:
                status = "done" if ret == 0 else "failed"
                db.update_version(vid, status=status)
                db.record_work(vid, "builder", exit_status=status,
                               finished_at=datetime.now().isoformat())
                print(f"  {vid}: {status} (pid={proc_obj.pid}, exit={ret})")
                del running[vid]

        # Check for pending tasks (versions with status "draft")
        if len(running) < MAX_AGENTS:
            for v in db.list_versions():
                if v["status"] == "draft" and v["id"] not in running:
                    task = v.get("message", "")
                    if task:
                        proc, outfile = launch_agent_process(task, v["id"])
                        db.update_version(v["id"], status="running")
                        db.record_work(v["id"], "builder", input_spec=task, exit_status="running",
                                       started_at=datetime.now().isoformat())
                        running[v["id"]] = (proc, outfile, datetime.now())
                        print(f"  {v['id']}: launched (pid={proc.pid}) '{task[:50]}...'")
                        break

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOrchestrator stopped.")
