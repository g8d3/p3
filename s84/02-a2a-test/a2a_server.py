#!/usr/bin/env python3
"""
A2A Agent Server — lightweight implementation of the A2A v1.0 HTTP+JSON/REST binding.

Compliant with:
- Agent Card at /.well-known/agent.json
- POST /message:send
- POST /tasks/{id}:cancel
- GET /tasks/{id}
- GET /tasks

Uses threading to handle async task processing alongside synchronous HTTP.
"""

import json
import os
import sys
import threading
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Optional, Callable

# ── Shared state (per-agent) ──

TASKS: dict[str, dict] = {}  # id -> task dict
TASKS_LOCK = threading.Lock()
AGENT_NAME = ""
AGENT_SKILLS = []
AGENT_PORT = 0

# ── A2A v1.0 Task State Machine ──

class TaskState:
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    REJECTED = "rejected"
    AUTH_REQUIRED = "auth-required"
    UNKNOWN = "unknown"

TERMINAL_STATES = {
    TaskState.COMPLETED, TaskState.FAILED,
    TaskState.CANCELED, TaskState.REJECTED
}

# ── Helpers ──

def new_task_id() -> str:
    return f"task-{uuid.uuid4().hex[:12]}"

def create_task(message_body: str, context_id: str = "") -> dict:
    tid = new_task_id()
    with TASKS_LOCK:
        task = {
            "id": tid,
            "contextId": context_id or tid,
            "status": {"state": TaskState.WORKING, "timestamp": time.time()},
            "artifacts": [],
            "history": [
                {"role": "user", "parts": [{"text": message_body}],
                 "messageId": f"msg-{uuid.uuid4().hex[:8]}"}
            ],
            "metadata": {
                "agent": AGENT_NAME,
                "received_at": time.time()
            }
        }
        TASKS[tid] = task
    return task

def complete_task(tid: str, result_text: str):
    with TASKS_LOCK:
        task = TASKS.get(tid)
        if not task:
            return
        # BUG FIX: don't overwrite terminal states (e.g. canceled)
        if task["status"]["state"] in TERMINAL_STATES:
            return
        task["status"] = {"state": TaskState.COMPLETED, "timestamp": time.time()}
        task["artifacts"] = [{
            "parts": [{"text": result_text}],
            "id": f"art-{uuid.uuid4().hex[:8]}",
            "index": 0
        }]
        task["history"].append({
            "role": "agent",
            "parts": [{"text": result_text}],
            "messageId": f"msg-{uuid.uuid4().hex[:8]}"
        })

def fail_task(tid: str, error: str):
    with TASKS_LOCK:
        task = TASKS.get(tid)
        if not task:
            return
        # BUG FIX: don't overwrite terminal states
        if task["status"]["state"] in TERMINAL_STATES:
            return
        task["status"] = {"state": TaskState.FAILED, "timestamp": time.time(), "error": error}

def set_task_state(tid: str, state: str):
    with TASKS_LOCK:
        task = TASKS.get(tid)
        if not task:
            return
        # BUG FIX: don't overwrite terminal states
        if task["status"]["state"] in TERMINAL_STATES and state in TERMINAL_STATES:
            return
        task["status"] = {"state": state, "timestamp": time.time()}

def get_task_safe(tid: str) -> Optional[dict]:
    with TASKS_LOCK:
        return TASKS.get(tid)

# ── Agent-specific logic (overridden per agent) ──

PROCESSOR: Optional[Callable] = None
CANCEL_HANDLER: Optional[Callable] = None

