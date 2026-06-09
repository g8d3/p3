#!/usr/bin/env python3
"""
worker.py — One-shot task executor.
Reads a task from the graph, reasons with LLM, executes, writes back.
Can be spawned in parallel: `python3 worker.py` picks the oldest task.
"""
import json, os, subprocess, sys, time, traceback, urllib.request, urllib.error
from pathlib import Path

BASE = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(BASE))
from graph.core import Graph

DB_PATH = str(BASE / "data" / "agent-graph.db")
LLM_URL = os.environ.get("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1/")
LLM_KEY = os.environ.get("OPENCODE_GO_API_KEY", "")
LLM_MODEL = os.environ.get("OPENCODE_GO_MODEL", "deepseek-v4-flash")


def llm(prompt: str, timeout: int = 90) -> str:
    if not LLM_KEY:
        return "NO_API_KEY"
    payload = {"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}],
               "max_tokens": 4096, "temperature": 0.3}
    req = urllib.request.Request(LLM_URL + "chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {LLM_KEY}"})
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(r.read())["choices"][0]["message"]["content"]
    except Exception as e:
        return f"LLM_ERROR: {e}"


class Worker:
    def __init__(self, graph: Graph):
        self.g = graph
        self.g.set_agent("worker")

    def pick_task(self) -> dict | None:
        tasks = self.g.pending_tasks()
        # prefer tasks that haven't been tried before
        for t in tasks:
            edges = self.g.get_edges(source_id=t["id"])
            attempts = [e for e in edges if e["type"].startswith("failed_")]
            if not attempts:
                return t
        # all tasks have been tried; pick the one with fewest failures
        if tasks:
            return tasks[0]
        return None

    def gather_context(self, task: dict) -> str:
        lines = [f"Graph: {self.g.count_nodes()} nodes, {len(self.g.query_nodes('project'))} projects"]
        related = self.g.search_nodes(task["name"][:40])
        for r in related[:5]:
            lines.append(f"Found: [{r['type']}] {r['name']}")
        log = self.g.get_log(limit=5)
        for l in log:
            lines.append(f"Log: {l['agent_id']} {l['action']} {l['result']}")
        # Pending tasks
        pending = self.g.pending_tasks()
        lines.append(f"Pending tasks: {len(pending)}")
        for p in pending[:3]:
            lines.append(f"  - {p['name']}")
        # Stats by type
        stats = self.g.stats()
        for t, c in stats.get("nodes_by_type", {}).items():
            lines.append(f"  {t}: {c}")
        return "\n".join(lines)

    def reason(self, task: dict, context: str) -> str:
        prompt = f"""You are an autonomous worker agent. Your shared knowledge graph records everything.

PENDING TASK: {task['name']}
PROPERTIES: {json.dumps(task['properties'], indent=2)}
ID: {task['id']}

CURRENT GRAPH STATE:
{context}

Your job: decide ONE action and respond with exactly one of:

EXECUTE: <shell command>
  Run any command. Use this for: scanning files, creating directories, writing code,
  running analysis, moving files. You have FULL access to the terminal.

GRAPH: <description>
  Add a new task or node to the graph for another agent to handle.

ASK_HUMAN: <question>
  You're stuck or need a decision.

DEFER: <reason>
  Not now, but don't forget.

Examples of good EXECUTE commands:
- EXECUTE: find /home/vuos/code/p3/s84 -name '*.py' -type f | head -30
- EXECUTE: mkdir -p /home/vuos/code/p3/s86-new-project && echo '# New project' > /home/vuos/code/p3/s86-new-project/README.md
- EXECUTE: python3 -c "import os; [print(f) for f in os.listdir('/home/vuos/code/p3/s84')]"

Prefer EXECUTE over other options. Be specific and practical."""
        return llm(prompt)

    def run_decision(self, decision: str, task: dict):
        task_id = task["id"]
        d = decision.strip()

        if d.startswith("EXECUTE:"):
            cmd = d[len("EXECUTE:"):].strip().strip("`").strip()
            print(f"[worker] $ {cmd[:120]}")
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                ok = r.returncode == 0
                self.g.add_node("artifact", f"out-{task_id[:8]}",
                    {"command": cmd, "stdout": r.stdout[-1000:], "stderr": r.stderr[-1000:],
                     "returncode": r.returncode}, agent_id="worker")
                if ok:
                    self.g.add_edge(task_id, "completed", task_id, {}, agent_id="worker")
                    print(f"[worker] ok (exit={r.returncode})")
                else:
                    self.g.add_edge(task_id, "failed_exec", task_id, {}, agent_id="worker")
                    print(f"[worker] fail (exit={r.returncode})")
            except subprocess.TimeoutExpired:
                self.g.add_edge(task_id, "failed_timeout", task_id, {}, agent_id="worker")
                print("[worker] timeout")
            except Exception as e:
                self.g.add_edge(task_id, "failed_error", task_id, {}, agent_id="worker")
                print(f"[worker] error: {e}")

        elif d.startswith("GRAPH:"):
            desc = d[len("GRAPH:"):].strip()
            self.g.add_node("task", desc, {"source": "worker"}, agent_id="worker")
            self.g.add_edge(task_id, "completed", task_id, {}, agent_id="worker")
            print(f"[worker] spawned task: {desc[:80]}")

        elif d.startswith("ASK_HUMAN:"):
            q = d[len("ASK_HUMAN:"):].strip()
            self.g.add_node("question", q, {"task_id": task_id}, agent_id="worker")
            self.g.add_edge(task_id, "waiting_human", task_id, {}, agent_id="worker")
            print(f"[worker] waiting for human")

        elif d.startswith("DEFER:"):
            self.g.add_edge(task_id, "deferred", task_id, {}, agent_id="worker")
            print(f"[worker] deferred")

        elif d == "NO_API_KEY":
            self.g.add_node("question", "No API key available for worker. Set OPENCODE_GO_API_KEY.",
                          {"task_id": task_id}, agent_id="worker")
            self.g.add_edge(task_id, "waiting_human", task_id, {}, agent_id="worker")
            print("[worker] no API key")

        else:
            self.g.add_edge(task_id, "deferred", task_id, {}, agent_id="worker")
            print(f"[worker] unknown decision, deferred")

    def work(self, task: dict):
        task_id = task["id"]
        print(f"[worker] task: {task['name']}")
        self.g.log("worker", "started", "task", task_id)

        context = self.gather_context(task)
        decision = self.reason(task, context)
        print(f"[worker] decided: {decision[:150]}")

        self.run_decision(decision, task)
        self.g.log("worker", "finished", "task", task_id, "ok", decision[:200])


if __name__ == "__main__":
    g = Graph(DB_PATH)
    w = Worker(g)
    task = w.pick_task()
    if task:
        w.work(task)
    else:
        print("[worker] no pending tasks")
    g.close()
