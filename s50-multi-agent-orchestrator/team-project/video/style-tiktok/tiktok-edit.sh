#!/usr/bin/env bash
# ============================================================================
# TikTok Vertical Video Editor (ffmpeg)
# Creates a 9:16 (1080x1920) vertical video with:
#   - Hook in first 2 seconds (flash + zoom + shake + bold text)
#   - Fast cuts every 2-3 seconds
#   - Zoom / Ken Burns effects (alternating in/out)
#   - Flash transitions at every cut
#   - Text overlays with animation (hook, mid-roll, CTA)
#   - Sound effect timings (bass drop, pop at cuts, whoosh at mid)
#   - Vignette + color grade for cinematic TikTok look
#
# Usage:
#   ./tiktok-edit.sh input1.mp4 input2.mp4 input3.mp4 -o output.mp4
#   ./tiktok-edit.sh --demo          # generate a test from colour bars
#
# Requirements: ffmpeg >= 5.0, ffprobe, bc
# ============================================================================

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
WIDTH=1080
HEIGHT=1920
FPS=30
CUT_MIN=2.0          # min seconds per clip segment
CUT_MAX=3.0          # max seconds per clip segment
TOTAL_DURATION=15    # target total duration (seconds) — TikTok sweet spot
HOOK_DURATION=2.0    # first N seconds = the hook
ZOOM_FACTOR=1.15     # max zoom-in amplitude (1.0 = none)
FONT="Impact"
FONTCOLOR="white"
FONTSIZE=90
BORDERW=4
SHADOWCOLOR="black"
SHADOWX=3
SHADOWY=3
SFX_DIR="./sfx"      # folder with sound effects (pop.mp3, whoosh.mp3, bass.mp3)

# ── Text content (edit these!) ──────────────────────────────────────────────
HOOK_TEXT="WAIT FOR IT"       # big hook text, first 2s
MID_TEXT="NO WAY"             # mid-roll accent
CTA_TEXT="FOLLOW FOR MORE"    # end call-to-action

# ── Helpers ─────────────────────────────────────────────────────────────────
log()  { echo -e "\033[1;36m[EDIT]\033[0m $*"; }
die()  { echo -e "\033[1;31m[ERR]\033[0m  $*" >&2; exit 1; }
cmd()  { log "$ $*"; "$@"; }

round2() { LC_NUMERIC=C awk "BEGIN { printf \"%.2f\", $1 }"; }

need() { command -v "$1" &>/dev/null || die "Missing dependency: $1"; }
need ffmpeg
need ffprobe
need bc

# ── Probe helper ────────────────────────────────────────────────────────────
get_duration() {
    ffprobe -v error -show_entries format=duration \
        -of default=noprint_wrappers=1:nokey=1 "$1"
}

# ── Demo mode ───────────────────────────────────────────────────────────────
generate_demo_clips() {
    log "Generating 6 demo colour clips..."
    local colors=("red" "blue" "green" "yellow" "magenta" "cyan")
    local labels=("HOOK" "SCENE 1" "SCENE 2" "MID-ROLL" "CLIMAX" "OUTRO")
    mkdir -p _demo_clips
    for i in "${!colors[@]}"; do
        local out="_demo_clips/clip${i}.mp4"
        if [[ ! -f "$out" ]]; then
            cmd ffmpeg -y -f lavfi \
                -i "color=c=${colors[$i]}:s=${WIDTH}x${HEIGHT}:d=4:r=${FPS}" \
                -vf "drawtext=text='${labels[$i]}':fontsize=120:fontcolor=white:borderw=5:bordercolor=black:x=(w-text_w)/2:y=(h-text_h)/2" \
                -c:v libx264 -preset ultrafast -pix_fmt yuv420p "$out"
        fi
    done
    INPUTS=(_demo_clips/clip{0,1,2,3,4,5}.mp4)
    log "Demo clips ready."
}

# ── Parse args ──────────────────────────────────────────────────────────────
DEMO=false
INPUTS=()
OUTPUT="output_tiktok.mp4"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --demo) DEMO=true; shift ;;
        -o)     OUTPUT="$2"; shift 2 ;;
        -d)     TOTAL_DURATION="$2"; shift 2 ;;
        *)      INPUTS+=("$1"); shift ;;
    esac
done

