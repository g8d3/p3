#!/usr/bin/env python3
"""
API Proxy + Watchdog — intercepta llamadas al LLM, detecta agentes idle.
Web UI en http://localhost:9099 para monitorear actividad en tiempo real.
"""
import json, os, sys, time, threading, base64, struct, hashlib, ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import urllib.request, urllib.error

PROXY_PORT = 9098
UI_PORT = 9099
UPSTREAM_URL = os.environ.get("OPENCODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1/")
AGENT_TIMEOUT = 45

agents = {}
agents_lock = threading.Lock()
log_entries = []
log_lock = threading.Lock()
log_details = {}
MAX_LOG = 100
MAX_DETAILS = 30

sse_clients = []
ws_clients = []
sse_lock = threading.Lock()
ua_to_window = {}

def build_snapshot():
    with agents_lock:
        now = time.time()
        state = {}
        for k, v in agents.items():
            never = v.get("last_request", 0) == 0
            if never:
                elapsed = int(now - v.get("last_seen", now))
            else:
                elapsed = int(now - v["last_request"])
            is_idle = v.get("idle", False) or never
            state[k] = {"last_s": elapsed,
                        "never_active": never,
                        "idle": is_idle,
                        "status": "nunca" if never else ("idle" if is_idle else "activo"),
                        "pid": v.get("pid"), "cpu": v.get("cpu"),
                        "mem_pct": v.get("mem_pct")}
    with log_lock:
        logs = list(log_entries[:30])
    return {"upstream": UPSTREAM_URL, "agents": state, "logs": logs, "timestamp": time.strftime("%H:%M:%S")}

def notify_clients(event="log", data=None):
    if data is None:
        data = {}
    # SSE clients
    sse_data = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    with sse_lock:
        for client in sse_clients[:]:
            try:
                client.request.settimeout(2)
                client.wfile.write(sse_data.encode())
                client.wfile.flush()
            except:
                try: sse_clients.remove(client)
                except: pass
    # WS clients
    payload = json.dumps({"type": event, **data})
    try:
        for client in ws_clients[:]:
            try:
                client.request.settimeout(2)
                client.wfile.write(ws_encode(payload))
                client.wfile.flush()
            except:
                try: ws_clients.remove(client)
                except: pass
    except:
        pass

def get_agent_id(headers, body):
    xid = headers.get("X-Agent-ID", "")
    if xid:
        return xid
    ua = headers.get("User-Agent", "").lower()
    for key in ("opencode", "crush", "python"):
        if key in ua:
            return ua_to_window.get(key, key)
    return f"agent-{len(agents)}"

def register_agent(aid, pid, host):
    with agents_lock:
        agents[aid] = {"last_request": time.time(), "idle": False,
                       "pid": pid, "host": host,
                       "cpu": 0, "mem_mb": 0,
                       "started": time.time()}
    log_entry(f"[REG] {aid} pid={pid} host={host}")

def heartbeat_agent(aid, pid, cpu, mem):
    with agents_lock:
        if aid in agents:
            agents[aid]["last_request"] = time.time()
            agents[aid]["cpu"] = cpu
            agents[aid]["mem_mb"] = mem

def track_activity(agent_id):
    now = time.time()
    with agents_lock:
        if agent_id not in agents:
            agents[agent_id] = {"last_request": now, "idle": False, "pid": 0}
        else:
            agents[agent_id]["last_request"] = now
            agents[agent_id]["idle"] = False

def mark_idle(agent_id):
    now = time.time()
    with agents_lock:
        if agent_id in agents:
            agents[agent_id]["idle"] = True
            agents[agent_id]["last_request"] = now
    notify_clients("idle", {"type": "idle", "agent": agent_id, "last_s": int(time.time() - now + 1)})

def check_idle():
    """Hilo watchdog: detecta agentes idle. No envía mensajes a tmux."""
    while True:
        time.sleep(5)
        with agents_lock:
            now = time.time()
            for aid, info in list(agents.items()):
                elapsed = now - info["last_request"]
                if elapsed > AGENT_TIMEOUT and not info["idle"]:
                    info["idle"] = True
                    log_entry(f"[IDLE] {aid}: {elapsed:.0f}s sin actividad")
                elif elapsed <= AGENT_TIMEOUT and info["idle"]:
                    info["idle"] = False
                    log_entry(f"[ACTIVE] {aid}: volvió a trabajar")

def fmt_duration(secs):
    if secs < 0 or secs > 1e8:
        return "-"
    if secs < 60:
        return f"{secs}s"
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        return f"{secs // 3600}h"
    return f"{secs // 86400}d {(secs % 86400) // 3600}h"

