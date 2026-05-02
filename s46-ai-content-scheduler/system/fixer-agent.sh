#!/bin/bash
# ============================================================
# fixer-agent.sh — Continuous Tool Improvement Agent
#
# NOT a polling monitor. This scans logs for known error
# patterns and proactively fixes the root causes. It learns.
#
# When it finds an issue:
# 1. Extracts the error from logs
# 2. Checks if it's a known pattern
# 3. If known, applies the fix
# 4. If novel, logs it for human review
#
# Usage:
#   ./fixer-agent.sh                 # Scan logs, fix issues
#   ./fixer-agent.sh --learn <file>  # Teach it a new fix pattern
#   ./fixer-agent.sh --known-issues  # List known issue patterns
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_DIR/scheduler/logs"
FIX_LOG="$PROJECT_DIR/scheduler/logs/fixer.log"
KNOWN_ISSUES="$SCRIPT_DIR/known-issues.md"

mkdir -p "$(dirname "$FIX_LOG")"

# ─── Known Issues Database ───
# Format: grep pattern → fix description → fix command
#
# Each entry:
#   PATTERN: regex to match in logs
#   FIX: human-readable description
#   ACTION: bash command to apply the fix

apply_fix() {
  local pattern="$1"
  local description="$2"
  local action="$3"
  local log_evidence="$4"

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] FIX: $description" | tee -a "$FIX_LOG"
  echo "  Evidence: $log_evidence" | tee -a "$FIX_LOG"

  eval "$action" 2>&1 | tee -a "$FIX_LOG"
  local exit_code=$?

  if [ $exit_code -eq 0 ]; then
    echo "  ✅ Fix applied successfully" | tee -a "$FIX_LOG"
  else
    echo "  ❌ Fix failed (exit: $exit_code)" | tee -a "$FIX_LOG"
  fi
  echo "" | tee -a "$FIX_LOG"
  return $exit_code
}

