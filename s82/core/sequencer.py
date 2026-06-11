#!/usr/bin/env python3
"""
sequencer.py — Task sequencer infinito.

Nunca se detiene. Siempre encuentra la siguiente tarea para cada worker.
También monitorea consumo de tokens y facilita comunicación cross-worker.

Ciclo: cada 30s detecta workers idle y les asigna nueva tarea.
Cuando se acaban las tareas predefinidas, genera nuevas automáticamente.
"""
import json, os, subprocess, sys, time, urllib.request, random
from datetime import datetime
from pathlib import Path

BASE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUS_DIR = "/tmp/agent-bus"
PROXY_URL = "http://localhost:9098"
CYCLE = 20
TOKEN_LIMIT = 100000  # alerta si se supera este consumo

LOG_FILE = BASE / "data" / "sequencer.log"
TOKEN_FILE = BASE / "data" / "token-usage.json"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")

def proxy_get(path):
    try:
        return json.loads(urllib.request.urlopen(f"{PROXY_URL}{path}", timeout=5).read())
    except: return {}

def proxy_agents():
    return proxy_get("/health").get("agents", {})

def send_task(worker, msg):
    inbox = Path(BUS_DIR) / worker / "in"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / f"seq-{int(time.time()*1000)}").write_text(msg)

def tasks_for(worker, cycle):
    """Genera tareas infinitas. Cuando se acaban las predefinidas, crea nuevas."""
    trading = [
        "Ejecuta: cd /home/vuos/code/p3/s39-trading-bot/ && ls -la y dime qué archivos .py existen. Luego corre: head -80 main.py",
        "Diseña una señal sintética de ejemplo. Crea artifacts/trading/signal_test.py que simule precios ETH y calcule RSI, MACD, y FundingRate. Ejecútalo: python3 artifacts/trading/signal_test.py",
        "Lee sobre funding rate arbitrage. Busca en s1-funding-rate-scraper cómo obtener funding rates. Documenta en TRADING.md qué se necesitaría para un bot de funding arb.",
        "Prueba la API pública de HyperLiquid: curl -s 'https://api.hyperliquid.xyz/info' -d '{\"type\":\"allMids\"}' | python3 -m json.tool | head -20. Documenta el resultado.",
        "Crea un experimento: backtest simple de 2 señales (momentum + funding) en ETH. Usa datos sintéticos. Corre: python3 artifacts/trading/signal_test.py si existe, si no crea uno.",
        "Revisa s86-dex-trading-pipeline/README.md si existe. Explica cómo integrarlo con s39.",
        "Lee sobre Kelly criterion para position sizing. Escribe una función en Python que calcule Kelly optimal f dado un historial de returns. Prueba: python3 -c 'import numpy as np; print(np.mean([0.1,-0.05,0.2,-0.02,0.15]))'",
        "Genera una estrategia nueva: mean reversion con Bollinger Bands en funding rate. Documenta en TRADING.md como 'Estrategia Propuesta #1'.",
    ]
    content = [
        "Mejora record-screen.sh: agrega opción --with-cursor que muestre el cursor del mouse. Documenta el cambio.",
        "Prueba overlay de texto en video: ffmpeg -i artifacts/s82-demo.mp4 -vf 'drawtext=text=\"s82 System\":fontsize=24:fontcolor=white:x=10:y=10' -c:a copy artifacts/s82-overlay.mp4. Reporta resultados.",
        "Graba un clip de 15s del dashboard: 1) Abre http://localhost:9093 en curl o w3m 2) Graba con record-screen.sh 15 artifacts/dashboard-clip.mp4.",
        "Crea un storyboard para un video de 2min sobre el sistema multi-agente. Escríbelo en CONTENT.md como 'Storyboard Video #1: secciones, duración, qué mostrar.'",
        "Propón una colaboración con worker-1: un video sobre trading automatizado. ¿Qué mostrarían? Escribe en CONTENT.md: 'Video Colab Trading: plan'.",
        "Explora s52-cinematic-coding-video-generator para ideas de edición. Lee su SKILL.md o README. Extrae 3 técnicas útiles.",
        "Crea un script de post-procesamiento automático: /home/vuos/code/p3/s82/scripts/post-process.sh que tome un video raw y agregue: título al inicio, música de fondo, créditos al final.",
    ]
    all_tasks = trading + content
    if worker == "worker-1":
        base = trading
    elif worker == "worker-2":
        base = content
    else:
        base = all_tasks
    # Cycle through tasks, when exhausted generate random new ones
    idx = cycle % len(base) if base else 0
    if cycle < len(base):
        return base[idx]
    else:
        # Generate novel tasks after predefined ones
        novel = [
            f"Explora un proyecto aleatorio en /home/vuos/code/p3/ y propón cómo integrarlo: ls -d /home/vuos/code/p3/s*/ | shuf -n 1",
            f"Lee un artículo sobre trading/agent systems (usa curl a una URL) y resume lo aprendido en TRADING.md",
            f"Crea un dashboard simple en python que muestre datos en tiempo real: usa http.server para servir un HTML con datos del proxy.",
            f"Escribe un análisis crítico del sistema actual en ORCHESTRATION.md: qué funciona, qué no, qué mejorarías.",
            f"Haz un experimento: corre 10 consultas a la API en paralelo y mide el tiempo de respuesta. Usa python con threading.",
        ]
        return novel[idx % len(novel)]


