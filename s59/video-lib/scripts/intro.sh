#!/bin/bash
# ==============================================================================
# scripts/intro.sh - Generates and iterates intro videos
# Usage: ./scripts/intro.sh <tool_name> [tool_subtitle] [target_duration]
#
# Workflow (iterativa):
#   1. Generate 5s intro → review
#   2. If good, generate 10s intro (more detail)
#   3. If good, generate 15s intro (with b-roll)
#   4. If good, generate 20s intro (full reveal)
#
# Default: starts at 5s, repeats until you approve, then escalates
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(dirname "$SCRIPT_DIR")"
PRODUCE="$LIB_DIR/bin/produce"
OUTPUT_DIR="$LIB_DIR/output"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

TOOL_NAME="${1:?Usage: ./intro.sh <tool_name> [subtitle] [target_duration]}"
TOOL_SUBTITLE="${2:-OpenCode Tool}"
TARGET_DURATION="${3:-20}"
LOG_FILE="$OUTPUT_DIR/intro_progress_${TIMESTAMP}.log"

mkdir -p "$OUTPUT_DIR"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$LOG_FILE"; }

# --- Iteration stages ---
stages=(5 10 15 20)

# Generate intro for a given duration
generate_intro() {
    local duration=$1
    local output="$OUTPUT_DIR/intro_${TOOL_NAME}_${duration}s_${TIMESTAMP}.mp4"
    local subtitle=""

    case $duration in
        5)  subtitle="Conociendo $TOOL_NAME" ;;
        10) subtitle="$TOOL_NAME — OpenCode Plugin" ;;
        15) subtitle="Contexto infinito · Memoria cross-session" ;;  # Magic Context feature
        20) subtitle="Tu agente nunca olvida · cache-aware · dreamer" ;;
    esac

    log "Generando intro de ${duration}s para '$TOOL_NAME'..."
    "$PRODUCE" intro "$TOOL_NAME" "$subtitle" "$duration"
}

# --- Main loop ---
log "=== INTRO PRODUCTION: $TOOL_NAME ==="
log "Target: ${TARGET_DURATION}s | Starting at 5s"

for duration in "${stages[@]}"; do
    [ "$duration" -gt "$TARGET_DURATION" ] && break
    log "--- STAGE: ${duration} seconds ---"

    for attempt in 1 2 3; do
        log "Attempt $attempt/3 for ${duration}s..."
        generated=$(generate_intro "$duration" 2>&1 | tail -1)
        log "Generated: $generated"
    done
done

log "=== DONE ==="
log "All intros generated in: $OUTPUT_DIR"
ls -la "$OUTPUT_DIR" | grep "intro_${TOOL_NAME}"
