#!/bin/bash
# Quick-start: setup everything with one command
# Usage: bash <(curl -fsSL https://raw.githubusercontent.com/.../quickstart.sh)
# Or:  ./quickstart.sh
set -euo pipefail

echo "=== Video Production Library - Quick Start ==="
echo ""

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$LIB_DIR"

# 1. Check dependencies
echo "[1/4] Checking dependencies..."
DEPS_MISSING=0
for cmd in ffmpeg ffprobe curl jq; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "  MISSING: $cmd"
        DEPS_MISSING=$((DEPS_MISSING + 1))
    fi
done

if [ "$DEPS_MISSING" -gt 0 ]; then
    echo "  Installing missing dependencies..."
    sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg jq curl 2>/dev/null
fi
echo "  Dependencies: OK"

# 2. Generate sound effects
echo ""
echo "[2/4] Generating sound effects..."
bash scripts/generate-sfx.sh 2>/dev/null
echo "  SFX: OK"

# 3. Test intro generation
echo ""
echo "[3/4] Testing intro generation..."
INTRO_FILE=$(bash bin/produce intro "Video Production" "Test" 3 2>/dev/null | grep "^$LIB_DIR/output/" | tail -1)
if [ -n "$INTRO_FILE" ] && [ -f "$INTRO_FILE" ]; then
    DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$INTRO_FILE" 2>/dev/null)
    echo "  Intro: OK (${DUR}s, 1920x1080)"
else
    echo "  Intro: FAILED"
fi

# 4. Check API keys
echo ""
echo "[4/4] API Keys:"
if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
    echo "  DEEPSEEK_API_KEY: ✓ set"
else
    echo "  DEEPSEEK_API_KEY: ✗ not set (needed for script generation)"
    echo "    → export DEEPSEEK_API_KEY='sk-...'"
fi

echo ""
echo "=== Ready ==="
echo ""
echo "Commands:"
echo "  bin/produce intro <name> [subtitle] [secs]   Create intro video"
echo "  bin/produce script <tool> [desc] [url]       Generate script from tool info"
echo "  bin/produce tts <text>                       Generate voiceover audio"
echo "  bin/produce record <secs>                    Record screen"
echo "  bin/produce sfx <video> <sfx> [at_sec]       Add sound effect"
echo "  bin/produce transition <v1> <v2> [type]      Transition between clips"
echo "  bin/produce compose [dir]                    Compose final video"
echo ""
echo "Quick demo:"
echo "  scripts/intro.sh 'Tool Name' 'Description' 20"
echo "  scripts/demo.sh 'Tool Name' https://github.com/..."
