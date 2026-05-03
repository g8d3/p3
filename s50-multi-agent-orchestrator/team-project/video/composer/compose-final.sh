#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# compose-final.sh — Final FFmpeg composition command
#
# Composes screen recording + TTS + SFX + text overlays + zoom → 9:16 vertical
#
# This is a single-call ffmpeg command. No dependencies beyond ffmpeg/ffprobe.
#
# Usage:
#   ./compose-final.sh                    # compose with defaults
#   ./compose-final.sh --dry-run          # print command without executing
#   ./compose-final.sh --help             # show this help
###############################################################################

# ─── Paths ──────────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

SCREEN="$PROJECT_DIR/recordings/screen.mp4"
TTS_DIR="$PROJECT_DIR/audio-en-new"
SFX_DIR="$PROJECT_DIR/sfx"
OUTPUT="$PROJECT_DIR/output/final-vertical.mp4"

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true
[[ "${1:-}" == "--help" || "${1:-}" == "-h" ]] && sed -n '2,/^###/{ /^###/d; s/^# \?//; p }' "$0" && exit 0

# ─── Validate inputs ───────────────────────────────────────────────────────
for f in "$SCREEN"; do
    [[ -f "$f" ]] || { echo "ERROR: Missing $f"; exit 1; }
done

# ─── Prepare TTS (concatenate clips into single file) ──────────────────────
TTS_CONCAT=$(mktemp /tmp/compose-tts-XXXXXX.txt)
TTS_FULL=$(mktemp /tmp/compose-tts-full-XXXXXX.mp3)
trap 'rm -f "$TTS_CONCAT" "$TTS_FULL"' EXIT

for clip in "$TTS_DIR"/clip-*.mp3; do
    echo "file '$(realpath "$clip")'" >> "$TTS_CONCAT"
done

ffmpeg -y -f concat -safe 0 -i "$TTS_CONCAT" \
    -af "apad=pad_dur=0.5" \
    -c:a libmp3lame -q:a 2 "$TTS_FULL" 2>/dev/null

TTS_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$TTS_FULL")
DURATION=$(echo "$TTS_DUR + 3" | bc | cut -d. -f1)   # +3s outro buffer
echo "TTS: ${TTS_DUR}s → output: ${DURATION}s"

# ─── Font ───────────────────────────────────────────────────────────────────
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
[[ -f "$FONT" ]] || FONT=$(find /usr/share/fonts -name "*Bold*.ttf" 2>/dev/null | head -1)

# ─── FFmpeg command ────────────────────────────────────────────────────────
#
# Input mapping:
#   [0] screen recording   (looped if shorter than output)
#   [1] TTS narration      (concatenated clips)
#   [2] sfx/whoosh.mp3
#   [3] sfx/ding.mp3
#   [4] sfx/pop.mp3
#   [5] sfx/success.mp3
#   [6] sfx/click.wav
#
# Filter complex:
#
# VIDEO CHAIN:
#   crop  → center-crop source to 9:16 aspect
#   scale → upscale 15% for Ken Burns zoom headroom (1242×2208)
#   crop  → crop back to 1080×1920 with oscillating pan offset
#   fps   → 30fps
#   fmt   → yuv420p
#   text  → 6 timed drawtext overlays (hook, agents, tech, CTA, URL)
#
# AUDIO CHAIN:
#   TTS at full volume, padded to duration
#   8 SFX events with adelay at precise timestamps
#   amix → merge all 9 streams (1 TTS + 8 SFX)
#

CMD=(
ffmpeg -y

# ── Input 0: Screen recording (loop to fill duration) ──
-stream_loop -1
-i "$SCREEN"

# ── Input 1: TTS narration ──
-i "$TTS_FULL"

# ── Inputs 2-6: Sound effects ──
-i "$SFX_DIR/whoosh.mp3"
-i "$SFX_DIR/ding.mp3"
-i "$SFX_DIR/pop.mp3"
-i "$SFX_DIR/success.mp3"
-i "$SFX_DIR/click.wav"

# ── Filter complex ──
-filter_complex "
  [0:v]
    crop=ih*9/16:ih:iw/2-iw*9/32:0,
    scale=1242:2208,
    crop=1080:1920:(1242-1080)/2+sin(t*0.5)*30:(2208-1920)/2+cos(t*0.3)*20,
    fps=30,
    format=yuv420p,
    drawtext=fontfile=${FONT}:text='5 AI AGENTS':fontsize=80:fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h/5:enable='between(t,1.5,5)',
    drawtext=fontfile=${FONT}:text='BUILDING\nTOGETHER':fontsize=68:fontcolor=#00ff88:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h/3:enable='between(t,7,11)',
    drawtext=fontfile=${FONT}:text='IN REAL TIME':fontsize=56:fontcolor=#ff9800:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h/2:enable='between(t,15,19)',
    drawtext=fontfile=${FONT}:text='HTML  CSS  JS\nTESTS  DOCS':fontsize=48:fontcolor=#00bfff:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h*0.55:enable='between(t,23,28)',
    drawtext=fontfile=${FONT}:text='READY TO\nTRY IT?':fontsize=72:fontcolor=yellow:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h/3:enable='between(t,34,39)',
    drawtext=fontfile=${FONT}:text='github.com/your-project':fontsize=36:fontcolor=white:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h*0.85:enable='between(t,40,45)'
  [vout];

  [1:a]volume=1.0,apad=pad_dur=${DURATION}[tts];
  [2:a]adelay=0|0,volume=0.35[sfx0];
  [3:a]adelay=5000|5000,volume=0.35[sfx1];
  [3:a]adelay=11000|11000,volume=0.35[sfx2];
  [4:a]adelay=18000|18000,volume=0.35[sfx3];
  [5:a]adelay=24000|24000,volume=0.35[sfx4];
  [4:a]adelay=31000|31000,volume=0.35[sfx5];
  [6:a]adelay=34000|34000,volume=0.35[sfx6];
  [2:a]adelay=37000|37000,volume=0.35[sfx7];

  [tts][sfx0][sfx1][sfx2][sfx3][sfx4][sfx5][sfx6][sfx7]
    amix=inputs=9:duration=longest:dropout_transition=2
  [aout]
"

# ── Map outputs ──
-map "[vout]"
-map "[aout]"

# ── Encoding ──
-c:v libx264 -preset medium -crf 20
-c:a aac -b:a 192k -ar 48000
-movflags +faststart -pix_fmt yuv420p
-t "$DURATION"

# ── Metadata ──
-metadata "title=5 AI Agents Build an App"
-metadata "comment=Generated by multi-agent video composer"

# ── Output ──
"$OUTPUT"
)