def scan_agents():
    """Escanea /proc en busca de procesos LLM y los registra. Elimina agentes muertos."""
    my_pid = os.getpid()
    agent_cmds = {"opencode": "opencode", "crush": "crush", "python": "python3"}
    while True:
        time.sleep(10)
        alive_pids = set()
        pending_logs = []
        try:
            for pid_dir in os.listdir("/proc"):
                if not pid_dir.isdigit(): continue
                pid = int(pid_dir)
                if pid == my_pid: continue
                try:
                    with open(f"/proc/{pid}/cmdline") as f:
                        cmd = f.read().replace("\0", " ")
                except: continue
                matched_key = None
                for key, pat in agent_cmds.items():
                    if pat in cmd:
                        matched_key = key
                        break
                if not matched_key:
                    continue
                alive_pids.add(pid)
                # Leer TMUX_PANE del proceso para obtener nombre ventana
                aid = matched_key
                tmux_pane = ""
                try:
                    with open(f"/proc/{pid}/environ") as f:
                        env = f.read().split("\0")
                    for e in env:
                        if e.startswith("TMUX_PANE="):
                            tmux_pane = e.split("=", 1)[1]
                            break
                    if tmux_pane:
                        import subprocess
                        name = subprocess.run(
                            ["tmux", "display-message", "-t", tmux_pane, "-p", "#{window_name}"],
                            capture_output=True, text=True, timeout=2
                        ).stdout.strip()
                        if name:
                            aid = name
                except: pass
                ua_to_window[matched_key] = aid
                # Leer RAM (MB y %) y CPU (%)
                cpu = 0; mem_mb = 0; mem_pct = 0
                try:
                    with open(f"/proc/{pid}/status") as f:
                        for line in f:
                            if line.startswith("VmRSS:"):
                                mem_mb = round(float(line.split()[1]) / 1024, 1)
                            elif line.startswith("VmSize:"):
                                total_vm = float(line.split()[1])
                    with open(f"/proc/{pid}/stat") as f:
                        raw = f.read()
                    end = raw.index(")") + 2
                    fields = raw[end:].split()
                    utime = float(fields[11])
                    stime = float(fields[12])
                    start = float(fields[19])
                    ticks = utime + stime
                    cpu_sec = ticks / 100
                    start_sec = start / 100
                    with open("/proc/uptime") as f:
                        uptime = float(f.read().split()[0])
                    age = uptime - start_sec
                    cpu = round(cpu_sec / age * 100, 1) if age > 1 else 0
                    if mem_mb > 0:
                        with open("/proc/meminfo") as f:
                            for line in f:
                                if line.startswith("MemTotal:"):
                                    total_mem = float(line.split()[1]) / 1024
                                    break
                        mem_pct = round(mem_mb / total_mem * 100, 1)
                except:
                    pass

                with agents_lock:
                    if aid not in agents:
                        agents[aid] = {"last_request": 0, "last_seen": time.time(),
                                       "idle": True, "pid": int(pid), "cpu": cpu,
                                       "mem_mb": mem_mb, "mem_pct": mem_pct,
                                       "started": time.time()}
                        pending_logs.append(("detect", aid, pid))
                    else:
                        agents[aid].update({"pid": int(pid), "cpu": cpu,
                                            "mem_mb": mem_mb, "mem_pct": mem_pct,
                                            "last_seen": time.time()})
        except: pass

        # Log outside the lock (notify_clients may block)
        for kind, aid, pid in pending_logs:
            log_entry(f"[DETECT] {aid} pid={pid}")

        # Clean up dead agents (process no longer alive) - log outside lock
        gone = []
        with agents_lock:
            for aid in list(agents):
                info = agents[aid]
                pid = info.get("pid")
                if pid and pid not in alive_pids:
                    gone.append((aid, pid))
                    del agents[aid]
        for aid, pid in gone:
            log_entry(f"[GONE] {aid} pid={pid}")

def log_entry(*args):
    """log_entry(status, agent, model, req, resp, ms, detail_id=None) o log_entry(msg_string)."""
    with log_lock:
        if len(args) == 1:
            entry = {"t": time.strftime("%H:%M:%S"), "type": "sys", "msg": args[0]}
            log_entries.insert(0, entry)
        else:
            entry = {"t": time.strftime("%H:%M:%S"), "type": "http",
                     "status": args[0], "agent": args[1], "model": args[2],
                     "req": args[3], "resp": args[4], "ms": args[5]}
            if len(args) > 6:
                entry["detail_id"] = args[6]
            log_entries.insert(0, entry)
        while len(log_entries) > MAX_LOG:
            log_entries.pop()
    notify_clients("log", {"type": "log", "entry": entry})

