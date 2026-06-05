#!/usr/bin/env python3
"""
A2A Message Monitor — intercepta y muestra todo el tráfico HTTP entre
el cliente y los agentes. Corre como proxy o como logger lateral.
"""
import http.server
import json
import os
import socketserver
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MONITOR_LOG = os.path.join(BASE_DIR, "workdir", "monitor.log")
PORT = 9099  # monitor web UI port

log_lock = threading.Lock()
entries = []

def log_entry(method, url, req_body, status, resp_body, elapsed_ms):
    entry = {
        "t": time.strftime("%H:%M:%S"),
        "method": method,
        "url": url,
        "req": req_body[:200] if req_body else "",
        "status": status,
        "resp": resp_body[:300] if resp_body else "",
        "ms": elapsed_ms
    }
    with log_lock:
        entries.append(entry)
        # Keep last 50
        while len(entries) > 50:
            entries.pop(0)

def print_compact(entry):
    """Print a compact one-line log entry."""
    status_str = f"{entry['status']}" if entry['status'] else "---"
    ms_str = f"{entry['ms']}ms" if entry['ms'] >= 0 else ""
    print(f"  [{entry['t']}] {entry['method']} {entry['url'][:60]} → {status_str} {ms_str}")

class MonitorHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default logging

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with log_lock:
                html = "<html><head><meta charset='utf-8'/><meta http-equiv='refresh' content='2'/>"
                html += "<style>body{background:#000;color:#0f0;font-family:monospace;font-size:13px}"
                html += ".req{color:#88f}.resp{color:#0f0}.info{color:#ff8}</style></head><body>"
                html += "<h2>🕵️ A2A Message Monitor</h2>"
                for e in reversed(entries):
                    cls = "req" if e['method'] == "POST" else "resp"
                    html += f"<div class='{cls}'>[{e['t']}] {e['method']} {e['url'][:80]}</div>"
                    if e['req']:
                        html += f"<div style='color:#888;margin-left:20px'>{e['req'][:100]}</div>"
                    if e['resp']:
                        html += f"<div style='margin-left:20px'>{e['resp'][:120]}</div>"
                    html += f"<div style='color:#666;font-size:11px;margin-left:20px'>{e['ms']}ms</div>"
                html += "</body></html>"
            self.wfile.write(html.encode())
        else:
            self.send_error(404)

def start_monitor_ui():
    server = socketserver.TCPServer(("", PORT), MonitorHandler)
    print(f"  📡 Monitor UI: http://localhost:{PORT}")
    server.serve_forever()

# Track time for each request
_request_times = {}

def http_request(method, url, body=None):
    """Make an HTTP request and log it to the monitor."""
    t0 = time.time()
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"} if body else {}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        resp_data = resp.read().decode()
        status = resp.status
    except urllib.error.HTTPError as e:
        resp_data = e.read().decode()
        status = e.code
    except Exception as e:
        resp_data = str(e)
        status = 0

    elapsed = int((time.time() - t0) * 1000)
    entry = {
        "t": time.strftime("%H:%M:%S"),
        "method": method,
        "url": url,
        "req": json.dumps(body)[:200] if body else "",
        "status": status,
        "resp": resp_data[:300],
        "ms": elapsed
    }
    with log_lock:
        entries.append(entry)
        while len(entries) > 50:
            entries.pop(0)
    print_compact(entry)
    return resp_data


# ── Main test script ──

