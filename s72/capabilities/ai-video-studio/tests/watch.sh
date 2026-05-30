#!/bin/bash
# watch.sh — Monitorea la ventana 0 y corre tests cuando hay cambios
# Modo de uso: bash test-reports/watch.sh &
# Esto corre en background y detecta cambios en window 0

WINDOW="main:0"
HARNESS="python3.12 /home/vuos/code/p3/s72/test-reports/harness.py"
REPORTS="/home/vuos/code/p3/s72/test-reports"
LAST_HASH=""

echo "[watch] Monitoreando ventana $WINDOW por cambios..."

while true; do
  # Capturar contenido actual de window 0
  CONTENT=$(tmux capture-pane -t $WINDOW -p -S -50 2>/dev/null)
  HASH=$(echo "$CONTENT" | md5sum | cut -d' ' -f1)

  if [ "$HASH" != "$LAST_HASH" ]; then
    if [ -n "$LAST_HASH" ]; then
      echo "[watch] $(date '+%H:%M:%S') — Cambio detectado en window 0"

      # Extraer mensajes nuevos (diff simple)
      echo "$CONTENT" | grep -iE '(✓|❌|error|fail|test|commit|push|deploy|listo|completado)' | tail -5

      # Correr tests automáticos
      echo "[watch] Ejecutando test suite..."
      $HARNESS 2>&1 | tail -10

      # Generar timestamp report
      TS=$(date '+%Y%m%d-%H%M%S')
      $HARNESS > "$REPORTS/auto-$TS.txt" 2>&1
      echo "[watch] Reporte guardado: auto-$TS.txt"
    fi
    LAST_HASH="$HASH"
  fi

  sleep 5
done
