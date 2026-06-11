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
            # Enhance signals with timeframe and duration
            if "signals" in signals:
                csv_path = BASE / "data" / "trading_log.csv"
                signal_history = {}
                if csv_path.exists():
                    for line in reversed(csv_path.read_text().strip().split("\n")[1:]):
                        parts = line.split(",")
                        if len(parts) >= 8:
                            asset = parts[1].strip()
                            sig = parts[7].strip()
                            if asset not in signal_history:
                                signal_history[asset] = []
                            signal_history[asset].append({"ts": parts[0].strip(), "sig": sig})
                for s in signals["signals"]:
                    s["timeframe"] = "1H"
                    s["trend"] = s.get("direction", "?")
                    asset = s.get("asset", "")
                    if asset in signal_history:
                        hist = signal_history[asset]
                        current_sig = s.get("direction", "")
                        first_occurrence = None
                        for h in hist:
                            if h["sig"] == current_sig:
                                first_occurrence = h
                            else:
                                break
                        if first_occurrence:
                            try:
                                from datetime import datetime
                                t0 = datetime.fromisoformat(first_occurrence["ts"])
                                mins = int((datetime.utcnow() - t0).total_seconds() / 60)
                                s["duration"] = f"{mins}min"
                                s["first_seen"] = first_occurrence["ts"]
                            except: pass
                    if asset in signal_history and len(signal_history[asset]) > 2:
                        recent = [h["sig"] for h in signal_history[asset][:3]]
                        s["trend"] = "changing" if len(set(recent)) > 1 else s.get("direction", "stable")
                    s["updated"] = signals.get("updated", "")

            acks = help_acks()
            total_helps = sum(len(v) for v in acks.values())
            resolved = sum(1 for v in acks.values() for h in v if h.get("resolved"))

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
            progress_files = list((BASE / "progress").glob("*.md"))
            progress_lines = sum(len(f.read_text().split("\n")) for f in progress_files if f.is_file())
            artifacts = list((BASE / "artifacts").rglob("*"))
            artifact_count = len([a for a in artifacts if a.is_file()])
            artifact_size = sum(a.stat().st_size for a in artifacts if a.is_file())

            reviews_file = BASE / "progress" / "REVIEWS.md"
            latest_review = ""
            if reviews_file.exists():
                sections = reviews_file.read_text().split("\n## ")
                if len(sections) > 1:
                    latest_review = sections[-1][:500]

            # Agent metadata: role, current task, tmux window
            agent_meta = {
                "worker-1": {"role": "Trading", "window": 2, "task_file": "TRADING.md",
                             "current_focus": "Señales HyperLiquid, runner, IC analysis"},
                "worker-2": {"role": "Content", "window": 3, "task_file": "CONTENT.md",
                             "current_focus": "Screen recording, narración edge-tts, guiones"},
                "supervisor": {"role": "Coordinator", "window": None, "task_file": None,
                               "current_focus": "Monitoreo 5s, salud del sistema"},
                "sequencer": {"role": "Orchestrator", "window": None, "task_file": None,
                              "current_focus": "Asignación infinita de tareas"},
                "helperd": {"role": "Reflex", "window": None, "task_file": None,
                            "current_focus": "Detección de peers stuck"},
                "reviewer": {"role": "Quality", "window": 5, "task_file": "REVIEWS.md",
                             "current_focus": "Revisión de videos y reports con Mimo v2.5"},
                "runner": {"role": "Trading Bot", "window": None, "task_file": None,
                           "current_focus": "Señales cada 5min, log CSV"},
            }

            # Build agent list with metadata
            agent_list = []
            for name, info in sorted(agents.items()):
                meta = agent_meta.get(name, {"role": "detected", "window": None, "task_file": None, "current_focus": ""})
                agent_list.append({
                    "name": name,
                    "last_s": info.get("last_s", 0),
                    "idle": info.get("idle", False),
                    "never_active": info.get("never_active", True),
                    "status": info.get("status", "?"),
                    "role": meta["role"],
                    "window": meta["window"],
                    "focus": meta["current_focus"],
                })

            # Goal tree: high-level objectives → by agent
            goal_tree = {
                "Trading HyperLiquid": {
                    "status": "active",
                    "sub": {
                        "Runner 24/7": {"status": "✅", "agent": "runner"},
                        "Señales RSI+MACD+Funding": {"status": "✅", "agent": "worker-1"},
                        "IC Analysis": {"status": "⚠️", "agent": "worker-1"},
                        "Backtest Sharpe 4.63": {"status": "✅", "agent": "worker-1"},
                        "Live trading": {"status": "⏳", "agent": "worker-1"},
                    }
                },
                "Content Creation": {
                    "status": "active",
                    "sub": {
                        "Screen recording pipeline": {"status": "✅", "agent": "worker-2"},
                        "Narración edge-tts": {"status": "✅", "agent": "worker-2"},
                        "Video final publicable": {"status": "⚠️", "agent": "worker-2"},
                        "Guión escena por escena": {"status": "⚠️", "agent": "worker-2"},
                    }
                },
                "System Infrastructure": {
                    "status": "active",
                    "sub": {
                        "7 componentes funcionando": {"status": "✅", "agent": "supervisor"},
                        "Autoheal revive caídos": {"status": "✅", "agent": "supervisor"},
                        "Git disciplina": {"status": "⚠️", "agent": "system"},
                        "Calidad con Mimo v2.5": {"status": "⚠️", "agent": "reviewer"},
                    }
                },
            }

            # Per-agent pipeline data
            agent_pipelines = {}
            trlog = BASE / "data" / "trading_log.csv"
            w1_signal_count = len(trlog.read_text().strip().split("\n")) - 1 if trlog.exists() else 0
            agent_pipelines["worker-1"] = {
                "pipeline": [
                    {"step": "HL API Integration", "status": "✅"},
                    {"step": "Signal Runner 24/7", "status": "✅"},
                    {"step": "Backtest Sharpe 4.63", "status": "✅"},
                    {"step": "IC Analysis", "status": "⚠️"},
                    {"step": "Live Trading", "status": "⏳"},
                ],
                "metrics": {"signals_logged": w1_signal_count, "assets": "ETH, BTC, SOL, HYPE", "sharpe": "4.63"},
                "latest": f"{w1_signal_count} señales en log, runner activo",
            }
            # Worker-2: Content
            w2_videos = [f for f in (BASE / "artifacts" / "videos").iterdir() if f.suffix in (".mp4",".mp3")] if (BASE / "artifacts" / "videos").exists() else []
            w2_total_size = sum(f.stat().st_size for f in w2_videos) / 1024
            agent_pipelines["worker-2"] = {
                "pipeline": [
                    {"step": "Screen Recording (ffmpeg)", "status": "✅"},
                    {"step": "Narración edge-tts", "status": "✅"},
                    {"step": "Scene Script (guión)", "status": "⚠️"},
                    {"step": "Video Final Publicable", "status": "⚠️"},
                    {"step": "YouTube Upload Pipeline", "status": "⏳"},
                ],
                "metrics": {"videos": len(w2_videos), "total_size_kb": round(w2_total_size), "latest": "20s narrated clip"},
                "latest": f"{len(w2_videos)} archivos, {round(w2_total_size)}KB total",
            }

            # Tmux windows description
            tmux_windows = []
            import subprocess as _sp
            try:
                r = _sp.run(["tmux", "list-windows", "-F", "#{window_index}: #{window_name}"],
                           capture_output=True, text=True, timeout=3)
                for line in r.stdout.strip().split("\n"):
                    parts = line.split(": ", 1)
                    if len(parts) == 2:
                        idx, name = parts
                        tmux_windows.append({"idx": int(idx), "name": name})
            except: pass

            self._json({
                "agent_pipelines": agent_pipelines,
                "tmux_windows": tmux_windows,
                "components": components,
                "agents": agent_list,
                "signals": signals,
                "help_stats": {"total": total_helps, "resolved": resolved},
                "progress": {"files": len(progress_files), "lines": progress_lines},
                "artifacts": {"count": artifact_count, "size_kb": round(artifact_size/1024)},
                "latest_review": latest_review[:300],
                "goal_tree": goal_tree,
                "tmux_windows": tmux_windows,
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
        return open("/home/vuos/code/p3/s82/web/dashboard.html").read()
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