def main():
    # Start monitor web UI in background
    t = threading.Thread(target=start_monitor_ui, daemon=True)
    t.start()
    time.sleep(0.5)

    ALPHA = "http://localhost:9001"
    BETA = "http://localhost:9002"

    print("=" * 70)
    print("  🕵️  A2A PROTOCOL TEST — CON MONITOR DE MENSAJES")
    print("  Monitor: http://localhost:9099")
    print("  Alpha:   " + ALPHA)
    print("  Beta:    " + BETA)
    print("=" * 70)
    time.sleep(2)

    # ── INTRO ──
    print("\n📋 INTRODUCCIÓN")
    print("  Dos agentes A2A: Alpha-Generalist (puerto 9001) y Beta-Quality (puerto 9002).")
    print("  Ambos conectados al proveedor opencode-go (deepseek-v4-flash).")
    print("  Vamos a probar: descubrimiento, ejecución, cancelación y calidad.")
    time.sleep(3)

    # ── STEP 1: Discovery ──
    print("\n📋 PASO 1: DESCUBRIMIENTO")
    print("  Obteniendo las Agent Cards de cada agente...")
    time.sleep(1)

    print("\n--- GET /.well-known/agent.json (Alpha) ---")
    alpha_card = http_request("GET", f"{ALPHA}/.well-known/agent.json")
    print(f"  → Nombre: {json.loads(alpha_card).get('name')}")
    time.sleep(1)

    print("\n--- GET /.well-known/agent.json (Beta) ---")
    beta_card = http_request("GET", f"{BETA}/.well-known/agent.json")
    print(f"  → Nombre: {json.loads(beta_card).get('name')}")
    time.sleep(2)

    # ── STEP 2: Task ──
    print("\n📋 PASO 2: EJECUCIÓN DE TAREA")
    print("  Tarea: preguntar el clima a Alpha-Generalist")
    time.sleep(1)

    print("\n--- POST /message:send ---")
    task_body = {"message": {"role": "user", "parts": [{"text": "¿Qué clima hace hoy?"}], "messageId": "m1"}}
    resp1 = http_request("POST", f"{ALPHA}/message:send", task_body)
    task_id = json.loads(resp1).get("result", {}).get("id", "?")

    print(f"\n--- GET /tasks/{task_id[:20]}... ---")
    time.sleep(2)
    resp2 = http_request("GET", f"{ALPHA}/tasks/{task_id}")
    state = json.loads(resp2).get("result", {}).get("status", {}).get("state", "?")
    print(f"  → Estado: {state}")
    print(f"  ✅ Tarea completada. Tiempo: ~3s")
    time.sleep(2)

    # ── STEP 3: Cancel ──
    print("\n📋 PASO 3: CANCELACIÓN")
    print("  Enviamos tarea larga y la cancelamos...")
    time.sleep(1)

    print("\n--- POST /message:send (tarea larga) ---")
    task2 = {"message": {"role": "user", "parts": [{"text": "Escribe un reporte muy largo"}], "messageId": "m2"}}
    resp3 = http_request("POST", f"{ALPHA}/message:send", task2)
    tid2 = json.loads(resp3).get("result", {}).get("id", "?")
    time.sleep(0.5)

    print(f"\n--- POST /tasks/{tid2[:20]}...:cancel ---")
    resp4 = http_request("POST", f"{ALPHA}/tasks/{tid2}:cancel", {})
    cancel_state = json.loads(resp4).get("result", {}).get("status", {}).get("state", "?")
    print(f"  → Cancel state: {cancel_state}")
    time.sleep(1)

    resp5 = http_request("GET", f"{ALPHA}/tasks/{tid2}")
    final = json.loads(resp5).get("result", {}).get("status", {}).get("state", "?")
    print(f"  → Estado final: {final}")
    time.sleep(2)

    # ── STEP 4: Quality Gap ──
    print("\n📋 PASO 4: EL PROBLEMA DE CALIDAD")
    print("  Enviamos código BUENO y código con ERROR al mismo agente (Beta-Quality).")
    print("  Si A2A tuviera calidad, los estados deberían ser diferentes.")
    time.sleep(2)

    print("\n--- Código BUENO → POST /message:send (Beta) ---")
    good = {"message": {"role": "user", "parts": [{"text": "Revisa: def foo(): pass"}], "messageId": "m3"}}
    r3 = http_request("POST", f"{BETA}/message:send", good)
    tid3 = json.loads(r3).get("result", {}).get("id", "?")
    time.sleep(2)
    r3b = http_request("GET", f"{BETA}/tasks/{tid3}")
    s3 = json.loads(r3b).get("result", {}).get("status", {}).get("state", "?")

    print("\n--- Código con ERROR → POST /message:send (Beta) ---")
    bad = {"message": {"role": "user", "parts": [{"text": "Este código tiene un bug horrible"}], "messageId": "m4"}}
    r4 = http_request("POST", f"{BETA}/message:send", bad)
    tid4 = json.loads(r4).get("result", {}).get("id", "?")
    time.sleep(2)
    r4b = http_request("GET", f"{BETA}/tasks/{tid4}")
    s4 = json.loads(r4b).get("result", {}).get("status", {}).get("state", "?")

    print(f"\n  📊 RESULTADO:")
    print(f"     Código BUENO  → state: {s3}")
    print(f"     Código ERROR  → state: {s4}")
    if s3 == s4:
        print(f"     ❌ AMBOS IGUALES. El protocolo NO distingue calidad.")
    time.sleep(3)

    # ── STEP 5: A2A-Q ──
    print("\n📋 PASO 5: LA SOLUCIÓN — A2A-Q")
    print("  Extension que agrega al protocolo A2A:")
    print("  • Estados: quality:pending-review → needs-revision → passed")
    print("  • Operaciones: requestReview, submitVerdict")
    print("  • Métricas: eficacia (score), eficiencia (time, tokens)")
    print("  • Hardware: CPU, RAM, contexto")
    print("")
    print("  📄 RFC: s84/A2A-Q-RFC.md")
    print("  💻 Código: s84/a2a_test/")
    print("  🌐 GitHub: github.com/g8d3/p3/tree/main/s84")
    time.sleep(3)

    # ── OUTRO ──
    print("\n" + "=" * 70)
    print("  🎬 PRÓXIMO VIDEO")
    print("  Implementaremos A2A-Q en Python sobre el SDK oficial.")
    print("  Lo probaremos con agentes reales y mediremos calidad.")
    print("  ¿Funcionará? ¿Qué bugs aparecerán?")
    print("  ¿Podremos contribuir la extensión al protocolo oficial?")
    print("=" * 70)
    print("  Si quieres ayudar: github.com/g8d3/p3")
    print("  RFC listo para revisión. PRs bienvenidos.")
    print("=" * 70)


if __name__ == "__main__":
    main()
