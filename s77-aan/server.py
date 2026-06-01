#!/usr/bin/env python3
"""AAN Server — API + web UI for version registry."""
import http.server
import json
import os
import sqlite3
import urllib.parse
import time
import threading

from version_registry import VersionRegistry
from orchestrator import Orchestrator

HOST = "0.0.0.0"
PORT = 9091
WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
db = VersionRegistry()
orch = Orchestrator()


class APIHandler(http.server.BaseHTTPRequestHandler):
    def _send(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def _send_html(self, html, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def _send_file(self, path):
        try:
            with open(path, "rb") as f:
                data = f.read()
            ext = os.path.splitext(path)[1]
            mime = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".png": "image/png", ".svg": "image/svg+xml"}
            self.send_response(200)
            self.send_header("Content-Type", mime.get(ext, "text/plain"))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def _sse_loop(self):
        """Server-Sent Events: push version updates to client."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        seen = set(v["id"] for v in db.list_versions())
        try:
            while True:
                versions = db.list_versions()
                live = db.get_live()
                current = set(v["id"] for v in versions)
                if current != seen:
                    seen = current
                    data = json.dumps({"versions": versions, "live_id": live["id"] if live else None})
                    self.wfile.write(f"data: {data}\n\n".encode())
                    self.wfile.flush()
                time.sleep(2)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # client disconnected

    def _run_agent(self, description):
        """Launch a builder agent via tmux to create a new version."""
        import subprocess, tempfile
        outfile = os.path.join(os.path.dirname(__file__), "agent-output.txt")
        donefile = outfile + ".done"
        # Write the task for the agent
        task = f"Create new version implementing: {description}\nOutput your result to {outfile}"
        with open(outfile + ".task", "w") as f:
            f.write(task)

        # Launch opencode in dedicated tmux window
        cmd = f'cd {os.path.dirname(__file__)} && opencode run "{description}" > {outfile} 2>/dev/null; touch {donefile}'
        subprocess.run(["tmux", "new-window", "-d", "-n", "aan-build", cmd])
        return {"ok": True, "message": "Agent launched"}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/" or path == "":
            self._send_file(os.path.join(WEB_DIR, "index.html"))
        elif path.startswith("/web/"):
            self._send_file(os.path.join(os.path.dirname(__file__), path.lstrip("/")))
        elif path == "/api/events":
            self._sse_loop()
        elif path == "/api/versions":
            versions = db.list_versions()
            live = db.get_live()
            self._send({"versions": versions, "live_id": live["id"] if live else None})
        elif path.startswith("/api/versions/") and path.endswith("/tags"):
            v_id = path.split("/")[3]
            tags = db.get_version_tags(v_id)
            self._send({"tags": tags})
        elif path.startswith("/api/versions/"):
            v_id = path.split("/")[3]
            v = db.get_version(v_id)
            self._send(v) if v else self._send({"error": "not found"}, 404)
        elif path == "/api/tags":
            # Get all unique tags across versions
            tags = set()
            for v in db.list_versions():
                for t in db.get_version_tags(v["id"]):
                    tags.add(t["name"])
            self._send({"tags": sorted(tags)})
        elif path == "/api/agents":
            self._send({"agents": orch.get_status()})
        elif path == "/api/agents/running":
            self._send({"running": len(orch.get_running())})
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        body = self._read_body()

        if path == "/api/versions":
            v = db.create_version(body.get("created_by", "human"), body.get("message", ""))
            self._send(v, 201)
        elif path.startswith("/api/versions/") and path.endswith("/live"):
            v_id = path.split("/")[3]
            db.set_live(v_id)
            self._send({"ok": True, "live": v_id})
        elif path.startswith("/api/versions/") and path.endswith("/tags"):
            v_id = path.split("/")[3]
            tag = body.get("tag", "")
            try:
                db.create_tag(tag, "human")
            except sqlite3.IntegrityError:
                pass
            db.tag_version(tag, v_id)
            self._send({"ok": True})
        elif path == "/api/tags":
            tag = body.get("name", "")
            try:
                db.create_tag(tag, "human")
                self._send({"ok": True}, 201)
            except sqlite3.IntegrityError:
                self._send({"error": "tag exists"}, 409)
        elif path == "/api/agents/launch":
            task = body.get("task", "") or body.get("message", "")
            if not task:
                self._send({"error": "task required"}, 400)
                return
            v = db.create_version("agent", f"agent build: {task[:50]}")
            agent = orch.launch_agent("builder", task, v["id"])
            self._send({"version": v["id"], "agent": agent.agent_type, "status": agent.status})
        elif path.startswith("/api/versions/") and path.endswith("/update"):
            v_id = path.split("/")[3]
            changes = {k: body[k] for k in ("message", "status") if k in body}
            if changes:
                db.update_version(v_id, **changes)
            self._send({"ok": True})
        else:
            self._send({"error": "not found"}, 404)

    def log_message(self, fmt, *args):
        pass  # quiet


def main():
    server = http.server.ThreadingHTTPServer((HOST, PORT), APIHandler)
    print(f"AAN Server running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