class ProxyHandler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            with agents_lock:
                now = time.time()
                state = {}
                for k, v in agents.items():
                    never = v.get("last_request", 0) == 0
                    if never:
                        elapsed = int(now - v.get("last_seen", now))
                    else:
                        elapsed = int(now - v["last_request"])
                    is_idle = v.get("idle", False) or never
                    state[k] = {"last_s": elapsed,
                                "last_seen_s": int(now - v.get("last_seen", now)),
                                "never_active": never,
                                "idle": is_idle,
                                "status": "nunca" if never else ("idle" if is_idle else "activo"),
                                "pid": v.get("pid"), "cpu": v.get("cpu"),
                                "mem_pct": v.get("mem_pct")}
            with log_lock:
                logs_copy = list(log_entries[:30])
                self.wfile.write(json.dumps({"proxy": "ok", "agents": state,
                    "logs": logs_copy,
                    "timestamp": time.strftime("%H:%M:%S")}, indent=2).encode())
            return
        elif self.path == "/log":
            self.send_response(200)
            self.end_headers()
            with log_lock:
                self.wfile.write(json.dumps(log_entries[:50], indent=2).encode())
            return
        self.send_error(404)

    def do_POST(self):
        t0 = time.time()
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        path = self.path

        # Agent registration/heartbeat (no forward)
        if path == "/agent/register":
            data = json.loads(body)
            register_agent(data.get("agent","?"), data.get("pid",0), data.get("host",""))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return
        if path == "/agent/heartbeat":
            data = json.loads(body)
            heartbeat_agent(data.get("agent","?"), data.get("pid",0), data.get("cpu",0), data.get("mem_mb",0))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return

        agent_id = get_agent_id(self.headers, body)
        log_display = agent_id
        track_activity(agent_id)
        with agents_lock:
            if agent_id in agents and agents[agent_id].get("pid"):
                log_display = f"{agent_id}({agents[agent_id]['pid']})"

        # Capturar detalles de la request
        req_headers = dict(self.headers)
        req_headers.pop("Authorization", None)
        detail_id = f"{log_display}_{int(t0)}"

        try:
            req_body = json.loads(body)
            model = req_body.get("model", "?")
            messages = req_body.get("messages", [])
            msgs = len(messages)
            last_user = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    content = m.get("content", "") or m.get("text", "")
                    if isinstance(content, list):
                        content = " ".join(c.get("text","") for c in content if isinstance(c, dict))
                    if content:
                        last_user = content[:200]
                        break
            snippet = (last_user[:80] + "...") if len(last_user) > 80 else last_user
        except:
            model, msgs, snippet = "?", 0, "?"

        path = self.path.lstrip("/")
        if path.startswith("v1/"):
            path = path[3:]
        upstream = UPSTREAM_URL + path.lstrip("/")
        req = urllib.request.Request(upstream, data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": self.headers.get("Authorization", ""),
                     "User-Agent": "opencode-go-proxy/1.0"})
        try:
            resp = urllib.request.urlopen(req, timeout=60)
            self.send_response(resp.status)
            resp_headers = dict(resp.headers)
            for k, v in resp.headers.items():
                if k.lower() in ("content-type",):
                    self.send_header(k, v)
            self.end_headers()
            resp_body_buf = b""
            resp_snippet = ""
            chunk_count = 0
            while True:
                chunk = resp.read(8192)
                if not chunk:
                    break
                chunk_count += 1
                self.wfile.write(chunk)
                self.wfile.flush()
                if len(resp_body_buf) < 2048:
                    resp_body_buf += chunk[:2048 - len(resp_body_buf)]
                if not resp_snippet:
                    try:
                        raw = chunk.decode()
                        for line in raw.split("\n"):
                            if line.startswith("data: ") and "[DONE]" not in line:
                                d = json.loads(line[6:])
                                for c in d.get("choices", []):
                                    ct = c.get("delta", {}).get("content", "")
                                    if ct:
                                        resp_snippet = (ct[:80] + "...") if len(ct) > 80 else ct
                                    break
                    except:
                        pass
            elapsed = int((time.time() - t0) * 1000)
            if not resp_snippet and chunk_count > 0:
                resp_snippet = f"streamed({chunk_count} chunks)"
            log_entry("200", log_display, model, snippet, resp_snippet or "—", elapsed, detail_id)
            with log_lock:
                log_details[detail_id] = {
                    "req_headers": req_headers,
                    "req_body": json.loads(body) if isinstance(body, bytes) else body,
                    "resp_status": resp.status,
                    "resp_headers": resp_headers,
                    "resp_body": resp_body_buf.decode(errors="replace")[:2048],
                    "elapsed_ms": elapsed
                }
                while len(log_details) > MAX_DETAILS:
                    log_details.pop(next(iter(log_details)))
            mark_idle(agent_id)
        except urllib.error.HTTPError as e:
            elapsed = int((time.time() - t0) * 1000)
            err_body = e.read()
            log_entry(str(e.code), log_display, model, snippet, f"HTTP {e.code}", elapsed, detail_id)
            with log_lock:
                log_details[detail_id] = {
                    "req_headers": req_headers,
                    "req_body": json.loads(body) if isinstance(body, bytes) else body,
                    "resp_status": e.code,
                    "resp_headers": dict(e.headers),
                    "resp_body": err_body.decode(errors="replace")[:2048],
                    "elapsed_ms": elapsed
                }
                while len(log_details) > MAX_DETAILS:
                    log_details.pop(next(iter(log_details)))
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(err_body)
            mark_idle(agent_id)
        except Exception as e:
            elapsed = int((time.time() - t0) * 1000)
            log_entry("ERR", log_display, model, snippet, str(e)[:80], elapsed, detail_id)
            with log_lock:
                log_details[detail_id] = {
                    "req_headers": req_headers,
                    "req_body": json.loads(body) if isinstance(body, bytes) else body,
                    "resp_status": 502,
                    "resp_headers": {},
                    "resp_body": str(e)[:2048],
                    "elapsed_ms": elapsed
                }
                while len(log_details) > MAX_DETAILS:
                    log_details.pop(next(iter(log_details)))
            self.send_response(502)
            self.end_headers()
            self.wfile.write(str(e).encode())
            mark_idle(agent_id)

