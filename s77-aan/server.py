#!/usr/bin/env python3
"""AAN Server — multi-version agent platform.

Each version serves at /v{id}/... All versions are live simultaneously.
Agents build versions in parallel. The UI shows everything happening.
"""
import http.server
import json
import os
import sqlite3
import threading
import time
import urllib.parse

from version_registry import VersionRegistry
from orchestrator import Orchestrator

HOST = "0.0.0.0"
PORT = 9091
BASE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE, "web")
db = VersionRegistry()
orch = Orchestrator()


class AANHandler(http.server.BaseHTTPRequestHandler):
    """Routes requests by version path (/v{id}/...)."""

    def _respond(self, data, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if isinstance(data, bytes):
            self.wfile.write(data)
        elif isinstance(data, str):
            self.wfile.write(data.encode())
        else:
            self.wfile.write(json.dumps(data, default=str).encode())

    def _serve_file(self, path):
        try:
            with open(path, "rb") as f:
                data = f.read()
            ext = os.path.splitext(path)[1]
            mime = {".html": "text/html", ".js": "text/javascript",
                    ".css": "text/css", ".png": "image/png",
                    ".svg": "image/svg+xml", ".md": "text/markdown"}
            self._respond(data, 200, mime.get(ext, "text/plain"))
        except FileNotFoundError:
            self._respond({"error": "not found"}, 404)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def _route_version(self, v_id, subpath):
        """Route to a specific version's content."""
        v = db.get_version(v_id)
        if not v:
            self._respond({"error": "version not found"}, 404)
            return
        version_dir = os.path.join(BASE, "versions", v_id)
        serve_path = os.path.join(version_dir, subpath.lstrip("/"))
        if os.path.isfile(serve_path):
            self._serve_file(serve_path)
        else:
            # Show version info page
            html = f"""<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{v_id} — AAN</title><style>
body{{font-family:system-ui,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;max-width:800px;margin:0 auto}}
h1{{color:#58a6ff}}pre{{background:#161b22;padding:16px;border-radius:8px;overflow:auto}}
.info{{color:#8b949e;font-size:.9rem;margin:12px 0}}
a{{color:#58a6ff}}
</style></head><body>
<h1>{v_id}</h1>
<div class="info">{v.get('message','')} — by {v.get('created_by','')} — {v.get('status','')}</div>
<p><a href="/">← Back to AAN</a></p>"""
            # List files in version directory
            if os.path.isdir(version_dir):
                files = os.listdir(version_dir)
                if files:
                    html += "<h2>Files</h2><ul>"
                    for f in files:
                        fp = os.path.join(version_dir, f)
                        label = f + ("/" if os.path.isdir(fp) else "")
                        html += f'<li><a href="/{v_id}/{f}">{label}</a></li>'
                    html += "</ul>"
            html += "</body></html>"
            self._respond(html, 200, "text/html")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Version routing
        if path.startswith("/v"):
            parts = path.split("/", 2)
            v_id = parts[1]
            subpath = parts[2] if len(parts) > 2 else "/"
            self._route_version(v_id, subpath)
            return

        # Main UI
        if path == "/" or path == "":
            self._serve_file(os.path.join(WEB_DIR, "index.html"))
            return

        # Static files
        if path.startswith("/web/"):
            self._serve_file(os.path.join(BASE, "web", path[5:]))
            return

        # API: agents
        if path == "/api/agents":
            self._respond({"agents": orch.get_status()})
            return

        # API: versions
        if path == "/api/versions":
            self._respond({"versions": db.list_versions()})
            return

        # API: SSE events
        if path == "/api/events":
            self._sse_loop()
            return

        self._respond({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        body = self._read_body()

        if path == "/api/agents/launch":
            task = body.get("task", "")
            if not task:
                self._respond({"error": "task required"}, 400)
                return
            v = db.create_version("agent", f"agent: {task[:60]}")
            agent = orch.launch_agent("builder", task, v["id"])
            self._respond({"version": v["id"], "status": agent.status})
            return

        self._respond({"error": "not found"}, 404)

    def _sse_loop(self):
        """Push agent + version updates to clients."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        seen_versions = len(db.list_versions())
        seen_agents = len(orch.get_status())
        try:
            while True:
                versions = len(db.list_versions())
                agents = len(orch.get_status())
                changed = versions != seen_versions or agents != seen_agents
                if changed:
                    seen_versions, seen_agents = versions, agents
                    data = json.dumps({
                        "versions": db.list_versions(),
                        "agents": orch.get_status(),
                    })
                    self.wfile.write(f"data: {data}\n\n".encode())
                    self.wfile.flush()
                time.sleep(2)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def log_message(self, fmt, *args):
        pass  # quiet


def main():
    server = http.server.ThreadingHTTPServer((HOST, PORT), AANHandler)
    print(f"AAN running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
