#!/usr/bin/env python3
"""Dashboard en tiempo real: sirve datos del proxy con http.server"""
import json, urllib.request, http.server, socketserver, os
from datetime import datetime

PROXY_URL = "http://localhost:9098"

def get_proxy_data():
    try:
        d = json.loads(urllib.request.urlopen(f"{PROXY_URL}/health", timeout=3).read())
        return d.get("agents", {}), d.get("logs", [])
    except:
        return {}, []

PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>s82 Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:monospace;background:#0d1117;color:#c9d1d9;padding:20px}
h1{color:#58a6ff;font-size:20px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px}
.card h2{font-size:14px;color:#8b949e;text-transform:uppercase;margin-bottom:8px}
.card .val{font-size:28px;font-weight:bold}
.card .sub{font-size:12px;color:#8b949e;margin-top:4px}
.green{color:#3fb950}
.yellow{color:#d29922}
.red{color:#f85149}
.blue{color:#58a6ff}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:#8b949e;padding:6px 4px;border-bottom:1px solid #21262d}
td{padding:6px 4px;border-bottom:1px solid #21262d}
.agent-row:hover{background:#1c2333}
.log{font-size:11px;color:#484f58;padding:2px 0}
.refresh{color:#484f58;font-size:11px;text-align:center;margin-top:20px}
</style>
</head>
<body>
<h1>s82 Agent Dashboard</h1>
<div class="grid" id="stats"></div>
<h2 style="margin:16px 0 8px;color:#8b949e;font-size:14px;text-transform:uppercase">Agents</h2>
<table><thead><tr><th>Agent</th><th>Status</th><th>Last</th><th>CPU</th><th>RAM</th></tr></thead><tbody id="agents"></tbody></table>
<h2 style="margin:16px 0 8px;color:#8b949e;font-size:14px;text-transform:uppercase">Log</h2>
<div id="log"></div>
<div class="refresh" id="refresh">refreshing...</div>
<script>
async function load(){
  const r=await fetch('/api');
  const d=await r.json();
  const agents=Object.values(d.agents||{});
  const statsHtml=`
    <div class="card"><h2>Agentes</h2><div class="val blue">${agents.length}</div><div class="sub">monitoreados</div></div>
    <div class="card"><h2>Activos</h2><div class="val green">${agents.filter(a=>a.status==='activo').length}</div><div class="sub">en linea</div></div>
    <div class="card"><h2>Idle</h2><div class="val yellow">${agents.filter(a=>a.idle).length}</div><div class="sub">sin actividad</div></div>
    <div class="card"><h2>Nunca</h2><div class="val red">${agents.filter(a=>a.never_active).length}</div><div class="sub">nunca activos</div></div>`;
  document.getElementById('stats').innerHTML=statsHtml;
  document.getElementById('agents').innerHTML=agents.sort((a,b)=>a.name.localeCompare(b.name)).map(a=>{
    const c=a.status==='activo'?'green':a.status==='idle'?'yellow':'red';
    return `<tr class="agent-row"><td class="blue">${a.name}</td><td class="${c}">${a.status}</td><td>${a.last_s}s</td><td>${a.cpu||'-'}</td><td>${a.mem_pct||'-'}%</td></tr>`;
  }).join('');
  const logs=(d.logs||[]).slice(0,20);
  document.getElementById('log').innerHTML=logs.map(l=>`<div class="log">[${l.t||''}] ${l.msg||l.type||''}</div>`).join('')||'<div class="log">no logs</div>';
  document.getElementById('refresh').textContent='Updated: '+new Date().toLocaleTimeString();
}
load();
setInterval(load,3000);
</script>
</body>
</html>"""

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/api":
            agents, logs = get_proxy_data()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"agents": agents, "logs": logs[-30:]}).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(PAGE.encode())

PORT = 9191
with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
    print(f"[dashboard] http://localhost:{PORT}")
    httpd.serve_forever()