if [[ ${#INPUTS[@]} -gt 1 ]] && [[ "$OUTPUT" == "output_tiktok.mp4" ]]; then
    OUTPUT="${INPUTS[-1]}"
    unset 'INPUTS[-1]'
fi

if $DEMO; then
    generate_demo_clips
elif [[ ${#INPUTS[@]} -eq 0 ]]; then
    die "Usage: $0 [--demo | input1.mp4 input2.mp4 ... -o output.mp4]"
fi

log "Inputs: ${INPUTS[*]}"
log "Output: $OUTPUT  |  ${WIDTH}x${HEIGHT} @ ${FPS}fps  |  Target: ${TOTAL_DURATION}s"

# ── Step 1: Cut source clips into segments ──────────────────────────────────
mkdir -p _segments
SEGMENTS=()
CUT_TIMES=()       # track cumulative cut times for SFX placement
seg_idx=0
elapsed=0.0
src_idx=0

log "Step 1 — Cutting segments (${CUT_MIN}-${CUT_MAX}s each)..."
while (( $(echo "$elapsed < $TOTAL_DURATION" | bc -l) )); do
    src="${INPUTS[$((src_idx % ${#INPUTS[@]}))]}"
    src_dur=$(get_duration "$src")

    # Random cut length between CUT_MIN and CUT_MAX
    seg_dur=$(echo "$CUT_MIN + ($RANDOM / 32767.0) * ($CUT_MAX - $CUT_MIN)" | bc -l)
    seg_dur=$(round2 "$seg_dur")

    # Don't overshoot total duration
    remaining=$(echo "$TOTAL_DURATION - $elapsed" | bc -l)
    if (( $(echo "$seg_dur > $remaining" | bc -l) )); then
        seg_dur=$(round2 "$remaining")
    fi

    # Random start point in source (leave room for seg_dur)
    max_start=$(echo "$src_dur - $seg_dur - 0.5" | bc -l)
    if (( $(echo "$max_start < 0" | bc -l) )); then max_start=0; fi
    start=$(echo "($RANDOM / 32767.0) * $max_start" | bc -l)
    start=$(round2 "$start")

    seg_file="_segments/seg_$(printf '%03d' $seg_idx).mp4"
    if [[ ! -f "$seg_file" ]]; then
        cmd ffmpeg -y -ss "$start" -i "$src" -t "$seg_dur" \
            -vf "scale=${WIDTH}:${HEIGHT}:force_original_aspect_ratio=decrease,pad=${WIDTH}:${HEIGHT}:(ow-iw)/2:(oh-ih)/2:black" \
            -c:v libx264 -preset fast -pix_fmt yuv420p -an "$seg_file" 2>/dev/null
    fi
    SEGMENTS+=("$seg_file")
    CUT_TIMES+=("$elapsed")
    elapsed=$(echo "$elapsed + $seg_dur" | bc -l)
    seg_idx=$((seg_idx + 1))
    src_idx=$((src_idx + 1))
done
log "  Created ${#SEGMENTS[@]} segments totaling ~${elapsed}s"
log "  Cut points: ${CUT_TIMES[*]}"

# ── Step 2: Build per-segment filter (zoom, effects) ────────────────────────
log "Step 2 — Building complex filter graph..."

CONCAT_V=""
FILTER=""
in_labels=()
seg_count=${#SEGMENTS[@]}

for i in "${!SEGMENTS[@]}"; do
    label="v${i}"
    in_labels+=("[$label]")

    # ── Zoom (Ken Burns) effect ─────────────────────────────────────────
    # Alternate zoom-in vs zoom-out for variety
    if (( i % 2 == 0 )); then
        zoom_expr="min(${ZOOM_FACTOR},1+0.015*on/${FPS})"
    else
        zoom_expr="max(1.0,${ZOOM_FACTOR}-0.015*on/${FPS})"
    fi

    # ── Per-segment filter chain ────────────────────────────────────────
    seg_filter="[$i:v]scale=${WIDTH}*2:${HEIGHT}*2,zoompan=z='${zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=${WIDTH}x${HEIGHT}:fps=${FPS}"

    # ── Hook segment: boosted brightness + saturation ───────────────────
    if (( i == 0 )); then
        seg_filter+=",eq=brightness=0.15:saturation=1.3"
    fi

    # ── Flash transition at every cut (brightness pulse) ────────────────
    if (( i > 0 )); then
        seg_filter+=",eq=brightness='0.1*if(lt(t,0.1),1-t/0.1,0)':saturation=1.1"
    fi

    seg_filter+="[$label];"
    FILTER+="$seg_filter"
done

# ── Step 3: Text overlays ───────────────────────────────────────────────────
log "Step 3 — Adding text overlays..."

# Vignette + color grade applied to concatenated stream before text
# Then drawtext layers on top

MID_TIME=$(round2 "$(echo "$TOTAL_DURATION / 2" | bc -l)")
CTA_START=$(round2 "$(echo "$TOTAL_DURATION - 2.0" | bc -l)")

TEXT_FILTER="[vout]"

# Vignette for cinematic look
TEXT_FILTER+="vignette=PI/4,"

# Slight color grade: lift shadows, warm highlights
TEXT_FILTER+="curves=r='0/0 0.5/0.55 1/1':g='0/0 0.5/0.48 1/0.95':b='0/0 0.5/0.45 1/0.9',"

# Hook text: scale up from 0, shake, then fade out at 2s
TEXT_FILTER+="drawtext=text='${HOOK_TEXT}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
TEXT_FILTER+="fontsize='if(lt(t,0.3),${FONTSIZE}*t/0.3,${FONTSIZE})':"
TEXT_FILTER+="fontcolor=${FONTCOLOR}:borderw=${BORDERW}:bordercolor=black:"
TEXT_FILTER+="shadowcolor=${SHADOWCOLOR}:shadowx=${SHADOWX}:shadowy=${SHADOWY}:"
TEXT_FILTER+="x='(w-text_w)/2+3*sin(2*PI*t*15)':y='(h-text_h)/2':"
TEXT_FILTER+="enable='between(t,0,${HOOK_DURATION})'"

# Mid-roll accent text — pops in with size animation
TEXT_FILTER+=",drawtext=text='${MID_TEXT}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
TEXT_FILTER+="fontsize='if(lt(t-${MID_TIME},0.2),${FONTSIZE}*(t-${MID_TIME})/0.2,${FONTSIZE})':"
TEXT_FILTER+="fontcolor=yellow:borderw=5:bordercolor=black:"
TEXT_FILTER+="x='(w-text_w)/2':y='(h-text_h)/3':"
TEXT_FILTER+="enable='between(t,${MID_TIME},${MID_TIME}+1.5)'"

# CTA at the end — slides up from bottom
TEXT_FILTER+=",drawtext=text='${CTA_TEXT}':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
TEXT_FILTER+="fontsize=70:fontcolor=white:borderw=4:bordercolor=black:"
TEXT_FILTER+="x='(w-text_w)/2':y='if(lt(t-${CTA_START},0.3),h*0.8+200*(1-(t-${CTA_START})/0.3),h*0.8)':"
TEXT_FILTER+="enable='between(t,${CTA_START},${TOTAL_DURATION})'"

TEXT_FILTER+="[vfinal]"

# ── Step 4: Sound effects layer ─────────────────────────────────────────────
log "Step 4 — Preparing sound effects..."

SFX_INPUTS=()
USE_AUDIO=false

if [[ -d "$SFX_DIR" ]]; then
    for sfx in bass.mp3 pop.mp3 whoosh.mp3; do
        if [[ -f "$SFX_DIR/$sfx" ]]; then
            SFX_INPUTS+=("$SFX_DIR/$sfx")
        fi
    done
fi

# Generate placeholder sine tones if no SFX files found
if [[ ${#SFX_INPUTS[@]} -eq 0 ]]; then
    log "  No SFX in $SFX_DIR — generating placeholder tones..."
    mkdir -p _sfx
    ffmpeg -y -f lavfi -i "sine=frequency=60:duration=0.15" \
        -af "afade=t=out:st=0.05:d=0.1" -c:a aac _sfx/bass.m4a 2>/dev/null
    ffmpeg -y -f lavfi -i "sine=frequency=800:duration=0.08" \
        -af "afade=t=out:st=0.02:d=0.06" -c:a aac _sfx/pop.m4a 2>/dev/null
    ffmpeg -y -f lavfi -i "sine=frequency=200:duration=0.4" \
        -af "asetrate=44100*1.5,atempo=0.7,afade=t=in:d=0.1,afade=t=out:st=0.2:d=0.2" \
        -c:a aac _sfx/whoosh.m4a 2>/dev/null
    SFX_INPUTS=(_sfx/bass.m4a _sfx/pop.m4a _sfx/whoosh.m4a)
fi

USE_AUDIO=true

# ── Step 5: Assemble the ffmpeg command ─────────────────────────────────────
log "Step 5 — Assembling final video..."

FFMPEG_CMD=(ffmpeg -y)

for seg in "${SEGMENTS[@]}"; do
    FFMPEG_CMD+=(-i "$seg")
done
for sfx in "${SFX_INPUTS[@]}"; do
    FFMPEG_CMD+=(-i "$sfx")
done

sfx_start_idx=${#SEGMENTS[@]}

# ── Build the full filter graph ─────────────────────────────────────────────
FULL_FILTER=""

# Part A: Per-segment zoom/effects
FULL_FILTER+="$FILTER"

# Part B: Concatenate all segments
inputs_for_concat=""
for label in "${in_labels[@]}"; do
    inputs_for_concat+="$label"
done
FULL_FILTER+="${inputs_for_concat}concat=n=${seg_count}:v=1:a=0[vout];"

# Part C: Text overlays + vignette + color grade
FULL_FILTER+="$TEXT_FILTER"

# Part D: Audio — silent base + SFX at timed positions
if $USE_AUDIO; then
    FULL_FILTER+=";anullsrc=r=44100:cl=stereo[abase]"

    bass_idx=$sfx_start_idx
    pop_idx=$((sfx_start_idx + 1))
    whoosh_idx=$((sfx_start_idx + 2))

    # Bass drop at t=0 (hook)
    FULL_FILTER+=";[${bass_idx}:a]adelay=0|0,volume=0.6[abass]"

    # Pop at each actual cut point (skip first segment start)
    mix_labels="[abase][abass]"
    pop_count=0
    for ct in "${CUT_TIMES[@]}"; do
        if (( pop_count > 0 )); then
            ct_ms=$(awk "BEGIN { printf \"%d\", $ct * 1000 }")
            FULL_FILTER+=";[${pop_idx}:a]adelay=${ct_ms}|${ct_ms},volume=0.4[apop${pop_count}]"
            mix_labels+="[apop${pop_count}]"
        fi
        pop_count=$((pop_count + 1))
    done

    # Whoosh at mid-roll
    mid_ms=$(awk "BEGIN { printf \"%d\", $TOTAL_DURATION * 500 }")
    FULL_FILTER+=";[${whoosh_idx}:a]adelay=${mid_ms}|${mid_ms},volume=0.5[awhoosh]"
    mix_labels+="[awhoosh]"

    # Count total audio inputs for amix
    total_audio=$((2 + ${#CUT_TIMES[@]} - 1 + 1))  # base + bass + pops + whoosh
    FULL_FILTER+=";${mix_labels}amix=inputs=${total_audio}:normalize=0[afinal]"
fi

FFMPEG_CMD+=(-filter_complex "$FULL_FILTER")
FFMPEG_CMD+=(-map "[vfinal]")
if $USE_AUDIO; then
    FFMPEG_CMD+=(-map "[afinal]")
fi

FFMPEG_CMD+=(
    -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p
    -c:a aac -b:a 192k
    -t "$TOTAL_DURATION"
    -movflags +faststart
    "$OUTPUT"
)

# ── Run it ──────────────────────────────────────────────────────────────────
log "Running final encode..."
cmd "${FFMPEG_CMD[@]}"

# ── Cleanup ─────────────────────────────────────────────────────────────────
log "Cleaning up temp files..."
rm -rf _segments _sfx _demo_clips 2>/dev/null || true

# ── Done ────────────────────────────────────────────────────────────────────
OUT_DUR=$(get_duration "$OUTPUT" 2>/dev/null || echo "?")
OUT_SIZE=$(du -h "$OUTPUT" 2>/dev/null | cut -f1)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  TikTok video ready!"
echo "  📁  $OUTPUT"
echo "  ⏱  ${OUT_DUR}s  |  📐 ${WIDTH}x${HEIGHT}  |  💾 ${OUT_SIZE}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
