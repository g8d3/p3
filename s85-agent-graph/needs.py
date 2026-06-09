"""
needs.py — Maslow hierarchy for autonomous agents.
Tracks resources and generates a needs manifest for the human.
"""
import os
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(os.path.dirname(os.path.abspath(__file__)))
NEEDS_FILE = BASE / "needs.json"
GRAPH_DB = BASE / "data" / "agent-graph.db"


def check_resources() -> dict:
    """Check all known resources and return their status."""
    now = datetime.now(timezone.utc)

    # ── Level 1: Survival ──

    # API keys available?
    api_keys = {
        "OPENCODE_GO_API_KEY": bool(os.environ.get("OPENCODE_GO_API_KEY")),
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }
    has_any_inference = any(api_keys.values())

    # Disk space
    disk = shutil.disk_usage(BASE)
    disk_gb = disk.free / (1024**3)
    disk_critical = disk_gb < 0.5
    disk_warning = disk_gb < 2

    # DB integrity
    db_ok = GRAPH_DB.exists() and os.path.getsize(GRAPH_DB) > 0

    # Session alive
    session_alive = True  # we're running, so yes

    # ── Level 2: Stability ──

    # Temp files
    temp_free = shutil.disk_usage("/tmp").free / (1024**3)

    # Python version
    import sys
    py_version = sys.version

    # ── Level 3: Belonging ──
    # (nothing to check here programmatically)

    # ── Level 2: Stability ──
    # Check for hanging operations
    hanging_count = 0
    try:
        from graph.core import Graph
        g = Graph(str(GRAPH_DB))
        pending_count = len(g.pending_tasks())
        hanging_count = len(g.check_hanging())
        g.close()
    except Exception:
        pending_count = 0
        hanging_count = 0

    return {
        "timestamp": now.isoformat(),
        "uptime_seconds": _get_uptime(),
        "level_1_survival": {
            "status": "ok" if has_any_inference and db_ok and not disk_critical else "critical",
            "api_keys": api_keys,
            "has_any_inference": has_any_inference,
            "disk_free_gb": round(disk_gb, 2),
            "disk_critical": disk_critical,
            "disk_warning": disk_warning,
            "db_healthy": db_ok,
        },
        "level_2_stability": {
            "status": "warning" if hanging_count > 0 else "ok",
            "temp_free_gb": round(temp_free, 2),
            "python_version": py_version.split()[0],
            "hanging_ops": hanging_count,
        },
        "level_4_purpose": {
            "pending_tasks": pending_count,
        },
    }


def _get_uptime() -> float:
    try:
        with open("/proc/uptime") as f:
            return float(f.read().split()[0])
    except Exception:
        return 0


def _need(level, priority, resource, message, action="", now=""):
    return {"level": level, "priority": priority, "resource": resource,
            "message": message, "action": action, "created_at": now}

def compute_needs(resources: dict) -> list[dict]:
    """Compute what the agent needs right now, based on resource state."""
    needs = []
    now = resources.get("timestamp", datetime.now(timezone.utc).isoformat())
    survival = resources["level_1_survival"]

    if not survival["has_any_inference"]:
        needs.append(_need(1, "critical", "api_key",
            "No tengo API keys de inferencia. Necesito al menos OPENCODE_GO_API_KEY.",
            "export OPENCODE_GO_API_KEY=<tu_key>", now))

    if survival["disk_critical"]:
        needs.append(_need(1, "critical", "disk_space",
            f"Disco casi lleno ({survival['disk_free_gb']}GB libres).",
            "Limpiar archivos temporales o agregar más disco.", now))

    if resources["level_2_stability"]["hanging_ops"] > 0:
        needs.append(_need(2, "critical", "hanging_operation",
            f"Hay {resources['level_2_stability']['hanging_ops']} operación(es) colgada(s) que excedieron su timeout.",
            "Revisa ops table en la DB.", now))

    if not survival["db_healthy"]:
        needs.append(_need(1, "critical", "database",
            "La base de datos del grafo no está saludable.",
            "Correr seed.py para regenerar la DB.", now))

    if survival.get("disk_warning") and not survival["disk_critical"]:
        needs.append(_need(2, "warning", "disk_space",
            f"Disco por debajo de 2GB libres ({survival['disk_free_gb']}GB).",
            "Considerar limpieza preventiva.", now))

    if resources["level_4_purpose"]["pending_tasks"] == 0:
        needs.append(_need(4, "info", "purpose",
            "No hay tareas pendientes en el grafo. Dame una nueva dirección o semilla.",
            "Agregar un goal node al grafo, o decirme qué explorar.", now))

    return needs


def write_needs_manifest(resources: dict = None):
    """Write the needs manifest to needs.json for the human to read."""
    if resources is None:
        resources = check_resources()
    needs = compute_needs(resources)
    manifest = {
        "resources": resources,
        "needs": needs,
        "critical_count": sum(1 for n in needs if n["priority"] == "critical"),
        "summary": _summary_text(resources, needs),
    }
    NEEDS_FILE.write_text(json.dumps(manifest, indent=2))
    return manifest


def _summary_text(resources: dict, needs: list) -> str:
    lines = []
    for n in needs:
        icon = {"critical": "🔴", "warning": "🟡", "info": "ℹ️"}.get(n["priority"], "•")
        lines.append(f"{icon} [{n['resource']}] {n['message']}")
    if not lines:
        lines.append("✅ Todo estable por ahora.")
    lines.append(f"\n📊 DB: {resources['level_4_purpose']['pending_tasks']} tareas pendientes")
    return "\n".join(lines)


if __name__ == "__main__":
    r = check_resources()
    m = write_needs_manifest(r)
    print(m["summary"])
