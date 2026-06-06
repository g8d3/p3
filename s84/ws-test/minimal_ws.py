#!/usr/bin/env python3
"""Minimal HTTP + WebSocket server on port 9095. No SSL."""
import json, struct, base64, hashlib, socket, threading, time

WS_GUID = "258EAFA5-E914-47DA-95CA-5AB5DC11B735"
PORT = 9095

HTML = """<!doctype html><html><head><meta charset="utf-8"/>
<title>WS Test</title></head><body>
<h2>WS Test</h2>
<p>Status: <span id="s">connecting...</span></p>
<p>Messages: <span id="m">0</span></p>
<script>
const ws = new WebSocket('ws://' + location.host + '/ws');
ws.onopen = () => document.getElementById('s').textContent = 'connected';
ws.onmessage = e => {
  document.getElementById('s').textContent = 'msg: ' + e.data;
  document.getElementById('m').textContent = 1 + +document.getElementById('m').textContent;
};
ws.onclose = () => document.getElementById('s').textContent = 'closed';
ws.onerror = () => document.getElementById('s').textContent = 'error';
</script></body></html>"""

def handle(conn, addr):
    raw = b""
    while b"\r\n\r\n" not in raw:
        raw += conn.recv(4096)
    req = raw[:raw.index(b"\r\n\r\n")].decode()
    first = req.split("\r\n")[0]
    upgrade = "upgrade: websocket" in req.lower()

    if upgrade:
        key = [l.split(": ",1)[1] for l in req.split("\r\n") if l.startswith("Sec-WebSocket-Key")][0]
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
        conn.send(f"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: {accept}\r\n\r\n".encode())
        for i in range(60):
            msg = json.dumps({"t": time.strftime("%H:%M:%S"), "i": i})
            frame = bytearray([0x81])
            d = msg.encode(); L = len(d)
            if L < 126: frame.append(L)
            elif L < 65536: frame.append(126); frame.extend(struct.pack(">H", L))
            frame.extend(d)
            try: conn.send(bytes(frame)); time.sleep(1)
            except: break
        conn.close()
    else:
        body = HTML.encode()
        conn.send(f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n".encode())
        conn.send(body)
        conn.close()

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", PORT))
s.listen(5)
print(f"Minimal WS test server: http://100.102.52.59:{PORT}/")
while True:
    conn, addr = s.accept()
    threading.Thread(target=handle, args=(conn, addr), daemon=True).start()