# ─── Execute or print ──────────────────────────────────────────────────────
if [[ "$DRY_RUN" == "true" ]]; then
    echo "═══ DRY RUN — Final FFmpeg Command ═══"
    echo ""
    printf '%q ' "${CMD[@]}" | fold -s -w 100 | sed 's/^/  /'
    echo ""
    echo ""
    echo "═══ Pipeline Summary ═══"
    echo ""
    echo "  INPUTS:"
    echo "    [0] Screen:       $SCREEN (1920×1080, 15s, looped)"
    echo "    [1] TTS:          $TTS_DIR/*.mp3 → ${TTS_DUR}s concatenated"
    echo "    [2] whoosh.mp3    → sfx@0.0s, sfx@37.0s"
    echo "    [3] ding.mp3      → sfx@5.0s, sfx@11.0s"
    echo "    [4] pop.mp3       → sfx@18.0s, sfx@31.0s"
    echo "    [5] success.mp3   → sfx@24.0s"
    echo "    [6] click.wav     → sfx@34.0s"
    echo ""
    echo "  VIDEO CHAIN:"
    echo "    crop to 9:16 → scale 1242×2208 (+15% zoom)"
    echo "    → crop 1080×1920 + sin/cos pan → 30fps → yuv420p"
    echo "    → 6 timed text overlays:"
    echo "        1.5–5s     '5 AI AGENTS'          white/80px"
    echo "        7–11s      'BUILDING TOGETHER'     green/68px"
    echo "        15–19s     'IN REAL TIME'          orange/56px"
    echo "        23–28s     'HTML CSS JS TESTS'     blue/48px"
    echo "        34–39s     'READY TO TRY IT?'      yellow/72px"
    echo "        40–45s     'github.com/...'        white/36px"
    echo ""
    echo "  AUDIO CHAIN:"
    echo "    TTS @ volume 1.0, padded to ${DURATION}s"
    echo "    8× SFX @ volume 0.35, delayed via adelay"
    echo "    amix=9 streams → AAC 192kbps 48kHz"
    echo ""
    echo "  OUTPUT:"
    echo "    $OUTPUT"
    echo "    1080×1920 (9:16), ${DURATION}s, CRF 20, x264 medium"
    exit 0
fi

echo "╔══════════════════════════════════════════════════╗"
echo "║        COMPOSING FINAL VIDEO                     ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Screen:    screen.mp4 (1920×1080, looped)       ║"
echo "║  TTS:       ${TTS_DUR}s (5 clips)                ║"
echo "║  SFX:       8 events (whoosh/ding/pop/success)   ║"
echo "║  Overlays:  6 timed text hooks                   ║"
echo "║  Zoom:      Ken Burns (sin/cos oscillation)      ║"
echo "║  Duration:  ${DURATION}s                          ║"
echo "║  Output:    $(basename "$OUTPUT")                ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

"${CMD[@]}" 2>&1 | tail -20

# ─── Verify ────────────────────────────────────────────────────────────────
if [[ -f "$OUTPUT" ]]; then
    size=$(du -h "$OUTPUT" | cut -f1)
    out_dur=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTPUT" | cut -d. -f1)
    echo ""
    echo "╔══════════════════════════════════════════════════╗"
    echo "║        VIDEO COMPOSED SUCCESSFULLY ✓             ║"
    echo "╠══════════════════════════════════════════════════╣"
    echo "║  File:     $OUTPUT"
    echo "║  Size:     $size"
    echo "║  Duration: ${out_dur}s"
    echo "║  Format:   1080×1920 (9:16 vertical)"
    echo "╚══════════════════════════════════════════════════╝"
    echo ""
    echo "  Preview:  ffplay \"$OUTPUT\""
    echo "  Upload:   Ready for TikTok / Reels / Shorts"
else
    echo "ERROR: Composition failed"
    exit 1
fi