def check_token_usage():
    """Lee el proxy log para estimar consumo de tokens."""
    try:
        log_data = proxy_get("/log")
        total_tokens = 0
        for entry in log_data[:100]:
            req = entry.get("req", "")
            if "messages" in str(req):
                # Rough estimate: count characters / 4
                total_tokens += len(str(req)) // 4
        usage = {"timestamp": time.time(), "estimated_tokens": total_tokens}
        Path(TOKEN_FILE).write_text(json.dumps(usage, indent=2))
        return usage
    except: return {"estimated_tokens": 0}


def main():
    log("Sequencer started (infinite mode)")
    last_active = {}
    cycle = 0

    while True:
        cycle += 1
        agents = proxy_agents()
        now = time.time()
        token_usage = check_token_usage()
        tokens = token_usage.get("estimated_tokens", 0)

        for worker in ["worker-1", "worker-2"]:
            info = agents.get(worker, {})
            last_s = info.get("last_s", 999)
            never = info.get("never_active", True)
            was_active = last_active.get(worker, 0)

            # Token awareness: if high usage, give simpler tasks
            high_token_load = tokens > TOKEN_LIMIT

            if never:
                continue

            # If idle for >60s AND was recently active (had a task) → assign next
            if last_s > 60 and (was_active == 0 or (now - was_active) > 90):
                task = tasks_for(worker, cycle)
                if high_token_load:
                    task = f"[AHORRO TOKENS] {task} (mantén la respuesta corta)"
                send_task(worker, task)
                log(f"{worker}: task #{cycle} → {task[:80]}...")
                last_active[worker] = now

                # Cross-worker communication: occasionally tell them about each other
                if cycle % 5 == 0:
                    other = "worker-2" if worker == "worker-1" else "worker-1"
                    other_info = agents.get(other, {})
                    other_last = other_info.get("last_s", "?")
                    cross_msg = f"[NOTA] Tu compañero {other} está {'activo' if other_last < 60 else 'trabajando en otra tarea'}. Si ves algo que pueda ayudarle, menciónalo en tu reporte."
                    send_task(worker, cross_msg)
                    log(f"{worker}: cross-notify about {other}")

        # Token alert
        if tokens > TOKEN_LIMIT and cycle % 3 == 0:
            log(f"⚠️ TOKEN ALERT: ~{tokens} tokens estimados en últimos requests")
            for w in ["worker-1", "worker-2"]:
                send_task(w, f"[SISTEMA] Consumo alto de tokens (~{tokens}). Prioriza respuestas cortas y evita loops largos.")

        time.sleep(CYCLE)


if __name__ == "__main__":
    main()
