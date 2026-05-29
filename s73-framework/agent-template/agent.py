#!/usr/bin/env python3.12
"""Agente Template — Implementación mínima del contrato IPC.

Cualquier agente en cualquier lenguaje debe:
1. Leer tareas de su directorio inbox/
2. Ejecutar la acción solicitada
3. Escribir resultados/logs a stdout como JSON (una línea por mensaje)
4. Escribir resultado final en outbox/<nombre>/<task_id>.json
"""

import json
import os
import sys
import time
import uuid
from pathlib import Path


class Agent:
    """Base class for all agents. Hereda de esta o implementa el mismo contrato."""

    def __init__(self, name: str):
        self.name = name
        self.base_dir = Path(os.environ.get("FRAMEWORK_BASE", "."))
        self.inbox_dir = self.base_dir / "inbox" / name
        self.outbox_dir = self.base_dir / "outbox" / name
        self.shared_dir = self.base_dir / "shared"
        self.poll_interval = float(os.environ.get("AGENT_POLL_MS", "500")) / 1000
        self.running = True

        # Ensure directories exist
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        self.shared_dir.mkdir(parents=True, exist_ok=True)

        self.emit_log("info", f"Agent {name} started", {"pid": os.getpid()})

    # ── IPC: Envío de mensajes ―――――――――――――――――――

    def emit(self, msg_type: str, payload: dict, msg_id: str = None):
        """Escribe un mensaje JSON a stdout (el Orchestrator lo captura)."""
        msg = {
            "id": msg_id or f"{msg_type}_{uuid.uuid4().hex[:8]}",
            "type": msg_type,
            "agent": self.name,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "payload": payload,
        }
        print(json.dumps(msg), flush=True)

    def emit_log(self, level: str, message: str, data: dict | None = None):
        self.emit("log", {"level": level, "message": message, "data": data or {}})

    def emit_error(self, message: str, stack: str = ""):
        self.emit("error", {"message": message, "stack": stack})

    def emit_result(self, task_id: str, status: str, output: dict = None,
                    duration_ms: int = 0, fallback_used: str = None):
        payload = {
            "status": status,
            "output": output or {},
            "duration_ms": duration_ms,
            "fallback_used": fallback_used,
        }
        self.emit("result", payload, msg_id=task_id)

        # Also write to outbox for filesystem-based detection
        out_path = self.outbox_dir / f"{task_id}.json"
        with open(out_path, "w") as f:
            json.dump({
                "id": task_id,
                "type": "result",
                "agent": self.name,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "payload": payload,
            }, f, indent=2)

    # ── IPC: Lectura de tareas ―――――――――――――――――――

    def read_tasks(self) -> list[dict]:
        """Lee y elimina archivos de tareas del inbox."""
        tasks = []
        for fpath in sorted(self.inbox_dir.glob("*.json"), key=os.path.getmtime):
            try:
                with open(fpath) as f:
                    task = json.load(f)
                tasks.append(task)
                fpath.unlink()  # Eliminar después de leer (ack)
            except (json.JSONDecodeError, OSError) as e:
                self.emit_log("error", f"Failed to read task {fpath.name}: {e}")
        return tasks

    def read_shared(self, name: str) -> dict | None:
        fpath = self.shared_dir / f"{name}.json"
        if fpath.exists():
            try:
                with open(fpath) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def write_shared(self, name: str, data: dict):
        fpath = self.shared_dir / f"{name}.json"
        with open(fpath, "w") as f:
            json.dump(data, f, indent=2)

    # ── Loop principal ――――――――――――――――――――――――――

    def run(self):
        while self.running:
            tasks = self.read_tasks()
            for task in tasks:
                self.handle_task(task)
            time.sleep(self.poll_interval)

    def handle_task(self, task: dict):
        """Override this method in your agent.

        Debe:
        1. Extraer action + params del payload
        2. Ejecutar la acción
        3. Llamar a self.emit_result() con el resultado
        4. Si falla, llamar a self.emit_error() antes de emit_result con status=error
        """
        payload = task.get("payload", {})
        action = payload.get("action", "")
        params = payload.get("params", {})

        self.emit_log("info", f"Processing task: {action}", {"task_id": task["id"]})
        start = time.time()

        try:
            result = self.execute(action, params)
            elapsed = int((time.time() - start) * 1000)
            self.emit_result(task["id"], "ok", result, duration_ms=elapsed)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            self.emit_error(f"Task {task['id']} failed: {e}")
            self.emit_result(task["id"], "error", {"error": str(e)}, duration_ms=elapsed)

    def execute(self, action: str, params: dict) -> dict:
        """Override this. Aquí va la lógica real del agente."""
        raise NotImplementedError

    def stop(self):
        self.running = False


# ── Ejemplo mínimo de uso ――――――――――――――――――――――

if __name__ == "__main__":
    """Ejemplo: agente de eco (responde con lo mismo que recibe)."""
    class EchoAgent(Agent):
        def execute(self, action: str, params: dict) -> dict:
            self.emit_log("info", f"Echo: {action}", params)
            return {"echo": True, "action": action, "params": params}

    agent = EchoAgent(name=os.environ.get("AGENT_NAME", "echo-agent"))
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()
        agent.emit_log("info", "Agent stopped")
