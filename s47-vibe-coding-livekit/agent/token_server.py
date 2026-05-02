"""LiveKit token server + browser log collector."""

import os
import json
import uuid
import datetime

from livekit.api import AccessToken, VideoGrants
from http.server import HTTPServer, BaseHTTPRequestHandler


LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs

        if self.path == "/health":
            self._json(200, {"ok": True})
            return

        params = parse_qs(urlparse(self.path).query)
        room_name = (params.get("room") or ["vibe-coding-session"])[0]
        identity = (params.get("identity") or [f"user-{uuid.uuid4().hex[:6]}"])[0]

        token = AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
            .with_identity(identity) \
            .with_name(identity) \
            .with_grants(VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            ))

        self._json(200, {"token": token.to_jwt(), "room": room_name, "identity": identity})

    def do_POST(self):
        if self.path == "/log":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length).decode("utf-8")
                data = json.loads(body)
                level = data.get("level", "info")
                msg = data.get("message", "")
                stack = data.get("stack", "")
                ts = datetime.datetime.now().isoformat()
                print(f"[browser-{level}] {ts} — {msg}", flush=True)
                if stack:
                    for line in stack.split("\n")[:5]:
                        print(f"  {line}")
                self._json(200, {"ok": True})
            except Exception as e:
                print(f"[browser-log-error] {e}")
                self._json(400, {"error": str(e)})
        else:
            self._json(404, {"error": "not found"})

    def _json(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        print(f"[token-server] {args[0]} {args[1]} {args[2]}", flush=True)


def main():
    port = int(os.environ.get("TOKEN_PORT", "7882"))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"[token-server] listening on :{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
