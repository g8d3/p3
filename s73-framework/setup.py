#!/usr/bin/env python3.12
"""Entry point del framework. Inicializa estructura y lanza el Orchestrator."""

import os
import sys
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))


def cmd(description: str, *args, **kwargs):
    print(f"  → {description}...")
    result = subprocess.run(*args, **kwargs, cwd=BASE)
    if result.returncode != 0:
        print(f"  ❌ Failed (exit {result.returncode})")
        sys.exit(result.returncode)
    return result


def main():
    print("╭──────────────────────────────────────────────╮")
    print("│  Framework Multi-Agente                      │")
    print("│  Inicialización                             │")
    print("╰──────────────────────────────────────────────╯")
    print()

    # 1. Crear directorios
    for d in ["inbox", "outbox", "shared", "data", "logs"]:
        os.makedirs(os.path.join(BASE, d), exist_ok=True)
        print(f"  ✓ {d}/")

    # 2. Instalar dependencias
    print()
    req_path = os.path.join(BASE, "requirements.txt")
    if os.path.exists(req_path):
        cmd("Instalando dependencias Python",
            [sys.executable, "-m", "pip", "install", "-q", "-r", req_path])

    # 3. Inicializar config si no existe
    cfg_path = os.path.join(BASE, "config.yaml")
    if not os.path.exists(cfg_path):
        cmd("Generando config.yaml",
            [sys.executable, "-c", "import orchestrator; orchestrator.main()", "--init"])

    # 4. Arrancar
    print()
    print("  ✓ Listo. Para iniciar el Orchestrator:")
    print()
    print(f"    cd {BASE}")
    print("    python3.12 -m orchestrator")
    print()
    print("  O en modo foreground:")
    print(f"    python3.12 -m orchestrator &")
    print()
    print("  Web UI: http://localhost:9877")
    print()


if __name__ == "__main__":
    main()
