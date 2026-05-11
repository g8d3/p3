#!/usr/bin/env python3
"""
Agent Data Writer
=================
Módulo para que el ORQUESTRADOR (yo) escriba datos de agentes en CSVs.
Tú corres `monitor.py` para ver los datos en tiempo real.

Uso (desde el orquestrador):
    from writer import AgentWriter
    w = AgentWriter()
    w.upsert_agent("agent_001", name="Worker", status="active", ...)
    w.add_task("agent_001", "Procesar video", status="in_progress")
    w.add_log("agent_001", "task_001", "INFO", "Iniciando procesamiento")
"""

from __future__ import annotations

import csv
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"

# ── Lock global para escritura thread-safe ────────────────────────
_lock = threading.Lock()


class AgentWriter:
    """Escribe datos de agentes en CSVs dentro de data/."""

    def __init__(self, data_dir: str | Path = DATA_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # Inicializar contadores desde datos existentes
        self._init_counters()

    def _init_counters(self):
        """Lee los archivos existentes para inicializar los contadores
        de task_id y log_id, evitando duplicados entre invocaciones."""
        tasks = self._read("tasks.csv")
        max_t = 0
        for t in tasks:
            tid = t.get("task_id", "")
            if tid.startswith("task_"):
                try:
                    n = int(tid.split("_")[1])
                    if n > max_t:
                        max_t = n
                except (IndexError, ValueError):
                    pass
        AgentWriter._task_counter = max_t

        logs = self._read("logs.csv")
        max_l = 0
        for l in logs:
            lid = l.get("log_id", "")
            if lid.startswith("log_"):
                try:
                    n = int(lid.split("_")[1])
                    if n > max_l:
                        max_l = n
                except (IndexError, ValueError):
                    pass
        AgentWriter._log_counter = max_l

    # ── Agentes ────────────────────────────────────────────────

    def upsert_agent(
        self,
        agent_id: str,
        name: str = "",
        role: str = "",
        status: str = "idle",
        model: str = "",
    ) -> dict:
        """Crea o actualiza un agente. Devuelve el registro."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        rows = self._read("agents.csv")
        existing = [r for r in rows if r["agent_id"] == agent_id]

        if existing:
            agent = existing[0]
            if name:    agent["name"] = name
            if role:    agent["role"] = role
            if status:  agent["status"] = status
            if model:   agent["model"] = model
            agent["updated_at"] = now
        else:
            agent = {
                "agent_id": agent_id,
                "name":     name or agent_id,
                "role":     role,
                "status":   status,
                "model":    model,
                "created_at": now,
                "updated_at": now,
            }
            rows.append(agent)

        self._write("agents.csv", rows)
        return agent

    def get_agent(self, agent_id: str) -> dict | None:
        rows = self._read("agents.csv")
        for r in rows:
            if r["agent_id"] == agent_id:
                return r
        return None

    def list_agents(self) -> list[dict]:
        return self._read("agents.csv")

    # ── Tareas ─────────────────────────────────────────────────

    _task_counter = 0

    def add_task(
        self,
        agent_id: str,
        description: str,
        parent_task_id: str = "",
        status: str = "pending",
        priority: str = "medium",
    ) -> dict:
        """Añade una tarea a un agente. Devuelve el registro."""
        AgentWriter._task_counter += 1
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        task_id = f"task_{AgentWriter._task_counter:03d}"

        task = {
            "task_id":        task_id,
            "agent_id":       agent_id,
            "parent_task_id": parent_task_id,
            "description":    description,
            "status":         status,
            "priority":       priority,
            "started_at":     now if status in ("in_progress", "active", "running") else "",
            "completed_at":   "",
            "result":         "",
        }
        rows = self._read("tasks.csv")
        rows.append(task)
        self._write("tasks.csv", rows)
        return task

    def update_task(self, task_id: str, **fields) -> dict | None:
        """Actualiza campos de una tarea."""
        rows = self._read("tasks.csv")
        for r in rows:
            if r["task_id"] == task_id:
                now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
                if "status" in fields:
                    new_st = fields["status"]
                    if new_st in ("in_progress", "active", "running") and not r["started_at"]:
                        r["started_at"] = now
                    if new_st in ("completed", "success", "failure", "error"):
                        r["completed_at"] = now
                for k, v in fields.items():
                    r[k] = v
                self._write("tasks.csv", rows)
                return r
        return None

    # ── Logs ───────────────────────────────────────────────────

    _log_counter = 0

    def add_log(
        self,
        agent_id: str,
        task_id: str = "",
        level: str = "INFO",
        message: str = "",
    ) -> dict:
        """Añade una entrada de log."""
        AgentWriter._log_counter += 1
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        log_id = f"log_{AgentWriter._log_counter:04d}"

        entry = {
            "log_id":    log_id,
            "agent_id":  agent_id,
            "task_id":   task_id,
            "timestamp": now,
            "level":     level.upper(),
            "message":   message,
        }
        rows = self._read("logs.csv")
        rows.append(entry)
        self._write("logs.csv", rows)
        return entry

    # ── IO con lock ────────────────────────────────────────────

    def _read(self, filename: str) -> list[dict]:
        path = self.data_dir / filename
        if not path.exists():
            return []
        with _lock:
            with open(path, newline="") as f:
                reader = csv.DictReader(f)
                return list(reader)

    def _write(self, filename: str, rows: list[dict]) -> None:
        path = self.data_dir / filename
        if not rows:
            path.unlink(missing_ok=True)
            return
        with _lock:
            fieldnames = list(rows[0].keys())
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)


# ── Demo / auto-ejemplo ──────────────────────────────────────────

def demo():
    """Genera datos de ejemplo."""
    from pathlib import Path
    import shutil

    # Limpiar data/
    data_dir = Path(__file__).parent / "data"
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir()

    w = AgentWriter(data_dir)

    # Crear agentes
    w.upsert_agent("orchestrator_01", name="Orchestrator", role="coordinator", status="active", model="gpt-4o")
    w.upsert_agent("coder_01", name="CodeAgent", role="developer", status="in_progress", model="claude-4")
    w.upsert_agent("vision_01", name="VisionMonitor", role="screen_observer", status="active", model="gpt-4o-vision")
    w.upsert_agent("logger_01", name="DataLogger", role="logging", status="idle", model="local")

    # Tareas del orquestrador
    t1 = w.add_task("orchestrator_01", "Coordinar pipeline de video", status="in_progress", priority="high")
    w.add_log("orchestrator_01", t1["task_id"], "INFO", "Pipeline de video iniciado")
    w.add_log("orchestrator_01", t1["task_id"], "INFO", "Asignando CodeAgent para generación de código")

    # Tareas del coder
    t2 = w.add_task("coder_01", "Generar script de automatización", status="in_progress", priority="high")
    w.add_log("coder_01", t2["task_id"], "INFO", "Analizando requisitos del script")
    w.add_log("coder_01", t2["task_id"], "INFO", "Generando código Python para automatización")
    w.add_log("coder_01", t2["task_id"], "WARN", "Dependencia no encontrada: ffmpeg")

    t2_child = w.add_task("coder_01", "Instalar ffmpeg", parent_task_id=t2["task_id"], status="in_progress")
    w.add_log("coder_01", t2_child["task_id"], "INFO", "Descargando ffmpeg...")
    w.add_log("coder_01", t2_child["task_id"], "ERROR", "ffmpeg download failed: connection timeout")
    w.add_log("coder_01", t2_child["task_id"], "ERROR", "Retry attempt 2/3 failed")

    w.update_task(t2_child["task_id"], status="error")

    t2_child2 = w.add_task("coder_01", "Implementar fallback sin ffmpeg",
                           parent_task_id=t2["task_id"], status="pending")
    w.add_log("coder_01", t2_child2["task_id"], "WARN", "Usando captura con PIL como alternativa")

    # Tareas del vision monitor
    t3 = w.add_task("vision_01", "Monitorear escritorio", status="active", priority="medium")
    w.add_log("vision_01", t3["task_id"], "INFO", "Capturando screenshot del escritorio")
    w.add_log("vision_01", t3["task_id"], "INFO", "Analizando 12 elementos UI detectados")
    w.add_log("vision_01", t3["task_id"], "WARN", "Ventana de OBS no visible en accesibilidad")
    w.add_log("vision_01", t3["task_id"], "INFO", "Usando visión directa para localizar OBS")

    t3_child = w.add_task("vision_01", "Localizar botón de grabación",
                          parent_task_id=t3["task_id"], status="in_progress")
    w.add_log("vision_01", t3_child["task_id"], "INFO", "Escaneando región inferior de la pantalla")
    w.add_log("vision_01", t3_child["task_id"], "INFO", "Botón de grabación detectado en (920, 980)")
    w.add_log("vision_01", t3_child["task_id"], "INFO", "Coordenadas confirmadas, listo para clic")

    w.update_task(t3_child["task_id"], status="completed", result="Button found at (920, 980)")

    # Logger idle
    w.add_log("logger_01", "", "INFO", "Esperando datos para procesar...")

    print("✅ Demo data generated in data/")
    print(f"   Agents: {len(w.list_agents())}")
    print(f"   Tasks:  {len(w._read('tasks.csv'))}")
    print(f"   Logs:   {len(w._read('logs.csv'))}")


if __name__ == "__main__":
    demo()
