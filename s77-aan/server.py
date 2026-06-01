#!/usr/bin/env python3
"""AAN Server — API + web UI for version registry."""
import http.server
import json
import os
import sqlite3
import urllib.parse
import time

from version_registry import VersionRegistry

HOST = "0.0.0.0"
PORT = 9091
WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
db = VersionRegistry()


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
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        last_count = len(db.list_versions())
        try:
            while True:
                versions = db.list_versions()
                live = db.get_live()
                current = len(versions)
                if current != last_count:
                    last_count = current
                    data = json.dumps({"versions": versions, "live_id": live["id"] if live else None})
                    self.wfile.write(f"data: {data}\n\n".encode())
                    self.wfile.flush()
                time.sleep(1)
        except (BrokenPipeError, ConnectionResetError):
            pass

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
    server = http.server.HTTPServer((HOST, PORT), APIHandler)
    print(f"AAN Server running at http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
