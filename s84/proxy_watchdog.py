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
    # Usar header custom X-Agent-ID si existe
    xid = headers.get("X-Agent-ID", "")
    if xid:
        return xid
    ua = headers.get("User-Agent", "")
    if "opencode" in ua.lower():
        return "opencode"
    if "crush" in ua.lower():
        return "crush"
    if "python" in ua.lower():
        return "python"
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

def log_entry(*args):
    """log_entry(status, agent, model, req, resp, ms) o log_entry(msg_string)"""
    with log_lock:
        if len(args) == 1:
            entry = {"t": time.strftime("%H:%M:%S"), "type": "sys", "msg": args[0]}
        else:
            entry = {"t": time.strftime("%H:%M:%S"), "type": "http",
                     "status": args[0], "agent": args[1], "model": args[2],
                     "req": args[3], "resp": args[4], "ms": args[5]}
        log_entries.insert(0, entry)
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
            # Extraer snippet de la respuesta
            resp_snippet = ""
            try:
                resp_json = json.loads(data)
                choices = resp_json.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content") or msg.get("reasoning_content") or ""
                    if isinstance(content, list):
                        content = " ".join(str(c) for c in content)
                    if content:
                        resp_snippet = content[:3] + "..." + content[-3:] if len(content) > 6 else content
            except: pass
            log_entry("200", agent_id, model, snippet, resp_snippet, elapsed)
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

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "proxy.html")

def render_template(upstream, agents_dict, logs):
    with open(TEMPLATE_PATH) as f:
        tpl = f.read()

    now = time.time()
    agent_rows = ""
    for aid, info in sorted(agents_dict.items()):
        elapsed = now - info["last_request"]
        status = "🟢 activo" if not info["idle"] else "🟡 idle"
        cls = "ok" if not info["idle"] else "idle"
        agent_rows += f'<tr class="{cls}"><td>{html.escape(aid)}</td>' \
            f'<td class="status-{"on" if not info["idle"] else "off"}">{status}</td>' \
            f'<td>{elapsed:.0f}s</td></tr>'
    if not agent_rows:
        agent_rows = '<tr><td colspan="3" style="color:#666">—</td></tr>'

    log_rows = ""
    for entry in logs[:30]:
        if entry.get("type") == "http":
            cls = "ok" if entry["status"] == "200" else "err"
            log_rows += f'<tr class="{cls}"><td>{entry["t"]}</td>' \
                f'<td>{html.escape(entry["agent"][:20])}</td>' \
                f'<td>{html.escape(entry["model"])}</td>' \
                f'<td class="snip">{html.escape(entry["req"])}</td>' \
                f'<td class="snip">{html.escape(entry["resp"])}</td>' \
                f'<td style="text-align:right">{entry["ms"]}</td></tr>'
        else:
            log_rows += f'<tr class="info"><td>{entry["t"]}</td>' \
                f'<td colspan="4">{html.escape(entry.get("msg",""))}</td><td></td></tr>'
    if not log_rows:
        log_rows = '<tr><td colspan="6" style="color:#666">—</td></tr>'

    return tpl.replace("{{UPSTREAM}}", html.escape(upstream)) \
              .replace("{{AGENTS_ROWS}}", agent_rows) \
              .replace("{{LOG_ROWS}}", log_rows)

class UIHandler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        with agents_lock:
            agents_copy = dict(agents)
        with log_lock:
            logs_copy = list(log_entries)
        html = render_template(UPSTREAM_URL, agents_copy, logs_copy)
        self.wfile.write(html.encode())

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
