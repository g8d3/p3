#!/bin/bash
# ==============================================================================
# lib/ffmpeg.sh — Funciones ffmpeg PRE-TESTADAS para producción de video
# Cada función aquí fue verificada individualmente antes de incluirse.
# ==============================================================================

# --- Constantes ---
FONT_BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_MONO="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
W=1920
H=1080
FPS=30
CRF=18
SFX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../assets/sfx" && pwd)"

# --- BACKGROUND: Fondo con color y animación sutil ---
# TESTED: v5.1
# modes: dark, blue, tech, warm
video_bg() {
    local duration="${1:-5}"
    local mode="${2:-dark}"
    local output="${3:-build/bg.mp4}"
    mkdir -p "$(dirname "$output")"

    local c1 c2
    case "$mode" in
        dark)   c1="#0a0a0f"; c2="#16213e" ;;
        blue)   c1="#0a1628"; c2="#1a3a5c" ;;
        tech)   c1="#0f0f1a"; c2="#2a1a3a" ;;
        warm)   c1="#1a0f0a"; c2="#3a2a1a" ;;
        *)      c1="#0a0a0f"; c2="#16213e" ;;
    esac

    # Simple: color background + fade. No zoompan (causa problemas en filtros complejos)
    ffmpeg -y \
        -f lavfi -i "color=c=${c1}:s=${W}x${H}:r=${FPS}:d=${duration}" \
        -f lavfi -i "color=c=${c2}:s=${W}x${H}:r=${FPS}:d=${duration}" \
        -filter_complex "[0:v][1:v]blend=all_mode=addition:all_opacity=0.2,format=yuv420p,
            fade=t=in:st=0:d=0.5,fade=t=out:st=$((duration-2)):d=1" \
        -c:v libx264 -preset ultrafast -crf 23 "$output" 2>/dev/null
    echo "$output"
}

# --- TRANSITION: xfade entre dos clips ---
# TESTED: nuevo
video_transition() {
    local clip1="$1"
    local clip2="$2"
    local transition="${3:-fade}"
    local duration="${4:-0.5}"
    local output="${5:-build/transitioned.mp4}"

    local d1=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$clip1" 2>/dev/null || echo 3)
    local offset=$(echo "$d1 - $duration" | bc)

    ffmpeg -y -i "$clip1" -i "$clip2" \
        -filter_complex "xfade=transition=${transition}:duration=${duration}:offset=${offset}" \
        -c:v libx264 -preset medium -crf $CRF \
        -c:a aac -b:a 192k \
        "$output" 2>/dev/null
    echo "$output"
}

# --- CONCAT: Unir múltiples clips ---
# TESTED: nuevo
video_concat() {
    local output="${1:-build/concat.mp4}"
    shift
    local clips=("$@")

    local list_file="build/concat_list.txt"
    rm -f "$list_file"
    for clip in "${clips[@]}"; do
        echo "file '$clip'" >> "$list_file"
    done

    ffmpeg -y -f concat -safe 0 -i "$list_file" \
        -c:v libx264 -preset medium -crf $CRF \
        -c:a aac -b:a 192k \
        "$output" 2>/dev/null
    echo "$output"
}

# --- SCENE TITLE: MAGIC / CONTEXT split con sombra ---
# TESTED: v5.1, build/video-v2.mp4 (paso 2)
video_title() {
    local input="$1"
    local title1="${2:-MAGIC}"
    local title2="${3:-CONTEXT}"
    local accent="${4:-#e94560}"
    local start="${5:-1.2}"
    local duration="${6:-5}"
    local end=$(echo "$start + $duration" | bc)
    local output="${7:-build/titled.mp4}"

    ffmpeg -y -i "$input" \
        -vf "
            drawtext=text='$title1':fontcolor=white:fontsize=120:fontfile=$FONT_BOLD:x=w/2-text_w-10:y=(h-text_h)/2-60:enable='between(t,$start,$end)':shadowcolor=$accent@0.5:shadowx=6:shadowy=6,
            drawtext=text='$title2':fontcolor=$accent:fontsize=120:fontfile=$FONT_BOLD:x=w/2+10:y=(h-text_h)/2-60:enable='between(t,$start,$end)':shadowcolor=$accent@0.5:shadowx=6:shadowy=6
        " \
        -c:v libx264 -preset medium -crf $CRF "$output" 2>/dev/null
    echo "$output"
}

# --- SCENE SUBTITLE: Texto secundario centrado ---
# TESTED: v5.1
video_subtitle() {
    local input="$1"
    local text="$2"
    local start="${3:-1.8}"
    local duration="${4:-5}"
    local end=$(echo "$start + $duration" | bc)
    local output="${5:-build/subtitled.mp4}"

    ffmpeg -y -i "$input" \
        -vf "drawtext=text='$text':fontcolor=#aaaaaa:fontsize=22:fontfile=$FONT_BOLD:x=(w-text_w)/2:y=(h-text_h)/2+30:enable='between(t,$start,$end)'" \
        -c:v libx264 -preset medium -crf $CRF "$output" 2>/dev/null
    echo "$output"
}

