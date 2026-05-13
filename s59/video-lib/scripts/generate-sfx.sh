#!/bin/bash
# scripts/generate-sfx.sh - Generate sound effects programmatically
# Uses ffmpeg to create essential SFX from scratch
# Usage: ./scripts/generate-sfx.sh
# Generates: click, whoosh, ding, swoosh, pop, success, error, type
set -euo pipefail

SFX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/assets/sfx"
mkdir -p "$SFX_DIR"

gen() {
    local name="$1"
    local output="$SFX_DIR/${name}.wav"
    [ -f "$output" ] && echo "  EXISTS: $name" && return
    echo "  GEN:   $name"
    case "$name" in
        click)   ffmpeg -y -f lavfi -i "aevalsrc=exprs=sin(1000*2*PI*t):d=0.05" -ac 1 -ar 44100 "$output" 2>/dev/null ;;
        pop)     ffmpeg -y -f lavfi -i "aevalsrc=exprs=sin(800*2*PI*t)*exp(-t*30):d=0.15" -ac 1 -ar 44100 "$output" 2>/dev/null ;;
        whoosh)  ffmpeg -y -f lavfi -i "anoisesrc=d=0.5:c=pink:a=0.5" -af "afftfilt=real='hypot(re,im)*sin(2*PI*t*2000)':imag='hypot(re,im)*cos(2*PI*t*2000)'" -ac 1 -ar 44100 "$output" 2>/dev/null ;;
        ding)    ffmpeg -y -f lavfi -i "aevalsrc=exprs=sin(1800*2*PI*t)*exp(-t*8)+sin(1200*2*PI*t)*exp(-t*8):d=0.5" -ac 1 -ar 44100 "$output" 2>/dev/null ;;
        success) ffmpeg -y -f lavfi -i "aevalsrc=exprs=sin(523*2*PI*t)*exp(-t*4)+sin(659*2*PI*t)*exp(-t*4)+sin(784*2*PI*t)*exp(-t*4):d=0.8" -ac 1 -ar 44100 "$output" 2>/dev/null ;;
        error)   ffmpeg -y -f lavfi -i "aevalsrc=exprs=sin(150*2*PI*t)*exp(-t*3)+sin(120*2*PI*t)*exp(-t*3):d=0.6" -ac 1 -ar 44100 "$output" 2>/dev/null ;;
        type)    ffmpeg -y -f lavfi -i "anoisesrc=d=0.03:c=brown:a=0.3" -ac 1 -ar 44100 "$output" 2>/dev/null; for i in $(seq 1 5); do cat "$output" >> "${output%.*}_tmp.wav" 2>/dev/null || true; done; mv -f "${output%.*}_tmp.wav" "$output" 2>/dev/null || true ;;
        swoosh)  ffmpeg -y -f lavfi -i "aevalsrc=exprs=sin(200*2*PI*t*(1+t*2))*exp(-t*5):d=0.4" -ac 1 -ar 44100 "$output" 2>/dev/null ;;
    esac
}

echo "=== Generating Sound Effects ==="
for sfx in click pop whoosh ding success error type swoosh; do
    gen "$sfx"
done
echo ""
echo "Generated $(ls -1 "$SFX_DIR"/*.wav 2>/dev/null | wc -l) SFX files"
ls -lh "$SFX_DIR"
