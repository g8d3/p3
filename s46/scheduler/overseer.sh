#!/bin/bash
# ============================================================
# overseer.sh — Lightweight monitor for content agents
#
# Watches for:
# 1. Overlapping content (similar posts being generated)
# 2. Resource usage (CPU/memory to prevent crashes)
# 3. New content being produced
# 4. Dead agents that need cleanup
#
# Designed to run via cron every 30-60 minutes.
# Usage:
#   ./overseer.sh              # Full check
#   ./overseer.sh --quick      # Quick resource check only
#   ./overseer.sh --dedup      # Check for content overlap
#   ./overseer.sh --report     # Generate status report
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTENT_DIR="$PROJECT_DIR/content"
LOG_DIR="$SCRIPT_DIR/logs"
PID_DIR="$SCRIPT_DIR/.pids"
REPORT_FILE="$PROJECT_DIR/content/overseer-report.md"

# Redirect temp files to local tmp/ to avoid /tmp/ permission prompts
export TMPDIR="$PROJECT_DIR/tmp"

mkdir -p "$LOG_DIR" "$TMPDIR"
DATE_TAG=$(date +%Y-%m-%d-%H%M%S)
LOG_FILE="$LOG_DIR/overseer-${DATE_TAG}.log"

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

# --- Help ---
if [ "${1:-}" = "--help" ]; then
  echo "Usage: $0 [--quick|--dedup|--report|--cleanup]"
  exit 0
fi

# === RESOURCE CHECK ===
check_resources() {
  log "=== Resource Check ==="

  # CPU load
  local load
  load=$(uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}' | tr -d ' ')
  local cpu_cores
  cpu_cores=$(nproc)
  local threshold=$(echo "$cpu_cores * 0.8" | bc | cut -d. -f1)

  log "CPU load: $load (${cpu_cores} cores, threshold: ${threshold})"
  if [ "$(echo "$load > $threshold" | bc 2>/dev/null || echo 0)" = "1" ]; then
    log "⚠️  HIGH CPU LOAD — consider reducing parallel agents"
  fi

  # Memory
  local mem_total mem_used mem_avail mem_pct
  mem_total=$(free -m | awk '/^Mem:/ {print $2}')
  mem_used=$(free -m | awk '/^Mem:/ {print $3}')
  mem_avail=$(free -m | awk '/^Mem:/ {print $7}')
  mem_pct=$((mem_used * 100 / mem_total))

  log "Memory: ${mem_used}MB/${mem_total}MB used (${mem_pct}%), available: ${mem_avail}MB"
  if [ "$mem_pct" -gt 90 ]; then
    log "⚠️  HIGH MEMORY USAGE — risk of OOM"
  fi

  # Disk
  local disk_pct
  disk_pct=$(df -h "$PROJECT_DIR" | awk 'NR==2 {print $5}' | tr -d '%')
  log "Disk: ${disk_pct}% used on $(df -h "$PROJECT_DIR" | awk 'NR==2 {print $6}')"
  if [ "$disk_pct" -gt 85 ]; then
    log "⚠️  DISK SPACE LOW — ${disk_pct}% used"
  fi

  # OpenCode processes
  local oc_count
  oc_count=$(pgrep -c opencode 2>/dev/null || echo 0)
  log "OpenCode processes: $oc_count"

  # Temperature (if sensors available)
  if command -v sensors &>/dev/null; then
    local temp
    temp=$(sensors 2>/dev/null | grep -oP 'Package id 0:\s+\+\K[0-9.]+' | head -1 || true)
    if [ -n "$temp" ]; then
      log "CPU temp: ${temp}°C"
      if [ "$(echo "$temp > 80" | bc 2>/dev/null || echo 0)" = "1" ]; then
        log "⚠️  HIGH CPU TEMPERATURE — ${temp}°C"
      fi
    fi
  fi

  return 0
}

