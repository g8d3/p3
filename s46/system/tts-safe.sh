#!/bin/bash
# tts-safe.sh — TTS wrapper that handles JSON special characters
# Usage: tts-safe.sh <text> [--voice <v>] [--output <file>]
# Reads text from argument or stdin, safely passes to TTS API

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
export TMPDIR="$PROJECT_DIR/tmp"

# Get text (first arg or stdin)
if [ $# -ge 1 ] && [ "$1" != "--voice" ] && [ "$1" != "--output" ]; then
  TEXT="$1"
  shift
elif [ ! -t 0 ]; then
  TEXT=$(cat)
else
  echo "Error: no text provided"
  exit 1
fi

# Parse remaining args
VOICE="af_heart"
OUTPUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --voice) VOICE="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# Use Python for safe JSON escaping
python3 << PYEOF
import json, sys, subprocess, os

text = """$TEXT"""
voice = "$VOICE"
output = "$OUTPUT"

payload = {
    "text": text,
    "voice": voice,
    "speed": 1.0
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
