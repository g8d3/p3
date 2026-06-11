#!/usr/bin/env python3
"""
guardian.py — Único proceso que monitorea, piensa y actúa sobre el sistema.

Reemplaza: supervisor + helperd + sequencer + reviewer_agent.
Un solo agente con capacidad de razonamiento (LLM).

Ciclo cada 30s:
1. OBSERVA: estado del proxy, workers, componentes, artefactos
2. PIENSA: llama al LLM para analizar la situación
3. DECIDE: qué acción tomar
4. ACTÚA: ejecuta la acción (enviar mensaje, reiniciar, asignar tarea)
5. VERIFICA: en el próximo ciclo, confirma que la acción funcionó
"""
import json, os, subprocess, sys, time, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

BASE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PROXY_HEALTH = "http://localhost:9098/health"
BUS_DIR = "/tmp/agent-bus"
CYCLE = 30  # 30 segundos entre ciclos
LLM_URL = "http://localhost:9098/v1/chat/completions"
MAX_ATTEMPTS = 3  # máximos intentos por agente antes de escalar

LOG = BASE / "data" / "guardian.log"


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
    with open(LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def api(messages):
    """Llama al LLM vía proxy."""
    try:
        key = os.environ.get("OPENCODE_GO_API_KEY", "")
        req = urllib.request.Request(
            LLM_URL,
            data=json.dumps({
                "model": "deepseek-v4-flash",
                "messages": messages,
                "max_tokens": 400,
                "temperature": 0.2,
            }).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
                "X-Agent-ID": "guardian",
            },
        )
        r = urllib.request.urlopen(req, timeout=30)
        data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        log(f"LLM error: {e}")
        return ""


def proxy_get():
    try:
        d = json.loads(urllib.request.urlopen(PROXY_HEALTH, timeout=5).read())
        return d.get("agents", {})
    except:
        return {}


def tmux_send(win, text):
    try:
        subprocess.run(["tmux", "send-keys", "-t", str(win), text, "Enter"],
                       timeout=2, capture_output=True)
    except:
        pass


def tmux_cap(win):
    try:
        r = subprocess.run(["tmux", "capture-pane", "-t", str(win), "-p"],
                          capture_output=True, text=True, timeout=3)
        return r.stdout or ""
    except:
        return ""


def write_bus(target, msg):
    Path(BUS_DIR).mkdir(parents=True, exist_ok=True)
    inbox = Path(BUS_DIR) / target / "in"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / f"guardian-{int(time.time()*1000)}").write_text(msg)


def pid_alive(f):
    try:
        p = int(Path(f).read_text().strip())
        return Path(f"/proc/{p}").exists()
    except:
        return False


def restart(name, cmd):
    log(f"Reiniciando {name}: {cmd}")
    try:
        out = BASE / "data" / f"{name}-out.log"
        p = subprocess.Popen(cmd, stdout=open(out, "w"), stderr=subprocess.STDOUT)
        Path(BASE / "data" / f"{name}.pid").write_text(str(p.pid))
        log(f"{name} reiniciado (PID {p.pid})")
        return True
    except Exception as e:
        log(f"{name} fallo: {e}")
        return False