# === CONTENT OVERLAP CHECK ===
check_dedup() {
  log "=== Content Overlap Check ==="

  local posts_dir="$CONTENT_DIR/posts"
  if [ ! -d "$posts_dir" ]; then
    log "No posts directory yet"
    return 0
  fi

  local files=()
  while IFS= read -r f; do
    files+=("$f")
  done < <(ls -t "$posts_dir"/*.txt 2>/dev/null | head -20)

  local count=${#files[@]}
  if [ "$count" -lt 2 ]; then
    log "Only $count post(s) — not enough to compare"
    return 0
  fi

  log "Comparing $count recent posts for overlap..."

  local overlap_found=0
  for ((i = 0; i < count; i++)); do
    for ((j = i + 1; j < count; j++)); do
      local f1="${files[$i]}"
      local f2="${files[$j]}"
      local name1=$(basename "$f1")
      local name2=$(basename "$f2")

      # Simple word-level comparison
      local words1 words2 common total
      words1=$(tr -s '[:space:]' '\n' < "$f1" | tr '[:upper:]' '[:lower:]' | sort -u | wc -l)
      words2=$(tr -s '[:space:]' '\n' < "$f2" | tr '[:upper:]' '[:lower:]' | sort -u | wc -l)
      common=$(comm -12 \
        <(tr -s '[:space:]' '\n' < "$f1" | tr '[:upper:]' '[:lower:]' | sort -u) \
        <(tr -s '[:space:]' '\n' < "$f2" | tr '[:upper:]' '[:lower:]' | sort -u) \
        | wc -l)

      # Jaccard similarity
      total=$((words1 + words2 - common))
      if [ "$total" -gt 0 ]; then
        local similarity=$((common * 100 / total))
        if [ "$similarity" -gt 60 ]; then
          log "⚠️  HIGH OVERLAP (${similarity}%): $name1 ↔ $name2"
          overlap_found=1
        elif [ "$similarity" -gt 40 ]; then
          log "  MODERATE OVERLAP (${similarity}%): $name1 ↔ $name2"
        fi
      fi
    done
  done

  if [ "$overlap_found" = "0" ]; then
    log "✅ No significant overlap detected"
  fi

  return $overlap_found
}

# === CLEANUP DEAD AGENTS ===
cleanup_agents() {
  log "=== Agent Cleanup ==="
  local cleaned=0

  if [ -d "$PID_DIR" ]; then
    for pidfile in "$PID_DIR"/*.pid; do
      [ -f "$pidfile" ] || continue
      pid=$(cat "$pidfile")
      if ! kill -0 "$pid" 2>/dev/null; then
        name=$(basename "$pidfile" .pid)
        log "Cleaning up dead agent: $name (PID: $pid)"
        rm -f "$pidfile"
        cleaned=$((cleaned + 1))
      fi
    done
  fi

  # Remove stale PID files (> 24 hours)
  find "$PID_DIR" -name '*.pid' -mtime +1 -delete 2>/dev/null

  log "Cleaned $cleaned dead agent(s)"
}

# === GENERATE REPORT ===
generate_report() {
  log "=== Generating Status Report ==="

  cat > "$REPORT_FILE" << 'EOF'
# Overseer Report
EOF

  echo "" >> "$REPORT_FILE"
  echo "Generated: $(date)" >> "$REPORT_FILE"
  echo "" >> "$REPORT_FILE"

  # Content counts
  local post_count audio_count
  post_count=$(find "$CONTENT_DIR/posts" -name '*.txt' 2>/dev/null | wc -l)
  audio_count=$(find "$CONTENT_DIR/audio" -name '*.mp3' -o -name '*.wav' 2>/dev/null | wc -l)

  cat >> "$REPORT_FILE" << EOF
## Content Stats

| Type | Count |
|------|-------|
| Posts | $post_count |
| Audio files | $audio_count |

EOF

  # Resource summary
  local load mem_avail disk_pct
  load=$(uptime | awk -F'load average:' '{print $2}' | awk -F',' '{print $1}' | tr -d ' ')
  mem_avail=$(free -m | awk '/^Mem:/ {print $7}')
  disk_pct=$(df -h "$PROJECT_DIR" | awk 'NR==2 {print $5}')

  cat >> "$REPORT_FILE" << EOF
## System Resources

| Metric | Value |
|--------|-------|
| CPU Load | $load |
| Available Memory | ${mem_avail}MB |
| Disk Usage | $disk_pct |

EOF

  # Recent content
  echo "## Recent Posts" >> "$REPORT_FILE"
  echo "" >> "$REPORT_FILE"
  for f in $(ls -t "$CONTENT_DIR/posts"/*.txt 2>/dev/null | head -5); do
    local name size date
    name=$(basename "$f" .txt)
    size=$(wc -c < "$f")
    date=$(stat -c '%y' "$f" | cut -d. -f1)
    echo "- **${name}** (${size} bytes, ${date})" >> "$REPORT_FILE"
  done

  echo "" >> "$REPORT_FILE"
  log "Report saved to: $REPORT_FILE"
}

# === MAIN ===
case "${1:-}" in
  --quick)
    check_resources
    ;;
  --dedup)
    check_dedup
    ;;
  --cleanup)
    cleanup_agents
    ;;
  --report)
    check_resources
    check_dedup
    cleanup_agents
    generate_report
    ;;
  *)
    log "=== Overseer Run ==="
    check_resources
    check_dedup
    cleanup_agents
    log "=== Done ==="
    ;;
esac
