#!/usr/bin/env python3
"""AAN Orchestrator — launches agents, tracks their work, reports status."""
import json
import os
import subprocess
import threading
import time
from datetime import datetime

AGENT_DIR = os.path.dirname(os.path.abspath(__file__))

class Agent:
    def __init__(self, agent_type, task, version_id):
        self.agent_type = agent_type  # "builder", "validator", "explorer"
        self.task = task
        self.version_id = version_id
        self.status = "pending"  # pending → running → done | failed
        self.started_at = None
        self.finished_at = None
        self.output_file = os.path.join(AGENT_DIR, f"agent-{version_id}-{agent_type}.txt")
        self.pid = None

    def launch(self):
        self.status = "running"
        self.started_at = datetime.now().isoformat()
        done_file = self.output_file + ".done"

        def _run():
            try:
                result = subprocess.run(
                    ["uv", "run", "python3", os.path.join(AGENT_DIR, "agent_light.py"), self.task],
                    capture_output=True, text=True, timeout=300,
                    cwd=AGENT_DIR
                )
                output = result.stdout or result.stderr or "no output"
                with open(self.output_file, "w") as f:
                    f.write(output)
                self.status = "done" if result.returncode == 0 else "failed"
            except subprocess.TimeoutExpired:
                with open(self.output_file, "w") as f:
                    f.write("TIMEOUT: agent exceeded 300s")
                self.status = "failed"
            except Exception as e:
                with open(self.output_file, "w") as f:
                    f.write(f"ERROR: {e}")
                self.status = "failed"
            self.finished_at = datetime.now().isoformat()
            open(done_file, "w").close()

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return self


class Orchestrator:
    def __init__(self):
        self.agents = []
        self._lock = threading.Lock()

    def launch_agent(self, agent_type, task, version_id):
        agent = Agent(agent_type, task, version_id)
        agent.launch()
        with self._lock:
            self.agents.append(agent)
        return agent

    def get_status(self):
        with self._lock:
            return [{
                "type": a.agent_type,
                "task": a.task[:80],
                "version": a.version_id,
                "status": a.status,
                "started": a.started_at,
                "finished": a.finished_at,
            } for a in self.agents]

    def get_running(self):
        return [a for a in self.agents if a.status == "running"]
