#!/usr/bin/env python3
"""Simple real-time dashboard: proxy agents + trading signals + system health."""
import json, urllib.request, os, time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

DATA_DIR = Path("/home/vuos/code/p3/s82/data")
PORT = 9095
REFRESH = 5

def fetch_json(url):
    try:
        r = urllib.request.urlopen(url, timeout=3)
        return json.loads(r.read())
    except: return {}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            self.send_json(self.get_data())
        else:
            self.send_html()

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        html = self.build_html()
        self.wfile.write(html.encode())

    def get_data(self):
        proxy = fetch_json("http://localhost:9098/health")
        signals = {}
        if (DATA_DIR / "live_signals.json").exists():
            with open(DATA_DIR / "live_signals.json") as f:
                signals = json.load(f)
        ic = {}
        if (DATA_DIR / "ic_stats.json").exists():
            with open(DATA_DIR / "ic_stats.json") as f:
                ic = json.load(f)
        return {"proxy": proxy, "signals": signals, "ic": ic}

    def build_html(self):
        data = self.get_data()
        proxy = data.get("proxy", {})
        signals = data.get("signals", {})
        ic = data.get("ic", {})

        # Proxy agents table
        agents = proxy.get("agents", {})
        agent_rows = ""
        for name, a in agents.items():
            status = a.get("status", "?")
            cls = "ok" if status == "ok" else ("warn" if "nunca" in str(status) else "bad")
            cpu = a.get('cpu') or 0; mem = a.get('mem_pct') or 0; last_s = a.get('last_s') or 0
            agent_rows += f"<tr><td>{name}</td><td class='{cls}'>{status}</td><td>{float(cpu):.1f}%</td><td>{float(mem):.1f}%</td><td>{int(last_s)}s</td></tr>"

        # Signals table
        sig_rows = ""
        for s in signals.get("signals", []):
            d = s.get("direction","?")
            cls = "long" if d == "LONG" else "short" if d == "SHORT" else ""
            sig_rows += f"<tr><td>{s.get('asset','')}</td><td class='{cls}'>{d}</td><td>{s.get('rsi','')}</td><td>{s.get('macd','')}</td><td>{s.get('funding','')}</td><td>{s.get('ob_imbalance','')}</td></tr>"

        # IC table
        ic_rows = ""
        for k, v in ic.items():
            ic_v = v.get("ic") or "?"
            n = v.get("n") or 0
            cls = "ok" if isinstance(ic_v, (int,float)) and ic_v > 0 else ""
            ic_rows += f"<tr><td>{k}</td><td class='{cls}'>{ic_v}</td><td>{int(n)}</td><td>{v.get('ic_trend','?')}</td></tr>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta http-equiv="refresh" content="{REFRESH}">
<title>Dashboard</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:monospace; background:#0d1117; color:#c9d1d9; padding:20px; }}
h1 {{ color:#58a6ff; font-size:18px; margin-bottom:12px; }}
h2 {{ color:#8b949e; font-size:13px; text-transform:uppercase; margin:16px 0 6px; }}
table {{ width:100%; border-collapse:collapse; font-size:12px; margin-bottom:12px; }}
th {{ text-align:left; color:#8b949e; padding:6px 4px; border-bottom:1px solid #30363d; }}
td {{ padding:5px 4px; border-bottom:1px solid #21262d; }}
.ok {{ color:#3fb950; }} .warn {{ color:#d29922; }} .bad {{ color:#f85149; }}
.long {{ color:#3fb950; font-weight:bold; }} .short {{ color:#f85149; font-weight:bold; }}
.card {{ background:#161b22; border:1px solid #30363d; border-radius:6px; padding:12px; margin-bottom:10px; }}
.meta {{ color:#484f58; font-size:10px; margin-top:10px; }}
</style>
</head>
<body>
<h1>📊 Dashboard</h1>
<p style="color:#484f58;font-size:11px">Auto-refresh cada {REFRESH}s</p>

<div class="card">
<h2>Proxy Agents</h2>
<table><tr><th>Agent</th><th>Status</th><th>CPU</th><th>Mem</th><th>Last seen</th></tr>{agent_rows}</table>
</div>

<div class="card">
<h2>Trading Signals</h2>
<table><tr><th>Asset</th><th>Signal</th><th>RSI</th><th>MACDh</th><th>Funding</th><th>OB Imb</th></tr>{sig_rows}</table>
</div>

<div class="card">
<h2>Information Coefficient</h2>
<table><tr><th>Asset</th><th>IC</th><th>Samples</th><th>Trend</th></tr>{ic_rows}</table>
</div>

<div class="meta">
PID {os.getpid()} · updated {time.strftime("%H:%M:%S")} ·
<a href="/api/data" style="color:#58a6ff">API</a>
</div>
</body></html>"""

    def log_message(self, *a): pass  # quiet

HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
