#!/usr/bin/env bash
# ── Continuous Content Agent ──────────────────────────────────────────────
# Runs the pipeline non-stop: fetches trending news → generates video →
# splits into shorts → uploads. Designed for cron or tmux.
#
# Usage:
#   ./agent.sh                  # Run once
#   ./agent.sh --loop           # Run continuously (every 4h)
#   ./agent.sh --loop --interval 3600   # Every hour
#   ./agent.sh --schedule-cron  # Install as cron job (3x daily)
#   ./agent.sh --once --topic "Custom topic"  # One-off with custom topic
# ──────────────────────────────────────────────────────────────────────────

set -euo pipefail
cd "$(dirname "$0")"
WORK="work"; mkdir -p "$WORK"
LOG="$WORK/agent.log"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

generate() {
    local topic="${1:-}"
    local skip_upload="${2:-}"

    log "=== Starting generation ==="

    if [ -n "$topic" ]; then
        CMD="--skip-upload"
        [ -z "$skip_upload" ] && CMD=""
        log "Topic: $topic"
        PYTHONDONTWRITEBYTECODE=1 python3 pipeline.py --topic "$topic" $CMD 2>&1 | tee -a "$LOG"
    else
        log "Fetching from news..."
        python3 pipeline.py --news --skip-upload 2>&1 | tee -a "$LOG"
    fi

    log "=== Generation complete ==="
}

# ── Modes ─────────────────────────────────────────────────────────────────
case "${1:-}" in
    --loop)
        interval="${2:-14400}"  # default: 4 hours
        log "Continuous mode: every ${interval}s"
        while true; do
            generate
            log "Sleeping ${interval}s..."; sleep "$interval"
        done
        ;;
    --schedule-cron)
        SCRIPT="$(realpath "$0")"
        CRON="0 */6 * * * cd $(realpath .) && python3 pipeline.py --news 2>&1 >> $LOG"
        (crontab -l 2>/dev/null | grep -v "$SCRIPT"; echo "$CRON") | crontab -
        log "Cron installed: $CRON"
        crontab -l
        ;;
    --once)
        shift
        topic="${1:-}"
        generate "$topic"
        ;;
    *)
        # Default: run once with news
        generate "" "--skip-upload"
        ;;
esac