# --- SCENE FOOTER: Texto en esquina inferior ---
# TESTED: v5.1
video_footer() {
    local input="$1"
    local text="$2"
    local color="${3:-#888888}"
    local start="${4:-2.5}"
    local duration="${5:-5}"
    local end=$(echo "$start + $duration" | bc)
    local x="${6:-80}"
    local y="${7:-720}"

    local output="build/footer_$$.mp4"
    ffmpeg -y -i "$input" \
        -vf "drawtext=text='$text':fontcolor=$color:fontsize=18:fontfile=$FONT_MONO:x=$x:y=$y:enable='between(t,$start,$end)'" \
        -c:v libx264 -preset medium -crf $CRF "$output" 2>/dev/null
    echo "$output"
}

# --- CODE OVERLAY: Líneas de código tenues al fondo ---
# TESTED: v5.1
video_code_bg() {
    local input="$1"
    local duration="${2:-5}"
    shift 2
    local lines=("$@")
    local output="build/codebg_$$.mp4"

    local filter=""
    local i=0
    local y=120
    local start=0.5
    for line in "${lines[@]}"; do
        if [ -n "$filter" ]; then filter+=","; fi
        filter+="drawtext=text='$line':fontcolor=#00ff41@0.25:fontsize=14:fontfile=$FONT_MONO:x=80:y=$y:enable='between(t,${start},${duration}')"
        y=$((y+25))
        start=$(echo "$start + 0.2" | bc 2>/dev/null || echo "$start")
    done

    if [ -n "$filter" ]; then
        ffmpeg -y -i "$input" -vf "$filter" -c:v libx264 -preset ultrafast -crf 23 "$output" 2>/dev/null
        echo "$output"
    else
        echo "$input"
    fi
}

# --- MIX AUDIO: TTS + música + SFX sincronizados ---
# TESTED: v5, v5.1
video_mix_audio() {
    local tts_file="${1:?TTS file required}"
    local music_file="${2:?Music file required}"
    local output="${3:-build/audio-mixed.wav}"
    local duration="${4:-5}"
    shift 4

    local fade_out_start=$(echo "$duration - 0.5" | bc)

    mkdir -p "$(dirname "$output")"

    # Construir filtro de mezcla dinámicamente con los SFX adicionales
    local filter="[0:a]adelay=0|0,volume=2.0[tts];[1:a]adelay=0|0,volume=0.3[music];"
    local mix_inputs="[tts][music]"
    local weights="1.0 0.3"
    local input_count=2

    # Procesar SFX adicionales como pares: archivo,delay,volumen
    local idx=2
    while [ $# -ge 3 ]; do
        local sfx_file="$1"
        local sfx_delay="$2"
        local sfx_vol="$3"
        filter+="[${idx}:a]adelay=${sfx_delay}|${sfx_delay},volume=${sfx_vol}[sfx${idx}];"
        mix_inputs+="[sfx${idx}]"
        weights+=" 0.4"
        input_count=$((input_count + 1))
        idx=$((idx + 1))
        shift 3
    done

    filter+="${mix_inputs}amix=inputs=${input_count}:duration=longest:weights=${weights},"
    filter+="volume=1.8,afade=t=in:st=0:d=0.4,afade=t=out:st=${fade_out_start}:d=0.5,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"

    ffmpeg -y \
        -i "$tts_file" \
        -i "$music_file" \
        "$@" \
        -filter_complex "$filter" \
        -t "$duration" -c:a pcm_s16le "$output" 2>/dev/null
    echo "$output"
}

# --- TTS GENERATION (Inworld AI - Rafael español) ---
# TESTED: v5.1 (funciona con español)
# Depends on: node tts-inworld.js in the bin directory
video_tts() {
    local text="${1:?Text required}"
    local output="${2:-build/tts.mp3}"
    local speed="${3:-1.0}"
    local temp="${4:-1.5}"

    mkdir -p "$(dirname "$output")"
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../bin" && pwd)"
    node "$script_dir/tts-inworld.js" "$text" "$output" \
        --voice Rafael --speed "$speed" --temp "$temp" --mode EXPRESSIVE 2>/dev/null
    echo "$output"
}

# --- RENDER FINAL: Combinar video + audio ---
# TESTED: v5, v5.1
video_render() {
    local video="${1:?Video file required}"
    local audio="${2:-build/audio-mixed.wav}"
    local output="${3:-output/final.mp4}"

    mkdir -p "$(dirname "$output")"
    ffmpeg -y \
        -i "$video" -i "$audio" \
        -c:v libx264 -preset medium -crf $CRF \
        -c:a aac -b:a 192k -ar 48000 -ac 2 \
        -movflags +faststart -pix_fmt yuv420p -shortest \
        "$output" 2>/dev/null
    echo "$output"
}
