#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIDS_DIR="$PROJECT_DIR/.pids"
LOGS_DIR="$PROJECT_DIR/.logs"
TIMELINE="$PROJECT_DIR/.timeline"
mkdir -p "$PIDS_DIR" "$LOGS_DIR"

> "$TIMELINE"

log() {
    local agent="$1" status="$2" msg="$3"
    echo "$(date +%s%N | cut -c1-13)|$(date +%H:%M:%S)|${agent}|${status}|${msg}" >> "$TIMELINE"
}

declare -A AGENTS=(
    # Scripts
    [script-es]="script-es|Escribe un guion en español para un video de 60 segundos sobre cómo 5 agentes de IA construyen una app juntos. Estilo TikTok: hook fuerte, cortes rápidos, lenguaje casual. Incluye indicaciones de zoom y efectos."
    [script-en]="script-en|Write a 60-second English script for a TikTok video about how 5 AI agents built an app together. TikTok style: strong hook, fast cuts, casual language. Include zoom and effect cues."
    
    # Audio
    [audio-es]="audio-es|Genera audio TTS en español usando tts-speak. Lee el guion de script-es/guion.txt con voz am_michael, velocidad 1.1. Divide en clips de 5-10 segundos."
    [audio-en]="audio-en|Generate TTS audio in English using tts-speak. Read script-en/script.txt with voice am_michael, speed 1.1. Split into 5-10 second clips."
    
    # Video styles
    [style-fireship]="style-fireship|Create a Fireship-style video script: ultra fast paced, code-heavy, minimal talking head, text overlays with key points, 100 seconds format, dry humor."
    [style-networkchuck]="style-networkchuck|Create a NetworkChuck-style script: energetic, green screen energy, memes references, 'YOU need to learn this' energy, beginner friendly."
    [style-tiktok]="style-tiktok|Create a TikTok vertical video edit script using ffmpeg. Include: zoom effects, text overlays, sound effect timings, fast cuts every 2-3 seconds, hook in first 2 seconds."
    
    # Production
    [sfx]="sfx|Download or create sound effects for the video: whoosh, ding, pop, transition sounds. Use ffmpeg to generate synthetic sounds or describe where to source them."
    [composer]="composer|Create the final ffmpeg command to compose: screen recording + TTS audio + sound effects + text overlays + zoom effects into a 9:16 vertical video."
)

start_agents() {
    echo "🎬 Lanzando agentes de video..."
    
    for name in "${!AGENTS[@]}"; do
        IFS='|' read -r subdir task <<< "${AGENTS[$name]}"
        local work_dir="$PROJECT_DIR/$subdir"
        local pid_file="$PIDS_DIR/${name}.pid"
        
        mkdir -p "$work_dir"
        
        if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            continue
        fi
        
        log "$name" "START" "Iniciado"
        
        (
            cd "$work_dir"
            log "$name" "WORKING" "Generando..."
            pi -p "$task" --no-session 2>&1 | tee "$LOGS_DIR/${name}.log"
            log "$name" "DONE" "Completado ✓"
            rm -f "$pid_file"
        ) &
        
        echo $! > "$pid_file"
        echo "  🎙️ $name → $subdir/"
    done
    
    echo ""
    echo "📊 Monitorear: cat .timeline"
}

stop_all() {
    echo "🛑 Deteniendo..."
    for pid_file in "$PIDS_DIR"/*.pid; do
        [[ -f "$pid_file" ]] || continue
        kill "$(cat "$pid_file")" 2>/dev/null || true
        rm -f "$pid_file"
    done
}

status() {
    echo "📊 Estado:"
    for name in script-es script-en audio-es audio-en style-fireship style-networkchuck style-tiktok sfx composer; do
        local pid_file="$PIDS_DIR/${name}.pid"
        if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            echo "  🟢 $name"
        elif grep -q "${name}|DONE" "$TIMELINE" 2>/dev/null; then
            echo "  ✅ $name"
        else
            echo "  ⚪ $name"
        fi
    done
}

case "${1:-}" in
    start)  start_agents ;;
    stop)   stop_all ;;
    status) status ;;
    *)      echo "Uso: $0 {start|stop|status}" ;;
esac
