#!/usr/bin/env python3
"""
pulse.py — Pulso social para el equipo.
Cada N segundos: lee proxy, detecta agentes inactivos, notifica watcher.

Señales de stuck:
1. Proxy: sin actividad LLM por >30s (el agente dejó de pensar)
2. Tmux: el output no cambió entre chequeos (pantalla congelada)

Cuando ambas se cumplen → el watcher recibe un pulso contextual.
"""
import os, sys, time, json, subprocess, hashlib, urllib.request

PROXY_HEALTH = "http://localhost:9098/health"


def proxy_data():
    try:
        return json.loads(urllib.request.urlopen(PROXY_HEALTH, timeout=3).read())
    except:
        return {"agents": {}}


def capture(win):
    try:
        r = subprocess.run(["tmux", "capture-pane", "-t", str(win), "-p"],
                           capture_output=True, text=True, timeout=3)
        return r.stdout or ""
    except:
        return ""


def notify(win: int, msg: str):
    try:
        subprocess.run(["tmux", "send-keys", "-t", str(win), msg], timeout=2)
        subprocess.run(["tmux", "send-keys", "-t", str(win), "Enter"], timeout=2)
    except:
        pass


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", default="1,2", help="ventanas de agentes")
    parser.add_argument("--watcher", type=int, default=3, help="ventana del watcher")
    parser.add_argument("--names", default="1:A-agent,2:B-buddy", help="mapeo ventana:nombre")
    parser.add_argument("--interval", type=float, default=12)
    parser.add_argument("--stuck-after", type=float, default=20,
                        help="segundos sin LLM + output congelado = stuck")
    parser.add_argument("--idle-after", type=float, default=300,
                        help="segundos sin actividad = avisar al watcher (0 para desactivar)")
    args = parser.parse_args()

    windows = [int(w) for w in args.watch.split(",")]
    names = {}
    for e in args.names.split(","):
        if ":" in e:
            w, n = e.split(":", 1)
            names[int(w)] = n

    screenshots = {}
    last_notified_stuck = 0
    last_notified_idle = {}
    cycle = 0

    print(f"[pulse] vigilando {names} cada {args.interval}s, stuck>{args.stuck_after}s, idle>{args.idle_after}s", flush=True)

    while True:
        cycle += 1
        pd = proxy_data()
        now = time.time()

        for win in windows:
            name = names.get(win, f"V{win}")
            info = pd.get("agents", {}).get(name, {})
            last_s = info.get("last_s", 999)
            never = info.get("never_active", True)

            if never:
                continue

            out = capture(win)
            h = hashlib.md5(out.encode()).hexdigest()
            prev_h = screenshots.get(win)
            frozen = prev_h is not None and h == prev_h
            screenshots[win] = h

            # Only alert if agent has an active command AND frozen output
            has_cmd = False
            for line in out.split("\n")[-10:]:
                s = line.strip().removeprefix("┃").strip()
                if s.startswith("$ ") and len(s) > 2:
                    has_cmd = True
                    break

            if has_cmd and frozen and last_s > args.stuck_after:
                if now - last_notified_stuck > args.interval * 4:
                    preview = out.strip()[-80:].replace("\n", " ")
                    msg = f"[PULSO] {name} ({last_s}s inactivo, comando congelado: {preview})"
                    notify(args.watcher, msg)
                    print(f"[pulse] ⚠ {name}: comando colgado ({last_s}s)", flush=True)
                    last_notified_stuck = now

            # Idle detection: avisar si lleva mucho sin actividad (no stuck, solo inactivo)
            if args.idle_after > 0 and not never and last_s > args.idle_after:
                last_idle = last_notified_idle.get(win, 0)
                if now - last_idle > args.idle_after / 2:
                    msg = f"[PULSO] {name} lleva {last_s}s sin actividad. ¿cómo va tu proyecto?"
                    notify(args.watcher, msg)
                    print(f"[pulse] 💤 {name}: {last_s}s idle, avisando watcher", flush=True)
                    last_notified_idle[win] = now

        if cycle % 5 == 0:
            print(f"[pulse] ciclo {cycle}", flush=True)

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
