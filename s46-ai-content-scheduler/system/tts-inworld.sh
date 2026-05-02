#!/bin/bash
# ============================================================
# tts-inworld.sh — Inworld TTS with emotion & personality
#
# Generates speech with emotional expression, supports multiple
# voices, personality presets, and multi-segment narration.
#
# Usage:
#   tts-inworld.sh "text to speak" [options]
#   tts-inworld.sh --file post.txt [options]
#   tts-inworld.sh --personality storyteller --emotion EXCITED [options]
#   tts-inworld.sh --podcast intro greeting conclusion
#
# Options:
#   --voice <id>         Voice ID (default: Timothy)
#   --emotion <tag>      Emotion tag (see below)
#   --personality <name> Load personality preset (system/voices/*.sh)
#   --output <file>      Output file (.mp3 or .wav)
#   --speed <0.5-2.0>    Speaking speed
#   --podcast            Generate multiple segments as podcast sections
#
# Emotion Tags: NEUTRAL, EXCITED, WARM, SERIOUS, SYMPATHETIC, ANGRY, SAD
# Other tags may be available — experiment!
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VOICES_DIR="$SCRIPT_DIR/voices"
TMPDIR="${TMPDIR:-$PROJECT_DIR/tmp}"
mkdir -p "$TMPDIR" "$VOICES_DIR"

API_KEY="${INWORLD_API_KEY:-}"
API_URL="https://api.inworld.ai/tts/v1/voice"

# ─── Defaults ───
VOICE="Timothy"
EMOTION="NEUTRAL"
MODEL="inworld-tts-1.5-max"
SPEED=1.0
OUTPUT=""

# ─── Help ───
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  sed -n '/^#=/,/^=#/p' "$0" | grep -v '^#=' | sed 's/^# \?//'
  exit 0
fi

# ─── Parse args ───
POSITIONAL=()
while [ $# -gt 0 ]; do
  case "$1" in
    --voice) VOICE="$2"; shift 2 ;;
    --emotion) EMOTION="$2"; shift 2 ;;
    --personality)
      PERSONALITY_FILE="$VOICES_DIR/$2.sh"
      if [ -f "$PERSONALITY_FILE" ]; then
        source "$PERSONALITY_FILE"
        echo "🎭 Loaded personality: $2 (voice=$VOICE, emotion=$EMOTION)"
      else
        echo "⚠️  Personality file not found: $PERSONALITY_FILE"
        echo "   Available: $(ls "$VOICES_DIR"/*.sh 2>/dev/null | xargs -n1 basename | sed 's/\.sh$//' | tr '\n' ' ')"
      fi
      shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --speed) SPEED="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    --file)
      TEXT=$(cat "$2" 2>/dev/null) || { echo "Error: cannot read $2"; exit 1; }
      shift 2
      ;;
    --podcast)
      PODCAST_MODE=true
      shift
      ;;
    *) POSITIONAL+=("$1"); shift ;;
  esac
done

# ─── Get text from positional args or stdin ───
if [ -z "${TEXT:-}" ]; then
  if [ ${#POSITIONAL[@]} -gt 0 ]; then
    TEXT="${POSITIONAL[*]}"
  elif [ ! -t 0 ]; then
    TEXT=$(cat)
  fi
fi

if [ -z "${TEXT:-}" ]; then
  echo "Error: no text provided. See --help"
  exit 1
fi

# ─── Generate single audio segment ───
generate_segment() {
  local segment_text="$1"
  local segment_output="$2"
  local segment_emotion="${3:-$EMOTION}"

  local payload=$(cat << PAYLOAD
{
  "modelId": "$MODEL",
  "text": $(echo "$segment_text" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))"),
  "voiceId": "$VOICE",
  "emotion": {"tag": "$segment_emotion"}
}
PAYLOAD
)

  local temp_file="$TMPDIR/inworld-raw-$$.json"
  curl -s -X POST "$API_URL" \
    -H "Authorization: Basic $API_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload" \
    -o "$temp_file" 2>/dev/null

  # Check for errors
  if grep -q '"errorType"' "$temp_file" 2>/dev/null; then
    local err=$(python3 -c "import json; d=json.load(open('$temp_file')); print(d.get('message','unknown error'))" 2>/dev/null)
    echo "❌ Inworld API error: $err" >&2
    rm -f "$temp_file"
    return 1
  fi

  # Decode base64 audio
  python3 -c "
import json, base64
data = json.load(open('$temp_file'))
audio = base64.b64decode(data['audioContent'])
with open('$segment_output', 'wb') as f:
    f.write(audio)
print(f'  Segment: ${segment_output} ({len(audio)} bytes)')
" 2>&1 || {
    echo "❌ Failed to decode audio response" >&2
    rm -f "$temp_file"
    return 1
  }

  rm -f "$temp_file"
  return 0
}

