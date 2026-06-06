#!/usr/bin/env python3
import socket, threading, base64, hashlib, json, time
WS_GUID = "258EAFA5-E914-47DA-95CA-5AB5DC11B735"
PORT = 9097
LOG = "/tmp/ws_debug.log"
HTML = """<!doctype html><html><head><meta charset="utf-8"/><title>WS Debug</title></head><body><h2>WS Debug</h2><p>Status: <span id="s">connecting...</span></p><script>
var ws = new WebSocket('ws://' + location.host + '/ws');
ws.onopen=function(){document.getElementById('s').textContent='connected'};
ws.onclose=function(e){document.getElementById('s').textContent='closed:'+e.code};
ws.onerror=function(){document.getElementById('s').textContent='error'};
</script></body></html>"""

def handle(conn, addr):
    with open(LOG,'a') as f: f.write(f"{time.time()} CONN {addr}\n")
    raw = b""
    while b"\r\n\r\n" not in raw and len(raw) < 8192:
        c = conn.recv(4096)
        if not c: break
        raw += c
    if not raw: conn.close(); return
    req = raw[:raw.index(b"\r\n\r\n")].decode(errors='replace')
    with open(LOG,'a') as f: f.write(f"{time.time()} REQ {req[:200]}\n")
    if "websocket" in req.lower():
        key = [l.split(": ",1)[1] for l in req.split("\r\n") if "Sec-WebSocket-Key" in l][0]
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
        conn.send(f"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: {accept}\r\n\r\n".encode())
        with open(LOG,'a') as f: f.write(f"{time.time()} 101 SENT accept={accept[:16]}\n")
        for i in range(30):
            msg = json.dumps({"i":i}).encode()
            frame = bytearray([0x81])
            if len(msg) < 126: frame.append(len(msg))
            else: frame.append(126); frame.extend(struct.pack(">H",len(msg)))
            frame.extend(msg)
            try: conn.send(bytes(frame)); time.sleep(1)
            except: break
    else:
        body = HTML.encode()
        conn.send(f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n".encode())
        conn.send(body)
    conn.close()
    with open(LOG,'a') as f: f.write(f"{time.time()} CLOSE {addr}\n")

s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", PORT)); s.listen(5)
open(LOG,'w').write(f"{time.time()} SERVER START {PORT}\n")
print(f"Debug WS: http://192.168.0.88:{PORT}/")
while True: threading.Thread(target=handle, args=s.accept(), daemon=True).start()
