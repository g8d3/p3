#!/bin/bash
# scripts/demo.sh - Full demo production pipeline for a tool
# Usage: ./scripts/demo.sh <tool_name> <github_url> [demo_script]
#
# Pipeline:
#   1. Fetches tool README/docs
#   2. Generates script from docs (via DeepSeek/Qwen)
#   3. Generates voiceover (TTS)
#   4. Guides recording session
#   5. Composes final video with intro/outro
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(dirname "$SCRIPT_DIR")"
PRODUCE="$LIB_DIR/bin/produce"
OUTPUT_DIR="$LIB_DIR/output"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

TOOL_NAME="${1:?Usage: ./demo.sh <tool_name> <github_url>}"
GITHUB_URL="${2:-}"
TIMING_FILE="$OUTPUT_DIR/timing_${TOOL_NAME}_${TIMESTAMP}.txt"

mkdir -p "$OUTPUT_DIR"

log()   { echo "[$(date +%H:%M:%S)] $*"; }
logc()  { echo -e "\n=== $* ==="; }

# === Step 1: Fetch docs ===
logc "FETCHING DOCS"
if [ -n "$GITHUB_URL" ]; then
    if command -v gh &>/dev/null; then
        gh repo view "$(basename "$GITHUB_URL" .git)" --json description >> "$OUTPUT_DIR/tool_info_${TIMESTAMP}.json"
    fi
    log "Tool URL: $GITHUB_URL"
fi

# === Step 2: Generate script ===
logc "GENERATING SCRIPT"
SCRIPT_TEXT=$("$PRODUCE" script "$TOOL_NAME" "Tool from $GITHUB_URL")
echo "$SCRIPT_TEXT" > "$OUTPUT_DIR/script_${TOOL_NAME}_${TIMESTAMP}.txt"
log "Script saved to output/"

# === Step 3: Generate voiceover ===
logc "GENERATING VOICEOVER"
# Extract just the text lines from the script (lines with TEXTO_VOZ)
VOICEOVER_TEXT=$(echo "$SCRIPT_TEXT" | grep -i "TEXTO_VOZ" | sed 's/.*TEXTO_VOZ\]:\s*//i' | tr '\n' ' ')
if [ -z "$VOICEOVER_TEXT" ]; then
    VOICEOVER_TEXT="${TOOL_NAME}: $(echo "$SCRIPT_TEXT" | head -3)"
fi
VOICEOVER_FILE=$("$PRODUCE" tts "$VOICEOVER_TEXT")
log "Voiceover: $VOICEOVER_FILE"

# === Step 4: Record timing guide ===
logc "RECORDING GUIDE"
echo "=== TIMING GUIDE: $TOOL_NAME ===" > "$TIMING_FILE"
echo "$SCRIPT_TEXT" >> "$TIMING_FILE"
echo "" >> "$TIMING_FILE"
echo "--- Quick commands during recording ---" >> "$TIMING_FILE"
echo "  Ctrl+Shift+R  : start/stop recording" >> "$TIMING_FILE"
echo "  Ctrl+Shift+T  : mark timestamp" >> "$TIMING_FILE"
echo "  Ctrl+C        : abort" >> "$TIMING_FILE"
cat "$TIMING_FILE"

# === Step 5: Generate intro ===
logc "GENERATING INTRO"
INTRO_FILE=$(PROJECT_NAME="$TOOL_NAME" "$PRODUCE" intro "$TOOL_NAME" "Video Tutorial" 5)
log "Intro: $INTRO_FILE"

# === Summary ===
logc "READY TO RECORD"
echo ""
echo "  Tool:    $TOOL_NAME"
echo "  Script:  less output/script_${TOOL_NAME}_${TIMESTAMP}.txt"
echo "  Voice:   $VOICEOVER_FILE"
echo "  Timing:  $TIMING_FILE"
echo "  Intro:   $INTRO_FILE"
echo ""
echo "  Next:    ./bin/record 30   (record the demo)"
echo ""
