#!/usr/bin/env bash
# Log de actividades del orquestador (yo)
# Uso: ./orchestrator-log.sh "mensaje"

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
TIMELINE="$PROJECT_DIR/.timeline"

MSG="${1:-Trabajando...}"
TS=$(date +%s%N | cut -c1-13)
TIME=$(date +%H:%M:%S)

echo "${TS}|${TIME}|orchestrator|WORKING|${MSG}" >> "$TIMELINE"
