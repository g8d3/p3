#!/usr/bin/env python3
"""
web/server.py — Mobile-friendly dashboard for the multi-agent system.

Routes:
  /          → Dashboard HTML
  /api/team  → Agent team status (from proxy health + helperd log)
  /api/helps → Help history (from helperd acks)
  /api/graph → Graph nodes + edges
  /api/log   → Combined log (proxy + helperd)
"""
import json, os, subprocess, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from datetime import datetime

BASE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(BASE))
from core.graph import Graph
from core.config import PROXY_HEALTH

PORT = int(os.environ.get("DASHBOARD_PORT", "9093"))
g = Graph()


def curl_ok():
    import urllib.request
    try:
        urllib.request.urlopen(PROXY_HEALTH, timeout=3)
        return True
    except: return False

def proxy_data():
    import urllib.request
    try:
        d = json.loads(urllib.request.urlopen(PROXY_HEALTH, timeout=5).read())
        return d.get("agents", {}), d.get("logs", [])
    except Exception:
        return {}, []


def helperd_logs():
    logfile = BASE / "data" / "helperd.log"
    if not logfile.exists():
        return []
    with open(logfile) as f:
        return [json.loads(line) for line in f if line.strip()][-50:]


def help_acks():
    ackfile = BASE / "data" / "help-acks.json"
    if not ackfile.exists():
        return {}
    return json.loads(ackfile.read_text())


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        if self.path == "/api/team":
            agents, logs = proxy_data()
            now = datetime.utcnow()
            team = []
            for name, info in sorted(agents.items()):
                team.append({
                    "name": name,
                    "status": info.get("status", "unknown"),
                    "last_s": info.get("last_s", 0),
                    "never_active": info.get("never_active", True),
                    "idle": info.get("idle", False),
                    "pid": info.get("pid", 0),
                    "cpu": info.get("cpu", 0),
                    "mem_pct": info.get("mem_pct", 0),
                })
            self._json({"team": team, "logs": logs[-15:]})
            return

        if self.path == "/api/helps":
            acks = help_acks()
            hlogs = helperd_logs()
            resolved = 0
            total = 0
            for name, helps in acks.items():
                for h in helps:
                    total += 1
                    if h.get("resolved"):
                        resolved += 1
            self._json({
                "history": acks,
                "recent": hlogs[-20:],
                "stats": {"total_helps": total, "resolved": resolved},
            })
            return

        if self.path == "/api/graph":
            self._json({
                "nodes": g.query_nodes(),
                "edges": g.get_edges(),
                "stats": g.stats(),
            })
            return

        if self.path == "/api/status":
            agents, logs = proxy_data()
            sf = BASE / "data" / "live_signals.json"
            signals = json.loads(sf.read_text()) if sf.exists() else {}
            acks = help_acks()
            total_helps = sum(len(v) for v in acks.values())
            resolved = sum(1 for v in acks.values() for h in v if h.get("resolved"))

            # Component health
            def pid_alive(f):
                try:
                    p = int(Path(f).read_text().strip())
                    return Path(f"/proc/{p}").exists()
                except: return False
            components = {
                "proxy": curl_ok(),
                "helperd": pid_alive(BASE / "data/helperd.pid"),
                "dashboard": pid_alive(BASE / "data/dashboard.pid"),
                "supervisor": pid_alive(BASE / "data/supervisor.pid"),
                "sequencer": pid_alive(BASE / "data/sequencer.pid"),
                "runner": pid_alive(BASE / "data/runner.pid"),
                "busd": bool(subprocess.run(["pgrep","-f","inotifywait"], capture_output=True).returncode == 0),
            }

            # Progress stats
            progress_files = list((BASE / "progress").glob("*.md"))
            progress_lines = sum(len(f.read_text().split("\n")) for f in progress_files if f.is_file())

            # Artifacts
            artifacts = list((BASE / "artifacts").rglob("*"))
            artifact_count = len([a for a in artifacts if a.is_file()])
            artifact_size = sum(a.stat().st_size for a in artifacts if a.is_file())

            # Latest review
            reviews_file = BASE / "progress" / "REVIEWS.md"
            latest_review = ""
            if reviews_file.exists():
                lines = reviews_file.read_text().strip().split("\n")
                # Get last review section
                sections = reviews_file.read_text().split("\n## ")
                if len(sections) > 1:
                    latest_review = sections[-1][:500]

            self._json({
                "components": components,
                "agents": {k: {"last_s": v.get("last_s"), "status": v.get("status"),
                               "idle": v.get("idle"), "never_active": v.get("never_active")}
                          for k, v in agents.items()},
                "signals": signals,
                "help_stats": {"total": total_helps, "resolved": resolved},
                "progress": {"files": len(progress_files), "lines": progress_lines},
                "artifacts": {"count": artifact_count, "size_kb": round(artifact_size/1024)},
                "latest_review": latest_review[:300],
            })
            return

        if self.path == "/api/summary":
            agents, logs = proxy_data()
            sf = BASE / "data" / "live_signals.json"
            signals = json.loads(sf.read_text()) if sf.exists() else {}
            hlogs = helperd_logs()
            acks = help_acks()
            total_helps = sum(len(v) for v in acks.values())
            resolved = sum(1 for v in acks.values() for h in v if h.get("resolved"))
            self._json({
                "agents": {k: {"last_s": v.get("last_s"), "status": v.get("status"),
                               "idle": v.get("idle"), "never_active": v.get("never_active")}
                          for k, v in agents.items()},
                "signals": signals,
                "help_stats": {"total": total_helps, "resolved": resolved},
                "healthy": {"proxy": bool(agents), "dashboard": True},
            })
            return

        if self.path == "/api/signals":
            sf = BASE / "data" / "live_signals.json"
            if sf.exists():
                self._json(json.loads(sf.read_text()))
            else:
                self._json({"signals": [], "status": "no signals yet"})
            return

        if self.path == "/api/log":
            agents, logs = proxy_data()
            hlogs = helperd_logs()
            combined = (
                [{"source": "proxy", **l} for l in logs[-30:]] +
                [{"source": "helperd", **l} for l in hlogs[-30:]]
            )
            combined.sort(key=lambda x: x.get("timestamp", x.get("t", "")), reverse=True)
            self._json({"entries": combined[:50]})
            return

        self._html()

    def _html(self):
        html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>s82 Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,monospace;background:#0d1117;color:#c9d1d9;font-size:14px;padding:0}
