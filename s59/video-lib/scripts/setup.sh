#!/bin/bash
# scripts/setup.sh - Install all dependencies for video production
# Usage: ./scripts/setup.sh [--check-only|--install]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$(dirname "$SCRIPT_DIR")"
MODE="${1:-check}"

check_cmd() { command -v "$1" &>/dev/null; }
ok()   { echo "  [✓] $1"; }
fail() { echo "  [✗] $1"; }

case "$MODE" in
    check|--check-only)
        echo "=== Dependency Check ==="
        echo ""
        echo "Core tools:"
        check_cmd ffmpeg     && ok "ffmpeg"     || fail "ffmpeg (sudo apt install ffmpeg)"
        check_cmd ffprobe    && ok "ffprobe"    || fail "ffprobe (comes with ffmpeg)"
        check_cmd curl       && ok "curl"       || fail "curl (sudo apt install curl)"
        check_cmd jq         && ok "jq"         || fail "jq (sudo apt install jq)"
        echo ""
        echo "TTS engines (at least one):"
        check_cmd espeak     && ok "espeak"     || fail "espeak (sudo apt install espeak)"
        check_cmd gtts-cli   && ok "gtts-cli"   || fail "gtts-cli (pip install gTTS)"
        echo ""
        echo "Screen recording:"
        check_cmd xdg-open   && ok "X server"   || fail "X server (for x11grab)"
        echo ""
        echo "Optional:"
        check_cmd gh         && ok "gh (GitHub CLI)" || fail "gh (optional, for fetching tool info)"
        echo ""
        echo "Environment:"
        [ -n "${DEEPSEEK_API_KEY:-}" ] && ok "DEEPSEEK_API_KEY set" || fail "DEEPSEEK_API_KEY not set (export DEEPSEEK_API_KEY='sk-...')"
        echo ""
        echo "Assets:"
        for dir in sfx vfx transitions broll; do
            count=$(find "$LIB_DIR/assets/$dir" -type f 2>/dev/null | wc -l)
            echo "  assets/$dir/: $count files"
        done
        ;;

    install|--install)
        echo "=== Installing Dependencies ==="
        sudo apt-get update -qq
        sudo apt-get install -y -qq ffmpeg espeak jq curl 2>/dev/null
        pip install gTTS --quiet 2>/dev/null || true
        echo "Done. Run 'setup.sh --check' to verify."
        ;;
esac