# ─── Podcast mode: multiple segments with intro/outro ───
if [ "${PODCAST_MODE:-}" = "true" ]; then
  echo "🎙️ Podcast mode: ${#POSITIONAL[@]} segments"
  SEGMENT_DIR="$TMPDIR/podcast-$$"
  mkdir -p "$SEGMENT_DIR"
  SEGMENT_FILES=()

  for i in "${!POSITIONAL[@]}"; do
    seg_text="${POSITIONAL[$i]}"
    seg_file="$SEGMENT_DIR/segment-$(printf '%02d' $i).mp3"
    # Cycle through emotions for variety
    case $((i % 5)) in
      0) seg_emotion="EXCITED" ;;
      1) seg_emotion="WARM" ;;
      2) seg_emotion="SERIOUS" ;;
      3) seg_emotion="NEUTRAL" ;;
      4) seg_emotion="SYMPATHETIC" ;;
    esac
    echo "  [$(($i+1))/${#POSITIONAL[@]}] emotion=$seg_emotion"
    generate_segment "$seg_text" "$seg_file" "$seg_emotion" || {
      echo "  ⚠️ Segment $i failed"
      continue
    }
    SEGMENT_FILES+=("$seg_file")
  done

  if [ ${#SEGMENT_FILES[@]} -eq 0 ]; then
    echo "❌ No segments generated"
    exit 1
  fi

  # Combine segments
  if [ ${#SEGMENT_FILES[@]} -eq 1 ]; then
    FINAL="${OUTPUT:-$TMPDIR/podcast.mp3}"
    cp "${SEGMENT_FILES[0]}" "$FINAL"
  else
    FINAL="${OUTPUT:-$TMPDIR/podcast.mp3}"
    local concat_file="$TMPDIR/concat-$$.txt"
    for f in "${SEGMENT_FILES[@]}"; do
      echo "file '$(realpath "$f")'" >> "$concat_file"
    done
    ffmpeg -y -f concat -safe 0 -i "$concat_file" -c copy "$FINAL" 2>/dev/null
    rm -f "$concat_file"
  fi

  echo "✅ Podcast saved to: $FINAL"
  ls -lh "$FINAL"
  # Cleanup segments
  rm -rf "$SEGMENT_DIR"
  exit 0
fi

# ─── Single segment mode ───
# Split long text into chunks if needed
if [ ${#TEXT} -gt 1800 ]; then
  echo "📝 Text is long (${#TEXT} chars), splitting into chunks..."
  chunk_dir="$TMPDIR/tts-chunks-$$"
  mkdir -p "$chunk_dir"
  
  python3 << PYEOF
import sys, os
text = """$TEXT"""
max_chunk = 1800
chunks = []
current = ''
for sentence in text.replace('.', '.|').replace('?', '?|').replace('!', '!|').split('|'):
    if len(current) + len(sentence) < max_chunk:
        current += sentence
    else:
        if current:
            chunks.append(current.strip())
        current = sentence
if current:
    chunks.append(current.strip())
for i, chunk in enumerate(chunks):
    with open('$chunk_dir/chunk-{}.txt'.format(i), 'w') as f:
        f.write(chunk)
print(len(chunks))
PYEOF

  chunk_count=$(cat "$chunk_dir/chunk-*.txt" 2>/dev/null | wc -l || echo 0)
  # Get actual chunk count from file listing
  chunk_count=$(ls "$chunk_dir"/chunk-*.txt 2>/dev/null | wc -l)
  echo "  ${chunk_count} chunks to generate"
  COMBINED_FILES=()
  
  for chunk_file in "$chunk_dir"/chunk-*.txt; do
    [ -f "$chunk_file" ] || continue
    chunk_idx=$(basename "$chunk_file" .txt | sed 's/chunk-//')
    chunk_text=$(cat "$chunk_file")
    chunk_out="$chunk_dir/out-${chunk_idx}.mp3"
    # Vary emotion across chunks
    emotions=("EXCITED" "WARM" "SERIOUS" "NEUTRAL" "SYMPATHETIC")
    eidx=$((10#${chunk_idx} % 5))
    echo "  Chunk $((chunk_idx + 1))/${chunk_count} [${emotions[$eidx]}]"
    generate_segment "$chunk_text" "$chunk_out" "${emotions[$eidx]}" || {
      echo "  ⚠️ Chunk $chunk_idx failed"
      continue
    }
    COMBINED_FILES+=("$chunk_out")
  done

  if [ ${#COMBINED_FILES[@]} -eq 0 ]; then
    echo "❌ No chunks generated"
    rm -rf "$chunk_dir"
    exit 1
  fi

  # Combine chunks
  FINAL_OUTPUT="${OUTPUT:-$TMPDIR/combined.mp3}"
  concat_list="$TMPDIR/concat-list-$$.txt"
  for f in "${COMBINED_FILES[@]}"; do
    echo "file '$(realpath "$f")'" >> "$concat_list"
  done
  ffmpeg -y -f concat -safe 0 -i "$concat_list" -c copy "$FINAL_OUTPUT" 2>/dev/null
  rm -f "$concat_list"

  echo "✅ Audio saved to: $FINAL_OUTPUT"
  ls -lh "$FINAL_OUTPUT"
  rm -rf "$chunk_dir"
else
  # Short text, single segment
  FINAL_OUTPUT="${OUTPUT:-$TMPDIR/tts-output.mp3}"
  echo "🎤 Generating: emotion=$EMOTION, voice=$VOICE"
  generate_segment "$TEXT" "$FINAL_OUTPUT" "$EMOTION" || exit 1
  echo "✅ Audio saved to: $FINAL_OUTPUT"
  ls -lh "$FINAL_OUTPUT"
fi
