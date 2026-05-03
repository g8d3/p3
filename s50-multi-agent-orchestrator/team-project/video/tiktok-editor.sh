#!/usr/bin/env bash
set -euo pipefail

# Editor de video estilo TikTok con ffmpeg
# Uso: ./tiktok-editor.sh <screen-recording> <audio-dir> <output>

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

SCREEN="${1:-$PROJECT_DIR/recordings/screen.mp4}"
AUDIO_DIR="${2:-$PROJECT_DIR/audio-es}"
OUTPUT="${3:-$PROJECT_DIR/output/tiktok-final.mp4}"

mkdir -p "$(dirname "$OUTPUT")"

echo "🎬 Componiendo video estilo TikTok..."
echo "   Screen: $SCREEN"
echo "   Audio: $AUDIO_DIR"
echo "   Output: $OUTPUT"

# Verificar que existe el screen recording
if [[ ! -f "$SCREEN" ]]; then
    echo "❌ No se encontró: $SCREEN"
    echo "   Primero graba la pantalla: ./record-screen.sh start"
    exit 1
fi

# Obtener duración del screen recording
DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$SCREEN" | cut -d. -f1)
echo "   Duración: ${DURATION}s"

# Crear video vertical 9:16 con efectos TikTok
# 1. Recortar a formato vertical (centro de la pantalla)
# 2. Agregar zoom dinámico
# 3. Agregar textos
# 4. Mezclar audio

# Paso 1: Recortar a 9:16 (centro)
ffmpeg -y \
    -i "$SCREEN" \
    -vf "crop=ih*9/16:ih:iw/2-ih*9/32:0,scale=1080:1920" \
    -c:v libx264 -preset fast -crf 23 \
    /tmp/tiktok-crop.mp4

echo "✓ Crop a 9:16"

# Paso 2: Agregar efecto de zoom dinámico (cada 5 segundos)
# Usar zoompan para crear zoom in/out
ffmpeg -y \
    -i /tmp/tiktok-crop.mp4 \
    -vf "zoompan=z='min(zoom+0.001,1.5)':d=125:s=1080x1920:fps=15" \
    -c:v libx264 -preset fast -crf 23 \
    /tmp/tiktok-zoom.mp4

echo "✓ Zoom dinámico"

# Paso 3: Agregar textos overlay (puntos clave)
ffmpeg -y \
    -i /tmp/tiktok-zoom.mp4 \
    -vf "drawtext=text='5 AGENTES':fontsize=72:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h/4:enable='between(t,2,5)',\
drawtext=text='CONSTRUYENDO JUNTOS':fontsize=60:fontcolor=#00ff88:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h/3:enable='between(t,5,8)',\
drawtext=text='EN TIEMPO REAL':fontsize=48:fontcolor=#ff9800:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h*2/3:enable='between(t,10,13)'" \
    -c:v libx264 -preset fast -crf 23 \
    /tmp/tiktok-text.mp4

echo "✓ Textos overlay"

# Paso 4: Generar efectos de sonido sintéticos
# Whoosh
ffmpeg -y -f lavfi -i "sine=frequency=1000:duration=0.3" -af "afade=t=in:d=0,afade=t=out:d=0.3" /tmp/whoosh.mp3 2>/dev/null

# Ding
ffmpeg -y -f lavfi -i "sine=frequency=2000:duration=0.2" -af "afade=t=out:d=0.2" /tmp/ding.mp3 2>/dev/null

echo "✓ Efectos de sonido"

# Paso 5: Componer audio final
# Si hay TTS, mezclarlo. Si no, solo efectos
if ls "$AUDIO_DIR"/*.mp3 2>/dev/null | head -1 > /dev/null; then
    echo "   Mezclando TTS audio..."
    # Concatenar clips de TTS
    ls "$AUDIO_DIR"/*.mp3 | sort | while read f; do echo "file '$f'"; done > /tmp/tts-list.txt
    ffmpeg -y -f concat -safe 0 -i /tmp/tts-list.txt -c copy /tmp/tts-full.mp3
    
    # Mezclar TTS + efectos
    ffmpeg -y \
        -i /tmp/tiktok-text.mp4 \
        -i /tmp/tts-full.mp3 \
        -i /tmp/whoosh.mp3 \
        -i /tmp/ding.mp3 \
        -filter_complex "[1:a]volume=1.0[tts];[2:a]adelay=2000|2000,volume=0.3[whoosh];[3:a]adelay=5000|5000,volume=0.3[ding];[tts][whoosh][ding]amix=inputs=3:duration=first[aout]" \
        -map 0:v -map "[aout]" \
        -c:v copy -c:a aac -b:a 128k \
        "$OUTPUT"
else
    echo "   Solo efectos de sonido..."
    ffmpeg -y \
        -i /tmp/tiktok-text.mp4 \
        -i /tmp/whoosh.mp3 \
        -i /tmp/ding.mp3 \
        -filter_complex "[1:a]adelay=2000|2000,volume=0.3[whoosh];[2:a]adelay=5000|5000,volume=0.3[ding];[whoosh][ding]amix=inputs=2:duration=first[aout]" \
        -map 0:v -map "[aout]" \
        -c:v copy -c:a aac -b:a 128k \
        "$OUTPUT"
fi

echo ""
echo "✅ Video TikTok creado: $OUTPUT"
echo "   Formato: 1080x1920 (9:16)"
echo "   Duración: ~${DURATION}s"

# Limpiar temporales
rm -f /tmp/tiktok-*.mp4 /tmp/whoosh.mp3 /tmp/ding.mp3 /tmp/tts-*.mp3 /tmp/tts-list.txt