# ── Web UI ──

STATIC_DIR = os.path.dirname(os.path.abspath(__file__))

WS_GUID = "258EAFA5-E914-47DA-95CA-5AB5DC11B735"

def ws_encode(text):
    data = text.encode() if isinstance(text, str) else text
    frame = bytearray()
    frame.append(0x81)
    L = len(data)
    if L < 126:
        frame.append(L)
    elif L < 65536:
        frame.append(126)
        frame.extend(struct.pack(">H", L))
    else:
        frame.append(127)
        frame.extend(struct.pack(">Q", L))
    frame.extend(data)
    return bytes(frame)

def ws_decode(data):
    if len(data) < 2:
        return None
    b1, b2 = data[0], data[1]
    opcode = b1 & 0x0F
    masked = (b2 & 0x80) != 0
    L = b2 & 0x7F
    off = 2
    if L == 126 and len(data) >= 4:
        L = struct.unpack(">H", data[2:4])[0]
        off = 4
    elif L == 127 and len(data) >= 10:
        L = struct.unpack(">Q", data[2:10])[0]
        off = 10
    if masked:
        if len(data) < off + 4 + L:
            return None
        mask = data[off:off+4]
        off += 4
    else:
        if len(data) < off + L:
            return None
    payload = data[off:off+L]
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return {"opcode": opcode, "data": payload.decode(errors="replace")}

class UIHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, *a): pass
    def do_POST(self):
        if self.path == "/api/report-error":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                err_data = json.loads(body)
                log_entry(f"[CLIENT-ERR] {err_data.get('msg','?')[:200]}")
            except:
                log_entry("[CLIENT-ERR] invalid report")
            resp = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
            self.wfile.flush()
            return
        self.send_error(405)
    def do_GET(self):
        if self.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            with sse_lock:
                sse_clients.append(self)
            try:
                self.wfile.write(f"event: init\ndata: {json.dumps({'type': 'init', **build_snapshot()})}\n\n".encode())
                self.wfile.flush()
                import threading as _th
                def sse_ping(sock):
                    while True:
                        time.sleep(3)
                        try:
                            sock.wfile.write(f"event: ping\ndata: {json.dumps({'type': 'ping', 't': time.strftime('%H:%M:%S')})}\n\n".encode())
                            sock.wfile.flush()
                        except: break
                _th.Thread(target=sse_ping, args=(self,), daemon=True).start()
                while True:
                    time.sleep(30)
                    self.wfile.write(": heartbeat\n\n".encode())
                    self.wfile.flush()
            except:
                pass
            with sse_lock:
                try: sse_clients.remove(self)
                except: pass
            return
        if self.headers.get("Upgrade", "").lower() == "websocket":
            key = self.headers.get("Sec-WebSocket-Key", "")
            accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()
            self.send_response(101, "Switching Protocols")
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header("Sec-WebSocket-Accept", accept)
            self.end_headers()
            with sse_lock:
                ws_clients.append(self)
            try:
                self.wfile.write(ws_encode(json.dumps({"type": "init", **build_snapshot()})))
                self.wfile.flush()
                # Send ping every second as connection health check
                import threading
                def ws_heartbeat(sock):
                    while True:
                        time.sleep(1)
                        try:
                            sock.wfile.write(ws_encode(json.dumps({"type": "ping", "t": time.strftime("%H:%M:%S")})))
                            sock.wfile.flush()
                        except:
                            break
                threading.Thread(target=ws_heartbeat, args=(self,), daemon=True).start()
                buf = b""
                while True:
                    raw = self.rfile.read1(4096)
                    if not raw:
                        break
                    buf += raw
                    while True:
                        msg = ws_decode(buf)
                        if msg is None:
                            break
                        buf = b""
                        if msg["opcode"] == 0x8:
                            raise ConnectionError("close")
                        elif msg["opcode"] == 0x9:
                            self.wfile.write(ws_encode(b"") + b"\x8a\x00")
                            self.wfile.flush()
                        elif msg["opcode"] == 0x1:
                            try:
                                m = json.loads(msg["data"])
                                if m.get("type") == "error":
                                    log_entry(f"[CLIENT-ERR] {m.get('msg','')[:200]}")
                            except:
                                pass
            except:
                pass
            finally:
                self.close_connection = True
            with sse_lock:
                try: ws_clients.remove(self)
                except: pass
            return
        if self.path == "/clear":
            with log_lock:
                log_entries.clear()
            notify_clients("clear", {"type": "clear"})
            resp = b'{"ok":"logs cleared"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
            return
        if self.path.startswith("/detail/"):
            did = self.path[len("/detail/"):]
            with log_lock:
                d = log_details.get(did, {})
            body = json.dumps(d, ensure_ascii=True, default=str).encode(errors="replace")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        html_path = os.path.join(STATIC_DIR, "templates", "proxy.html")
        with open(html_path) as f:
            html_data = f.read()
        init_json = json.dumps({"type": "init", **build_snapshot()})
        html_data = html_data.replace("{{INIT_DATA}}", init_json)
        html_data = html_data.encode()
        self.send_header("Content-Length", str(len(html_data)))
        self.end_headers()
        self.wfile.write(html_data)
        self.wfile.flush()

class ThreadedProxy(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def watch_file():
    last = os.path.getmtime(__file__)
    while True:
        time.sleep(2)
        try:
            mtime = os.path.getmtime(__file__)
            if mtime != last:
                print("\n[HOT-RELOAD] Detected change, restarting...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except:
            pass

def main():
    print(f"\n=== LLM Proxy Watchdog ===")
    print(f"Puerto proxy: {PROXY_PORT}")
    print(f"Web UI: http://localhost:{UI_PORT}")
    print(f"Upstream: {UPSTREAM_URL}")
    print(f"Idle timeout: {AGENT_TIMEOUT}s\n")

    threading.Thread(target=check_idle, daemon=True).start()
    threading.Thread(target=scan_agents, daemon=True).start()
    threading.Thread(target=watch_file, daemon=True).start()


    CERT_FILE = "/tmp/proxy-cert.pem"
    KEY_FILE = "/tmp/proxy-key.pem"
    proxy = ThreadedProxy(("0.0.0.0", PROXY_PORT), ProxyHandler)
    ui = ThreadedProxy(("0.0.0.0", UI_PORT), UIHandler)
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(CERT_FILE, KEY_FILE)
            ui.socket = ctx.wrap_socket(ui.socket, server_side=True)
            print(f"   HTTPS UI: https://100.102.52.59:{UI_PORT}")
        except Exception as e:
            print(f"   SSL init failed (fallback to HTTP): {e}")
    else:
        print(f"   HTTP UI: http://localhost:{UI_PORT}")
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    threading.Thread(target=ui.serve_forever, daemon=True).start()

    try:
        while True: time.sleep(60)
    except KeyboardInterrupt:
        print("\nProxy detenido")
        proxy.shutdown()
        ui.shutdown()

if __name__ == "__main__":
    main()
