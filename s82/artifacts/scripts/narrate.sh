#!/usr/bin/env bash
# narrate.sh — Agrega narración TTS a un video
# Uso: ./narrate.sh <video.mp4> <texto> [output.mp4]
set -e

VIDEO="$1"
TEXT="$2"
OUTPUT="${3:-${VIDEO%.*}-narrated.mp4}"
TMP_AUDIO="/tmp/narration-$(date +%s).mp3"

if [ -z "$VIDEO" ] || [ -z "$TEXT" ]; then
  echo "Uso: ./narrate.sh <video.mp4> <texto> [output.mp4]"
  exit 1
fi

echo "=== Narración TTS ==="
echo "Video: $VIDEO"
echo "Texto: ${TEXT:0:60}..."

edge-tts --voice es-MX-DaliaNeural --text "$TEXT" --write-media "$TMP_AUDIO"
echo "Audio generado: $(ffprobe "$TMP_AUDIO" 2>&1 | grep -oP 'Duration: \S+')"

ffmpeg -i "$VIDEO" -i "$TMP_AUDIO" -c:v copy -c:a aac -map 0:v -map 1:a -shortest -y "$OUTPUT" 2>&1 | tail -2

rm -f "$TMP_AUDIO"
echo "Done: $(ls -lh "$OUTPUT" | awk '{print $5, $NF}')"
