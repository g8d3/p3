#!/usr/bin/env python3
"""
AAN Server — pure viewer/controller. Creates pending tasks in DB.
Independent orchestrator launches agents. Shared DB.
"""
import http.server
import json
import os
import sys
import time
import urllib.parse
import html as html_mod

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from version_registry import VersionRegistry

HOST = "0.0.0.0"
PORT = 9091
WEB_DIR = os.path.join(BASE, "web")
db = VersionRegistry()


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, data, status=200, ctype="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if isinstance(data, bytes):
            self.wfile.write(data)
        elif isinstance(data, str):
            self.wfile.write(data.encode())
        else:
            self.wfile.write(json.dumps(data, default=str).encode())

    def _serve_file(self, path):
        with open(path, "rb") as f:
            self._send(f.read(), 200, {
                ".html": "text/html", ".js": "text/javascript",
                ".css": "text/css", ".png": "image/png",
            }.get(os.path.splitext(path)[1], "text/plain"))

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/")

        if path in ("", "/"):
            self._serve_file(os.path.join(WEB_DIR, "index.html"))
        elif path == "/api/versions":
            versions = db.list_versions()
            live = db.get_live()
            self._send({"versions": versions, "live_id": live["id"] if live else None})
        elif path.startswith("/api/versions/") and path.endswith("/work"):
            vid = path.split("/")[3]
            self._send({"work": db.get_version_work(vid)})
        elif path.startswith("/api/versions/"):
            vid = path.split("/")[3]
            v = db.get_version(vid)
            self._send(v if v else {"error": "not found"}, 200 if v else 404)
        elif path == "/api/agents":
            # Show all versions with agent work
            agents = []
            for v in db.list_versions():
                if v["created_by"] == "agent":
                    work = db.get_version_work(v["id"])
                    agents.append({
                        "version": v["id"],
                        "status": v["status"],
                        "task": v["message"][:80],
                        "started": work[0]["started_at"] if work else None,
                        "finished": work[0]["finished_at"] if work else None,
                    })
            self._send({"agents": agents})
        elif path == "/api/events":
            self._sse_loop()
        else:
            # Version URL routing
            parts = path.split("/")
            if len(parts) >= 2 and parts[1].startswith("v"):
                vid = parts[1]
                v = db.get_version(vid)
                if not v:
                    self._send({"error": "not found"}, 404)
                    return
                # Read agent output
                out_path = os.path.join(BASE, "agent-outputs", f"{vid}.txt")
                if os.path.exists(out_path):
                    with open(out_path) as f:
                        out_text = f.read().strip() or "(empty)"
                else:
                    out_text = "(no output)"
                import html as _html
                out_escaped = _html.escape(out_text)
                html = f"""<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{vid}</title><style>
body{{font-family:system-ui,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;max-width:800px;margin:0 auto}}
h1{{color:#58a6ff}}pre{{background:#161b22;padding:16px;border-radius:8px;overflow:auto;font-size:.85rem}}
.info{{color:#8b949e;margin:12px 0}}a{{color:#58a6ff}}</style></head><body>
<h1>{vid}</h1>
<div class="info">{v.get('message','')} — {v.get('created_by','')} — {v.get('status','')}</div>
<pre>{out_escaped}</pre>
<a href="/" style="color:#58a6ff">← Back</a></body></html>"""
                self._send(html, 200, "text/html")
            else:
                self._send({"error": "not found"}, 404)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/")
        body = self._read_body()

        if path == "/api/agents/launch":
            task = body.get("task", "")
            if not task:
                self._send({"error": "task required"}, 400)
                return
            # Create version as "draft" — orchestrator picks it up
            v = db.create_version("agent", task, status="draft")
            self._send({"version": v["id"], "status": "queued"}, 201)

        elif path == "/api/versions/promote":
            vid = body.get("version", "")
            if not vid:
                self._send({"error": "version required"}, 400)
                return
            db.set_live(vid)
            self._send({"ok": True, "live": vid})

        else:
            self._send({"error": "not found"}, 404)

    def _sse_loop(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        seen = len(db.list_versions())
        try:
            while True:
                current = len(db.list_versions())
                if current != seen:
                    seen = current
                    data = json.dumps({
                        "versions": db.list_versions(),
                        "agents": [v for v in db.list_versions() if v["created_by"] == "agent"],
                    }, default=str)
                    self.wfile.write(f"data: {data}\n\n".encode())
                    self.wfile.flush()
                time.sleep(2)
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def log_message(self, fmt, *args):
        pass


def main():
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"AAN viewer at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
