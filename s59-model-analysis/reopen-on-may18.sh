#!/bin/zsh
# reopen-on-may18.sh — Reabre el issue #4506 y se limpia del crontab
# Programado via cron para el 18 de mayo de 2026

LOG="/tmp/pi-reopen.log"
TOKEN="${PI_REOPEN_TOKEN:?Variable PI_REOPEN_TOKEN no definida}"
REPO="earendil-works/pi"
ISSUE="4506"

echo "[$(date)] Ejecutando reopen-on-may18.sh..." >> "$LOG"

# 1. Reabrir el issue
curl -sL -X PATCH \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"state":"open"}' \
  "https://api.github.com/repos/$REPO/issues/$ISSUE" | jq '{ state: .state, number: .number }' >> "$LOG" 2>&1

# 2. Agregar comentario recordatorio
curl -sL -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"body":"Reopened automatically after the refactor freeze period (2026-05-17). The full bug report with fix and diagnostics is above."}' \
  "https://api.github.com/repos/$REPO/issues/$ISSUE/comments" >> "$LOG" 2>&1

echo "[$(date)] Issue reabierto. Limpiando crontab..." >> "$LOG"

# 3. Auto-limpiarse del crontab
crontab -l 2>/dev/null | grep -v "reopen-on-may18.sh" | crontab -

echo "[$(date)] Limpieza completa." >> "$LOG"
