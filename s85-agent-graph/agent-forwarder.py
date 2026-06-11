#!/usr/bin/env python3
"""
agent-forwarder.py — Forwarder por agente.
Agrega X-Agent-ID a cada request para que el proxy principal identifique al agente.
Cada agente usa un puerto diferente.

Uso: python3 agent-forwarder.py <agent_name> <port>
"""
import json, os, sys, urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler

AGENT = sys.argv[1]
PORT = int(sys.argv[2])
UPSTREAM = "http://localhost:9098"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        self._proxy()

    def do_POST(self):
        self._proxy()

    def _proxy(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b""
        upstream_url = UPSTREAM + self.path
        req = urllib.request.Request(
            upstream_url, data=body or None,
            headers={
                "Content-Type": self.headers.get("Content-Type", "application/json"),
                "Authorization": self.headers.get("Authorization", ""),
                "X-Agent-ID": AGENT,
                "User-Agent": f"opencode-forwarder/{AGENT}",
            })
        try:
            resp = urllib.request.urlopen(req, timeout=120)
            self.send_response(resp.status)
            ctype = resp.headers.get("Content-Type", "application/json")
            self.send_header("Content-Type", ctype)
            self.end_headers()
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(str(e).encode())


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: agent-forwarder.py <agent_name> <port>")
        sys.exit(1)
    server = HTTPServer(("", PORT), Handler)
    print(f"[forwarder:{AGENT}] listening on :{PORT} → {UPSTREAM}", flush=True)
    server.serve_forever()