.header{background:#161b22;border-bottom:1px solid #30363d;padding:12px 16px;position:sticky;top:0;z-index:10}
.header h1{color:#58a6ff;font-size:18px;display:inline}
.header .ts{color:#484f58;font-size:11px;float:right;margin-top:4px}
.stats{display:flex;gap:8px;padding:12px 16px;background:#0d1117;border-bottom:1px solid #21262d;flex-wrap:wrap}
.stat{border:1px solid #30363d;border-radius:6px;padding:8px 16px;text-align:center;flex:1;min-width:80px;background:#161b22}
.stat .n{font-size:20px;font-weight:bold;color:#58a6ff}
.stat .l{font-size:10px;color:#8b949e;text-transform:uppercase}
.tabs{display:flex;gap:0;padding:0 16px;background:#0d1117;border-bottom:1px solid #30363d;overflow-x:auto}
.tab{padding:10px 16px;cursor:pointer;color:#8b949e;border-bottom:2px solid transparent;font-size:13px;white-space:nowrap}
.tab:hover{color:#c9d1d9}
.tab.active{color:#58a6ff;border-bottom-color:#58a6ff}
.panel{display:none;padding:8px 16px}
.panel.active{display:block}
.table-wrap{overflow-x:auto;max-height:60vh;overflow-y:auto;border:1px solid #30363d;border-radius:6px;margin-top:8px}
table{width:100%;border-collapse:collapse;font-size:12px}
thead{position:sticky;top:0;z-index:2}
th{background:#161b22;color:#8b949e;font-weight:600;padding:8px 10px;text-align:left;border-bottom:2px solid #30363d;white-space:nowrap}
td{padding:6px 10px;border-bottom:1px solid #21262d;white-space:nowrap}
tr:hover td{background:#1c2333}
.pagination{padding:8px 0;display:flex;gap:8px;align-items:center;font-size:12px;color:#8b949e}
.pagination button{background:#21262d;border:1px solid #30363d;color:#c9d1d9;padding:4px 12px;border-radius:4px;cursor:pointer}
.pagination button:hover{background:#30363d}
.badge{display:inline-block;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:600}
.b-active{background:#1b4a1b;color:#3fb950}
.b-idle{background:#4a3b1b;color:#d29922}
.b-stuck{background:#4a1b1b;color:#f85149}
.b-never{background:#1b1b1b;color:#484f58}
.b-long{background:#1b4a1b;color:#3fb950}
.b-short{background:#4a1b1b;color:#f85149}
.b-neutral{background:#4a3b1b;color:#d29922}
.b-resolved{background:#1b4a1b;color:#3fb950;font-size:10px}
.b-pending{background:#4a1b1b;color:#f85149;font-size:10px}
.panel h2{color:#8b949e;font-size:13px;text-transform:uppercase;letter-spacing:1px;margin:12px 0 4px}
</style>
</head>
<body>
<div class="header"><h1>s82 Dashboard</h1><span class="ts" id="ts"></span></div>
<div class="stats" id="stats"></div>
<div class="tabs" id="tabs">
  <div class="tab active" data-panel="agents">Agents</div>
  <div class="tab" data-panel="helps">Helps</div>
  <div class="tab" data-panel="signals">Signals</div>
  <div class="tab" data-panel="log">Log</div>
</div>
<div class="panel active" id="panel-agents"><h2>Agents</h2><div class="table-wrap" id="agents-table"></div></div>
<div class="panel" id="panel-helps"><h2>Help Events</h2><div class="table-wrap" id="helps-table"></div></div>
<div class="panel" id="panel-signals"><h2>Trading Signals</h2><div class="table-wrap" id="signals-table"></div></div>
<div class="panel" id="panel-log"><h2>System Log</h2><div class="table-wrap" id="log-table"></div></div>

<script>
// ── Table helper with pagination ──
function paginatedTable(data, columns, page=0, perPage=15){
  const totalPages = Math.ceil(data.length / perPage) || 1;
  const start = page * perPage;
  const pageData = data.slice(start, start + perPage);
  let html = '<table><thead><tr>' + columns.map(c => '<th>' + (c.label||c.key) + '</th>').join('') + '</tr></thead><tbody>';
  pageData.forEach(row => {
    html += '<tr>' + columns.map(c => {
      let val = c.fn ? c.fn(row) : (row[c.key] !== undefined ? row[c.key] : '');
      return '<td>' + val + '</td>';
    }).join('') + '</tr>';
  });
  html += '</tbody></table>';
  if(totalPages > 1){
    html += '<div class="pagination">';
    html += '<button onclick="window.page=0;load()">«</button>';
    html += '<span>Page ' + (page+1) + '/' + totalPages + '</span>';
    html += '<button onclick="window.page=' + Math.min(page+1, totalPages-1) + ';load()">»</button>';
    html += '</div>';
  }
  return html;
}

// Tab switching
document.getElementById('tabs').addEventListener('click', function(e){
  const tab = e.target.closest('.tab');
  if(!tab) return;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  tab.classList.add('active');
  document.getElementById('panel-' + tab.dataset.panel).classList.add('active');
});

window.page = 0;

async function load(){
  const r = await fetch('/api/status').then(r => r.json());
  const agents = r.agents || {};
  const helps = r.help_stats || {};
  const signals = r.signals || {};
  const progress = r.progress || {};
  const artifacts = r.artifacts || {};

  // Stats bar
  const workerCount = Object.values(agents).filter(a => !a.never_active).length;
  document.getElementById('stats').innerHTML =
    `<div class="stat"><div class="n">${workerCount}</div><div class="l">Active Agents</div></div>` +
    `<div class="stat"><div class="n">${progress.lines||0}</div><div class="l">Doc Lines</div></div>` +
    `<div class="stat"><div class="n">${artifacts.count||0}</div><div class="l">Artifacts</div></div>` +
    `<div class="stat"><div class="n">${helps.total||0}</div><div class="l">Helps</div></div>` +
    `<div class="stat"><div class="n">${helps.resolved||0}</div><div class="l">Resolved</div></div>`;
  document.getElementById('ts').textContent = new Date().toLocaleTimeString();

  // Agents table
  const agentList = Object.entries(agents).map(([name, v]) => ({name, ...v}));
  const page = window.page || 0;
  document.getElementById('agents-table').innerHTML = paginatedTable(agentList, [
    {key:'name', label:'Name'},
    {key:'status', label:'Status', fn: r => '<span class="badge ' + (r.never_active?'b-never':r.idle?'b-idle':r.last_s>25?'b-stuck':'b-active') + '">' + (r.never_active?'off':r.idle?'idle':r.last_s>25?'stuck':'active') + '</span>'},
    {key:'last_s', label:'Last (s)', fn: r => r.last_s + 's'},
    {key:'never_active', label:'Type', fn: r => r.never_active?'process':'agent'},
  ], page, 15);

  // Helps table
  const helpList = [];
  if(r.latest_review){
    helpList.push({source:'reviewer', detail: r.latest_review.substring(0,100), status:'info'});
  }
  document.getElementById('helps-table').innerHTML = helpList.length > 0
    ? paginatedTable(helpList, [
        {key:'source', label:'Source'},
        {key:'detail', label:'Detail'},
        {key:'status', label:'Status'},
      ], 0, 10)
    : '<div style="padding:20px;color:#484f58;text-align:center">Help data loading...</div>';

  // Signals table
  const sigList = (signals.signals || []).map(s => ({
    asset: s.asset || '?',
    direction: s.direction || '?',
    rsi: s.rsi || '?',
    macd: s.macd || '?',
    signal: s.signal || ''
  }));
  document.getElementById('signals-table').innerHTML = sigList.length > 0
    ? paginatedTable(sigList, [
        {key:'asset', label:'Asset'},
        {key:'direction', label:'Signal', fn: r => '<span class="badge ' + (r.direction==='LONG'?'b-long':r.direction==='SHORT'?'b-short':'b-neutral') + '">' + r.direction + '</span>'},
        {key:'rsi', label:'RSI'},
        {key:'macd', label:'MACD'},
        {key:'signal', label:'Detail'},
      ], 0, 10)
    : '<div style="padding:20px;color:#484f58;text-align:center">No signals yet</div>';

  // Log table
  const logR = await fetch('/api/log').then(r => r.json());
  const entries = (logR.entries || []).map(e => ({
    time: e.t || e.timestamp || '',
    source: e.source || 'sys',
    msg: e.event || e.msg || e.reason || e.detail || ''
  }));
  document.getElementById('log-table').innerHTML = paginatedTable(entries, [
    {key:'time', label:'Time'},
    {key:'source', label:'Source'},
    {key:'msg', label:'Message'},
  ], 0, 20);
}
load();
setInterval(load, 5000);
</script>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(html.encode())

    def _json(self, data):
        body = json.dumps(data, default=str).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ThreadedServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    server = ThreadedServer(("0.0.0.0", PORT), DashboardHandler)
    print(f"[dashboard] http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
