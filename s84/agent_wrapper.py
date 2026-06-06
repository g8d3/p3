#!/usr/bin/env python3
"""Wrapper: registra agente, monitorea recursos, lanza opencode como hijo."""
import os, sys, time, json, urllib.request, threading, subprocess, signal

PROXY = os.environ.get("OPENCODE_GO_BASE_URL", "http://localhost:9098").rstrip("/")
WINDOW = os.environ.get("X_AID") or "?"
PID = os.getpid()
STARTED = time.time()

def proxy_post(path, data):
    try:
        req = urllib.request.Request(f"{PROXY}{path}",
            data=json.dumps(data).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=3)
    except: pass

def monitor(parent_pid, child_pid):
    """Reporta heartbeat mientras el hijo viva."""
    import subprocess
    while True:
        try:
            os.kill(child_pid, 0)
        except OSError:
            break  # hijo murio
        try:
            # Leer CPU y RAM via /proc/pid/stat
            with open(f"/proc/{parent_pid}/status") as f:
                data = f.read()
            vm_rss = 0
            for line in data.split("\n"):
                if line.startswith("VmRSS:"):
                    vm_rss = int(line.split()[1]) / 1024  # kB -> MB
            # CPU: tiempo de usuario+system desde inicio
            with open(f"/proc/{parent_pid}/stat") as f:
                stats = f.read().split()
            utime = float(stats[13])
            stime = float(stats[14])
            elapsed = time.time() - STARTED
            cpu_pct = round((utime + stime) / elapsed * 100, 1) if elapsed > 0 else 0
            proxy_post("/agent/heartbeat", {
                "agent": WINDOW, "pid": PID,
                "cpu": cpu_pct, "mem_mb": round(vm_rss, 1),
                "ts": time.time()
            })
        except: pass
        time.sleep(15)

# Registrar
proxy_post("/agent/register", {
    "agent": WINDOW, "pid": PID, "started": STARTED,
    "host": os.uname().nodename
})

# Lanzar opencode
opencode = "/home/vuos/.opencode/bin/opencode"
proc = subprocess.Popen([opencode] + sys.argv[1:])

# Monitorear en background
threading.Thread(target=monitor, args=(os.getpid(), proc.pid), daemon=True).start()

proc.wait()
proxy_post("/agent/unregister", {"agent": WINDOW})