class Guardian:
    def __init__(self):
        self.cycle = 0
        self.attempts = {}
        self.prev_state = ""
        log("Guardian iniciado — único proceso de monitoreo")

    def observe(self):
        """OBSERVA: recopila todo el estado del sistema."""
        agents = proxy_get()
        components = {
            "proxy": bool(agents),
            "helperd": pid_alive(BASE / "data/helperd.pid"),
            "dashboard": pid_alive(BASE / "data/dashboard.pid"),
            "supervisor": pid_alive(BASE / "data/supervisor.pid"),
            "sequencer": pid_alive(BASE / "data/sequencer.pid"),
            "runner": pid_alive(BASE / "data/runner.pid"),
        }
        # Solo workers reales
        real_workers = {
            k: {"last_s": v.get("last_s", 999), "never_active": v.get("never_active", True),
                "idle": v.get("idle", False)}
            for k, v in agents.items()
            if not k.startswith(("agent-", "supervisor-test", "python", "zsh", "git", "[tmux]", "mimo"))
            and k not in ("opencode",)  # excluir al coordinador
        }
        return {"agents": real_workers, "components": components,
                "timestamp": datetime.now().isoformat()}

    def think(self, state):
        """PIENSA: llama al LLM para analizar el estado y decidir acción."""
        summary = json.dumps({
            "workers": {k: {"last_s": v["last_s"], "idle": v["idle"], "active": not v["never_active"]}
                       for k, v in state["agents"].items()},
            "components_ok": sum(1 for v in state["components"].values() if v),
            "components_total": len(state["components"]),
        }, indent=2)

        prompt = (
            "Eres el guardián de un sistema multi-agente. Analiza este estado y decide qué hacer.\n\n"
            f"Estado:\n{summary}\n\n"
            "AGENTES: worker-1 (trading), worker-2 (contenido).\n"
            "• Si un worker lleva >120s inactivo y no tiene tarea: asígnale una\n"
            "• Si un worker lleva >60s con un comando colgado: envíale Escape\n"
            "• Si un componente está caído: di 'restart X'\n"
            "• Si todo funciona: di 'ok'\n\n"
            "Responde SOLO con una línea:\n"
            "ACCION: <acción>\n"
            "Ejemplos:\n"
            "ACCION: ok\n"
            "ACCION: task worker-1 Calcula el IC de las señales actuales y reporta en TRADING.md\n"
            "ACCION: escape worker-1\n"
            "ACCION: restart helperd\n"
        )
        return api([
            {"role": "system", "content": "Eres un guardián de sistemas. Respondes con ACCION: <acción>."},
            {"role": "user", "content": prompt},
        ])

    def act(self, action, state):
        """ACTÚA: ejecuta la acción decidida."""
        action = action.strip()
        if not action or action == "ACCION: ok":
            return

        log(f"Acción: {action}")

        if action.startswith("ACCION: task "):
            rest = action[len("ACCION: task "):]
            parts = rest.split(" ", 1)
            if len(parts) == 2:
                worker, task = parts
                write_bus(worker, f"[GUARDIAN] TAREA: {task}")
                log(f"Tarea asignada a {worker}: {task[:80]}...")

        elif action.startswith("ACCION: escape "):
            worker = action[len("ACCION: escape "):]
            tmux_send(worker, "Escape")
            log(f"Escape enviado a {worker}")

        elif action.startswith("ACCION: restart "):
            comp = action[len("ACCION: restart "):]
            cmds = {
                "helperd": (["python3", str(BASE / "core/helperd.py"), "foreground"],
                           str(BASE / "data/helperd.pid")),
                "dashboard": (["python3", str(BASE / "web/server.py")],
                            str(BASE / "data/dashboard.pid")),
                "supervisor": (["python3", str(BASE / "core/supervisor.py"), "foreground"],
                              str(BASE / "data/supervisor.pid")),
                "sequencer": (["python3", str(BASE / "core/sequencer.py")],
                             str(BASE / "data/sequencer.pid")),
                "runner": (["python3", str(BASE / "artifacts/trading/runner.py")],
                          str(BASE / "data/runner.pid")),
                "proxy": (["python3", str(BASE / "../s84/proxy/proxy_watchdog.py")],
                         str(BASE / "data/proxy.pid")),
            }
            if comp in cmds:
                cmd, pidf = cmds[comp]
                restart(comp, cmd)

    def verify(self, state):
        """VERIFICA: marca intentos como resueltos si el agente se recuperó."""
        for name, info in state["agents"].items():
            if info.get("last_s", 999) < 30 and name in self.attempts:
                pending = [a for a in self.attempts[name] if not a["resolved"]]
                if pending:
                    for a in pending:
                        a["resolved"] = True
                    log(f"VERIFICADO: {name} recuperado ({len(pending)} intentos cerrados)")

    def run(self):
        while True:
            self.cycle += 1
            try:
                state = self.observe()
                log(f"Ciclo {self.cycle}: {len(state['agents'])} agentes, "
                    f"{sum(1 for v in state['components'].values() if v)}/{len(state['components'])} componentes")

                # PIENSA (solo si el estado cambió o cada 3 ciclos)
                state_sig = json.dumps(state["agents"], sort_keys=True)
                if state_sig != self.prev_state or self.cycle % 3 == 0:
                    self.prev_state = state_sig
                    decision = self.think(state)
                    self.act(decision, state)

                # VERIFICA
                self.verify(state)

            except Exception as e:
                log(f"Error en ciclo {self.cycle}: {e}")
                import traceback
                traceback.print_exc(file=open(BASE / "data/guardian-error.log", "a"))

            time.sleep(CYCLE)


if __name__ == "__main__":
    Guardian().run()