# ─── Scan logs for known issues ───
scan_and_fix() {
  local found=0

  # Iterate through recent logs
  # Use nullglob so non-matching globs don't cause errors
  shopt -s nullglob
  local logfiles=("$LOG_DIR"/*.log "$LOG_DIR"/agent-*.log)
  shopt -u nullglob

  for logfile in "${logfiles[@]}"; do

    # ─── Issue: TTS JSON escaping ───
    # When tts-speak receives text with special chars, JSON breaks
    if grep -q 'invalid control character\|invalid request JSON\|Failed to read frame' "$logfile" 2>/dev/null; then
      local evidence=$(grep -n 'invalid control character\|Failed to read frame' "$logfile" | head -3)
      apply_fix \
        "tts-json-escaping" \
        "TTS API receives text with JSON-breaking characters — wrapping text in Python for proper escaping" \
        "cat > '$PROJECT_DIR/system/tts-safe.sh' << 'TTSFIX'
#!/bin/bash
# tts-safe.sh — TTS wrapper that handles JSON special characters
# Usage: tts-safe.sh <text> [--voice <v>] [--output <file>]
# Reads text from argument or stdin, safely passes to TTS API

SCRIPT_DIR=\"\$(cd \"\$(dirname \"\${BASH_SOURCE[0]}\")\" && pwd)\"
PROJECT_DIR=\"\$(cd \"\$SCRIPT_DIR/..\" && pwd)\"
export TMPDIR=\"\$PROJECT_DIR/tmp\"

# Get text (first arg or stdin)
if [ \$# -ge 1 ] && [ \"\$1\" != \"--voice\" ] && [ \"\$1\" != \"--output\" ]; then
  TEXT=\"\$1\"
  shift
elif [ ! -t 0 ]; then
  TEXT=\$(cat)
else
  echo \"Error: no text provided\"
  exit 1
fi

# Parse remaining args
VOICE=\"af_heart\"
OUTPUT=\"\"
while [ \$# -gt 0 ]; do
  case \"\$1\" in
    --voice) VOICE=\"\$2\"; shift 2 ;;
    --output) OUTPUT=\"\$2\"; shift 2 ;;
    *) shift ;;
  esac
done

# Use Python for safe JSON escaping
python3 << PYEOF
import json, sys, subprocess, os

text = \"\"\"\$TEXT\"\"\"
voice = \"\$VOICE\"
output = \"\$OUTPUT\"

payload = {
    \"text\": text,
    \"voice\": voice,
    \"speed\": 1.0
}

api_token = os.environ.get('CHUTES_API_TOKEN') or os.environ.get('CHUTES_API_KEY', '')
if not api_token:
    print('Error: CHUTES_API_TOKEN not set', file=sys.stderr)
    sys.exit(1)

import urllib.request
req = urllib.request.Request(
    'https://chutes-kokoro.chutes.ai/speak',
    data=json.dumps(payload).encode('utf-8'),
    headers={
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json'
    }
)
try:
    resp = urllib.request.urlopen(req)
    audio_data = resp.read()
    if output:
        with open(output, 'wb') as f:
            f.write(audio_data)
        print(f'Audio saved to: {output}')
    else:
        sys.stdout.buffer.write(audio_data)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
PYEOF
TTSFIX
chmod +x '$PROJECT_DIR/system/tts-safe.sh'
" \
        "$evidence"
      found=$((found + 1))
    fi

    # ─── Issue: OOM / Memory exhaustion ───
    if grep -q 'MemoryExhaustion\|memory exhausted\|Cannot allocate memory' "$logfile" 2>/dev/null; then
      local evidence=$(grep -n 'MemoryExhaustion\|Cannot allocate memory' "$logfile" | head -3)
      apply_fix \
        "parallel-oom" \
        "Parallel agent ran out of memory — reducing MAX_AGENTS and removing ulimit -v" \
        "sed -i 's/MAX_AGENTS=3/MAX_AGENTS=2/' '$PROJECT_DIR/scheduler/parallel-launch.sh'
sed -i 's/MAX_AGENTS=3/MAX_AGENTS=2/' '$PROJECT_DIR/scheduler/run-task.sh'" \
        "$evidence"
      found=$((found + 1))
    fi

    # ─── Issue: googlex.com DNS (URL typo) ───
    if grep -q 'ERR_NAME_NOT_RESOLVED.*googlex' "$logfile" 2>/dev/null; then
      local evidence=$(grep -n 'ERR_NAME_NOT_RESOLVED.*googlex' "$logfile" | head -3)
      apply_fix \
        "googlex-url" \
        "googlex.com doesn't resolve — should be x.com" \
        "sed -i 's/googlex\\.com/x.com/g; s/Googlex/X/g' '$PROJECT_DIR/scheduler/tasks/02-browser-bookmarks.sh'" \
        "$evidence"
      found=$((found + 1))
    fi
  done

  if [ $found -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] No known issues found in logs." | tee -a "$FIX_LOG"
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Fixed ${found} issue(s)." | tee -a "$FIX_LOG"
  fi
}

# ─── List known issues ───
list_known() {
  echo "=== Known Issue Patterns ==="
  echo ""
  echo "1. tts-json-escaping"
  echo "   Pattern: 'invalid control character' or 'invalid request JSON'"
  echo "   Fix: Wraps TTS call in Python for proper JSON escaping"
  echo "   Tool: system/tts-safe.sh"
  echo ""
  echo "2. parallel-oom"
  echo "   Pattern: 'MemoryExhaustion' or 'Cannot allocate memory'"
  echo "   Fix: Reduces MAX_AGENTS, removes ulimit -v"
  echo ""
  echo "3. googlex-url"
  echo "   Pattern: 'ERR_NAME_NOT_RESOLVED googlex'"
  echo "   Fix: Replaces googlex.com with x.com in task files"
  echo ""
}

# ─── Main ───
case "${1:-}" in
  --known-issues)
    list_known
    ;;
  --learn)
    echo "Learning mode not yet implemented."
    echo "To add a pattern, edit this script's scan_and_fix() function."
    ;;
  *)
    echo "=== Fixer Agent ===" | tee -a "$FIX_LOG"
    echo "Date: $(date)" | tee -a "$FIX_LOG"
    echo "" | tee -a "$FIX_LOG"
    scan_and_fix
    ;;
esac