# ── Threading HTTP Server ──

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads."""
    allow_reuse_address = True
    daemon_threads = True


class A2AHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        sys.stderr.write(f"[A2A:{AGENT_PORT}] {args[0]} {args[1]} {args[2]}\n")

    def _send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("A2A-Version", "1.0")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, code, message, status=400):
        self._send_json({"jsonrpc": "2.0", "error": {"code": code, "message": message}}, status)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw)

    # ── Routes ──

    def do_GET(self):
        path = self.path

        if path == "/.well-known/agent.json":
            self._send_json(self._build_agent_card())
            return

        if path.startswith("/tasks/") and len(path) > 7:
            tid = path[7:]
            task = get_task_safe(tid)
            if not task:
                self._send_error(-32001, f"Task {tid} not found", 404)
                return
            self._send_json({"jsonrpc": "2.0", "result": task})
            return

        if path == "/tasks":
            with TASKS_LOCK:
                tasks_list = list(TASKS.values())
            self._send_json({"jsonrpc": "2.0", "result": tasks_list})
            return

        self._send_error(-32601, f"Method not found: GET {path}", 404)

    def do_POST(self):
        path = self.path
        body = self._read_body()

        if path == "/message:send":
            self._handle_send_message(body)
            return

        if path.startswith("/tasks/") and path.endswith(":cancel"):
            tid = path[7:-7]
            self._handle_cancel_task(tid)
            return

        self._send_error(-32601, f"Method not found: POST {path}", 404)

    # ── Agent Card ──

    def _build_agent_card(self) -> dict:
        host = self.headers.get("Host", f"localhost:{AGENT_PORT}")
        return {
            "name": AGENT_NAME,
            "description": f"A2A test agent. Skills: {', '.join(AGENT_SKILLS)}",
            "url": f"http://{host}",
            "version": "1.0.0",
            "capabilities": {"streaming": False, "pushNotifications": False},
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": ["text/plain"],
            "skills": [
                {
                    "id": skill.lower().replace(" ", "-"),
                    "name": skill,
                    "description": f"Can {skill.lower()}",
                    "tags": [skill.lower()],
                    "examples": [f"I need you to {skill.lower()}"]
                }
                for skill in AGENT_SKILLS
            ]
        }

    # ── Send Message ──

    def _handle_send_message(self, body: dict):
        params = body.get("params", body)
        msg_obj = params.get("message", params)

        message_body = ""
        for part in msg_obj.get("parts", []):
            if "text" in part:
                message_body += part["text"]

        context_id = msg_obj.get("contextId", "")

        # Create task
        task = create_task(message_body, context_id)

        # Launch processor in a daemon thread
        if PROCESSOR:
            t = threading.Thread(target=PROCESSOR, args=(task,), daemon=True)
            t.start()

        # Return task immediately
        self._send_json({"jsonrpc": "2.0", "result": task}, 200)

    # ── Cancel Task ──

    def _handle_cancel_task(self, tid: str):
        task = get_task_safe(tid)
        if not task:
            self._send_error(-32001, f"Task {tid} not found", 404)
            return

        with TASKS_LOCK:
            if task["status"]["state"] in TERMINAL_STATES:
                self._send_error(-32003, f"Task {tid} already in terminal state", 409)
                return

        # Call cancel handler if provided
        if CANCEL_HANDLER:
            CANCEL_HANDLER(tid)

        set_task_state(tid, TaskState.CANCELED)

        task = get_task_safe(tid)
        self._send_json({"jsonrpc": "2.0", "result": task}, 200)


# ── Server factory ──

def create_server(port: int, name: str, skills: list[str],
                  processor=None, cancel_handler=None) -> ThreadedHTTPServer:
    global AGENT_PORT, AGENT_NAME, AGENT_SKILLS, PROCESSOR, CANCEL_HANDLER
    AGENT_PORT = port
    AGENT_NAME = name
    AGENT_SKILLS = skills
    if processor:
        PROCESSOR = processor
    if cancel_handler:
        CANCEL_HANDLER = cancel_handler

    server = ThreadedHTTPServer(("0.0.0.0", port), A2AHandler)
    print(f"[{name}] A2A agent running on http://localhost:{port}")
    print(f"[{name}] Agent Card: http://localhost:{port}/.well-known/agent.json")
    print(f"[{name}] Skills: {', '.join(skills)}")
    return server


# ── Main (when run directly) ──

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9001
    name = sys.argv[2] if len(sys.argv) > 2 else f"Agent-{port}"
    skills = sys.argv[3].split(",") if len(sys.argv) > 3 and sys.argv[3] else ["process tasks"]

    def default_processor(task: dict):
        msg = task["history"][0]["parts"][0]["text"]
        time.sleep(1)
        complete_task(task["id"], f"[{name}] Done: '{msg[:80]}'")

    PROCESSOR = default_processor
    server = create_server(port, name, skills)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()
