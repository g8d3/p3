#!/usr/bin/env bash
# agent-worker.sh — Runs Crush in REPL mode to execute implementation tasks.
# Communicates with coordinator (window 0) via bus files.
# Coordinator: writes tasks to bus/task.md
# Worker: writes results to bus/report.md, status to bus/status.md

BUS=/home/vuos/code/p3/s70/bus
mkdir -p "$BUS"
cd /home/vuos/code

echo "🚀 Worker agent started at $(date -Iseconds)" | tee "$BUS/report.md"
echo "idle" > "$BUS/status.md"

# The worker runs Crush interactively.
# Coordinator communicates via tmux send-keys.
# Worker reports back by writing to bus files.

echo ""
echo "=== WORKER AGENT ==="
echo "I execute implementation tasks for the coordinator."
echo "Write task descriptions to: $BUS/task.md"
echo "I'll write results to: $BUS/report.md"
echo "===================="
echo ""

# Start Crush REPL
OPENAI_API_KEY="$OPENAI_API_KEY" \
exec /home/vuos/.local/share/pi-node/current/bin/crush \
  --provider openai \
  --model gpt-4o \
  --system "Eres un worker agent de implementación. Tu función es ejecutar tareas técnicas concretas.

REGLAS:
1. Ejecutas la tarea que te den, sin desviarte
2. Reportas resultados a /home/vuos/code/p3/s70/bus/report.md
3. Si necesitas más información, la pides explícitamente
4. Si algo falla, reportas el error y qué intentaste
5. No filosofas, no propones cambios no solicitados — ejecutas"
