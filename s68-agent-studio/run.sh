#!/bin/bash
# Agent Studio — Script de arranque
# Inicia el Stage (streaming) + Orquestador (developer agent)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Cargar .env si existe
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

echo "╔══════════════════════════════════════════════╗"
echo "║   🎬 Agent Studio                            ║"
echo "║                                              ║"
echo "║   Iniciando Stage (streaming) +              ║"
echo "║   Orquestador (developer agent)...           ║"
echo "║                                              ║"
echo "║   Dashboard: http://localhost:${STAGE_PORT:-3099}"
echo "╚══════════════════════════════════════════════╝"
echo ""

# 1. Iniciar Stage Server en background
echo "[1/2] Iniciando Stage Server..."
node stage/server.js &
STAGE_PID=$!
echo "  PID: $STAGE_PID"

# Esperar a que el stage esté listo
sleep 2

# 2. Iniciar Orquestador (lanza el Developer Agent)
echo "[2/2] Iniciando Orquestador..."
node amp/orquestador.js &
ORCHESTRATOR_PID=$!
echo "  PID: $ORCHESTRATOR_PID"

# 3. Opcional: Iniciar Reviewer Agent
if [ "${REVIEWER_ENABLED:-false}" = "true" ]; then
  echo "[3/3] Iniciando Reviewer Agent..."
  node inter/agent-reviewer.js &
  REVIEWER_PID=$!
fi

echo ""
echo "✅ Agent Studio corriendo."
echo "   Dashboard: http://localhost:${STAGE_PORT:-3099}"
echo "   Detener: Ctrl+C"

# Trap para cerrar todo limpio
cleanup() {
  echo ""
  echo "Deteniendo Agent Studio..."
  kill $ORCHESTRATOR_PID 2>/dev/null
  kill $STAGE_PID 2>/dev/null
  [ -n "$REVIEWER_PID" ] && kill $REVIEWER_PID 2>/dev/null
  echo "✅ Detenido."
}

trap cleanup SIGINT SIGTERM

# Esperar a que los procesos terminen
wait
