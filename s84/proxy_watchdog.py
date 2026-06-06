#!/usr/bin/env python3
"""
API Proxy + Watchdog — intercepta llamadas al LLM, detecta agentes idle.
Web UI en http://localhost:9099 para monitorear actividad en tiempo real.
"""
import json, os, time, threading, html
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
MAX_LOG = 100

def get_agent_id(headers, body):
    ua = headers.get("User-Agent", "")
    if "opencode" in ua.lower():
        return "ventana-1 (evol-trading)"
    if "crush" in ua.lower():
        return "crush"
    if "python" in ua.lower():
        return "s84"
    return f"agent-{len(agents)}"

def track_activity(agent_id):
    with agents_lock:
        agents[agent_id] = {"last_request": time.time(), "idle": False}

def check_idle():
    """Hilo watchdog: detecta idle y envía recordatorios vía tmux."""
    last_nudge = {}
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

        # Nudge agents that are idle
        for aid, info in list(agents.items()):
            if info.get("idle"):
                last_nudged = last_nudge.get(aid, 0)
                if now - last_nudged > 30:  # nudgar cada 30s como máximo
                    last_nudge[aid] = now
                    # Map agent name to tmux window
                    if "evol-trading" in aid or "ventana-1" in aid:
                        win = "evol-trading"
                    elif "s84" in aid or "agent-0" in aid:
                        win = "s84"
                    else:
                        continue
                    msg = f"Sigue trabajando. Revisa shared-bridge/ para nuevos descubrimientos."
                    log_entry(f"[NUDGE] → {win}: {msg}")
                    import subprocess
                    subprocess.run(["tmux", "send-keys", "-t", win, "Enter"], capture_output=True)
                    time.sleep(0.2)
                    subprocess.run(["tmux", "send-keys", "-t", win, msg, "Enter"], capture_output=True)

def log_entry(msg):
    with log_lock:
        log_entries.insert(0, {"t": time.strftime("%H:%M:%S"), "msg": msg})
        while len(log_entries) > MAX_LOG:
            log_entries.pop()

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
                    elapsed = now - v["last_request"]
                    state[k] = {"last_s": int(elapsed), "idle": v["idle"],
                                "status": "idle" if v["idle"] else "activo"}
                self.wfile.write(json.dumps({"proxy": "ok", "agents": state,
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

        agent_id = get_agent_id(self.headers, body)
        track_activity(agent_id)

        try:
            req_body = json.loads(body)
            model = req_body.get("model", "?")
            messages = req_body.get("messages", [])
            msgs = len(messages)
            # Primeros y últimos caracteres del último mensaje del usuario
            last_user = ""
            for m in reversed(messages):
                if m.get("role") == "user":
                    content = m.get("content", "") or m.get("text", "")
                    if isinstance(content, list):
                        content = " ".join(c.get("text","") for c in content if isinstance(c, dict))
                    if content:
                        last_user = content[:100]
                        break
            snippet = last_user[:3] + "..." + last_user[-3:] if len(last_user) > 6 else last_user
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
            data = resp.read()
            elapsed = int((time.time() - t0) * 1000)
            log_entry(f"[200] {agent_id} | {model} | {msgs} msgs | \"{snippet}\" | {elapsed}ms")
            self.send_response(resp.status)
            for k, v in resp.headers.items():
                if k.lower() in ("content-type",):
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)
        except urllib.error.HTTPError as e:
            elapsed = int((time.time() - t0) * 1000)
            log_entry(f"[{e.code}] {agent_id} | {model} | {elapsed}ms")
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            log_entry(f"[ERR] {agent_id} | {str(e)[:50]}")
            self.send_response(502)
            self.end_headers()
            self.wfile.write(str(e).encode())

# ── Web UI ──

class UIHandler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Refresh", "3")
        self.end_headers()
        now = time.time()
        html_parts = ['<!doctype html><html><head><meta charset="utf-8"/>',
            '<meta name="viewport" content="width=device-width"/><title>Proxy Watchdog</title>',
            '<style>body{background:#111;color:#0f0;font-family:monospace;padding:10px;font-size:14px}',
            '.ok{color:#0f0}.idle{color:#ff0}.err{color:#f00}.info{color:#0af}',
            'table{width:100%;border-collapse:collapse}td{padding:4px 8px;border-bottom:1px solid #222}',
            '.bar{height:6px;background:#333;border-radius:3px;margin:4px 0}',
            '.bar-fill{height:6px;background:#0f0;border-radius:3px;transition:width 1s}</style></head><body>']

        html_parts.append(f'<h2>🔍 Proxy Watchdog</h2>')
        html_parts.append(f'<p>Upstream: {UPSTREAM_URL}</p>')

        # Agent status
        with agents_lock:
            html_parts.append('<table><tr><th>Agente</th><th>Estado</th><th>Última request</th></tr>')
            for aid, info in sorted(agents.items()):
                elapsed = now - info["last_request"]
                status = "🟢 activo" if not info["idle"] else "🟡 idle"
                cls = "ok" if not info["idle"] else "idle"
                html_parts.append(f'<tr class="{cls}"><td>{aid}</td><td>{status}</td><td>{elapsed:.0f}s</td></tr>')
            html_parts.append('</table>')

        # Activity log
        html_parts.append('<h3>📋 Actividad reciente</h3><div style="font-size:12px">')
        with log_lock:
            for entry in log_entries[:30]:
                cls = "err" if "[ERR]" in entry["msg"] or "[4" in entry["msg"] else "ok" if "[200]" in entry["msg"] else "info"
                html_parts.append(f'<div class="{cls}">[{entry["t"]}] {html.escape(entry["msg"])}</div>')
        html_parts.append('</div></body></html>')

        self.wfile.write(''.join(html_parts).encode())

class ThreadedProxy(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def main():
    print(f"\n=== LLM Proxy Watchdog ===")
    print(f"Puerto proxy: {PROXY_PORT}")
    print(f"Web UI: http://localhost:{UI_PORT}")
    print(f"Upstream: {UPSTREAM_URL}")
    print(f"Idle timeout: {AGENT_TIMEOUT}s\n")

    threading.Thread(target=check_idle, daemon=True).start()

    proxy = ThreadedProxy(("0.0.0.0", PROXY_PORT), ProxyHandler)
    ui = ThreadedProxy(("0.0.0.0", UI_PORT), UIHandler)
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
