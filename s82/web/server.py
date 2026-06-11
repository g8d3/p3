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

            # Hierarchy tree: zoomable from general to specific
            hierarchy = [
                # (id, parent_id, label, type, data)
                ("root", None, "s82 System", "root", {"status":"active"}),
                ("trading", "root", "Trading", "area", {"agent":"worker-1","status":"active"}),
                ("trading-pipeline", "trading", "Pipeline", "group", {}),
                ("trading-pipe-runner", "trading-pipeline", "Runner 24/7", "item", {"status":"✅"}),
                ("trading-pipe-signals", "trading-pipeline", "RSI+MACD+Funding", "item", {"status":"✅"}),
                ("trading-pipe-ic", "trading-pipeline", "IC Analysis", "item", {"status":"⚠️"}),
                ("trading-pipe-backtest", "trading-pipeline", "Backtest Sharpe 4.63", "item", {"status":"✅"}),
                ("trading-pipe-live", "trading-pipeline", "Live Trading", "item", {"status":"⏳"}),
                ("trading-signals", "trading", "Current Signals", "group", {}),
            ]
            signals_list = signals.get("signals", [])
            for s in signals_list:
                sid = "sig-" + s.get("asset", "?").lower()
                direction = s.get("direction", "?")
                hierarchy.append((sid, "trading-signals", f"{s.get('asset','?')}: {direction} RSI={s.get('rsi','?')}", "leaf", s))
            hierarchy.append(("trading-metrics", "trading", "Metrics", "group", {}))
            w1_csv = BASE / "data" / "trading_log.csv"
            w1_count = len(w1_csv.read_text().strip().split("\n")) - 1 if w1_csv.exists() else 0
            hierarchy.append(("trading-metrics-count", "trading-metrics", f"Signals logged: {w1_count}", "leaf", {}))
            hierarchy.append(("trading-metrics-assets", "trading-metrics", "Assets: ETH, BTC, SOL, HYPE", "leaf", {}))
            hierarchy.append(("trading-metrics-sharpe", "trading-metrics", "Best Sharpe: 4.63", "leaf", {}))

            hierarchy.append(("content", "root", "Content", "area", {"agent":"worker-2","status":"active"}))
            hierarchy.append(("content-pipeline", "content", "Pipeline", "group", {}))
            w2_videos = sorted((BASE / "artifacts" / "videos").glob("*.mp4")) if (BASE / "artifacts" / "videos").exists() else []
            hierarchy.append(("content-pipe-recording", "content-pipeline", "Screen Recording (ffmpeg)", "item", {"status":"✅"}))
            hierarchy.append(("content-pipe-tts", "content-pipeline", "Narración edge-tts", "item", {"status":"✅"}))
            hierarchy.append(("content-pipe-guion", "content-pipeline", "Guión escena por escena", "item", {"status":"⚠️"}))
            hierarchy.append(("content-pipe-final", "content-pipeline", "Video Final Publicable", "item", {"status":"⚠️"}))
            hierarchy.append(("content-pipe-youtube", "content-pipeline", "YouTube Upload", "item", {"status":"⏳"}))
            hierarchy.append(("content-videos", "content", "Videos", "group", {}))
            for v in reversed(w2_videos[-5:]):
                size = v.stat().st_size / 1024
                hierarchy.append((f"vid-{v.stem[:20]}", "content-videos", f"{v.name} ({round(size)}KB)", "leaf", {}))
            hierarchy.append(("content-metrics", "content", "Metrics", "group", {}))
            hierarchy.append(("content-metrics-count", "content-metrics", f"Total videos: {len(w2_videos)}", "leaf", {}))

            hierarchy.append(("infra", "root", "Infrastructure", "area", {"status":"active"}))
            hierarchy.append(("infra-components", "infra", "Components", "group", {}))
            for name, ok in components.items():
                hierarchy.append((f"comp-{name}", "infra-components", f"{name}: {'✅' if ok else '❌'}", "leaf", {}))
            hierarchy.append(("infra-git", "infra", "Git", "group", {}))
            hierarchy.append(("infra-git-commit", "infra-git", f"Last commit: {subprocess.run(['git','log','--oneline','-1'], capture_output=True,text=True,timeout=5).stdout.strip()[:60]}", "leaf", {}))
            hierarchy.append(("infra-files", "infra", "Artifacts", "group", {}))
            hierarchy.append(("infra-files-count", "infra-files", f"{artifact_count} files ({round(artifact_size/1024)}KB)", "leaf", {}))
            hierarchy.append(("infra-files-progress", "infra-files", f"{progress_lines} lines in {len(progress_files)} docs", "leaf", {}))

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
                "hierarchy": hierarchy,
                "components": components,
                "agents": agent_list,
                "signals": signals,
                "help_stats": {"total": total_helps, "resolved": resolved},
                "progress": {"files": len(progress_files), "lines": progress_lines},
                "artifacts": {"count": artifact_count, "size_kb": round(artifact_size/1024)},
                "latest_review": latest_review[:300],
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
        path = "/home/vuos/code/p3/s82/web/dashboard.html"
        data = open(path, "rb").read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

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
