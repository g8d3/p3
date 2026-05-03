#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# compose.sh - Final FFmpeg Composition Pipeline
#
# Composes a 9:16 vertical video from:
#   1. Screen recording (any resolution → cropped to 1080×1920)
#   2. TTS narration audio (one file or directory of clips)
#   3. Sound effects (whoosh, ding, pop, click, etc.)
#   4. Timed text overlays (hooks, key points, CTAs)
#   5. Dynamic zoom/pan effects (Ken Burns style)
#
# Usage:
#   ./compose.sh [OPTIONS]
#
# Options:
#   -s, --screen  FILE       Screen recording input            (required)
#   -t, --tts     FILE|DIR   TTS audio file or directory        (optional)
#   -f, --sfx     DIR        Sound effects directory             (default: ../sfx)
#   -o, --output  FILE       Output file                         (default: ../output/final.mp4)
#   -l, --lang    LANG       Language for text overlays: en|es   (default: en)
#   -d, --duration SECS      Override total duration in seconds   (auto from TTS)
#       --dry-run            Print the ffmpeg command without executing
#       --no-zoom            Disable zoom effects
#       --no-text            Disable text overlays
#       --no-sfx             Disable sound effects
#   -h, --help               Show this help
#
# Environment overrides:
#   FONT_PATH   - Path to .ttf font file
#   SFX_VOLUME  - Sound effects volume 0.0–1.0  (default: 0.35)
#   TTS_VOLUME  - TTS narration volume 0.0–1.0  (default: 1.0)
#   CRF         - Video quality 0–51, lower=better (default: 20)
#   PRESET      - x264 speed preset              (default: medium)
###############################################################################

# ─── Defaults ────────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

SCREEN=""
TTS_INPUT=""
SFX_DIR="$(realpath "$PROJECT_DIR/sfx" 2>/dev/null || echo "$PROJECT_DIR/sfx")"
OUTPUT="$PROJECT_DIR/output/final.mp4"
LANG="en"
OVERRIDE_DURATION=""
DRY_RUN=false
ENABLE_ZOOM=true
ENABLE_TEXT=true
ENABLE_SFX=true

FONT_PATH="${FONT_PATH:-}"
SFX_VOLUME="${SFX_VOLUME:-0.35}"
TTS_VOLUME="${TTS_VOLUME:-1.0}"
CRF="${CRF:-20}"
PRESET="${PRESET:-medium}"

TMP_FILES=()
cleanup() { for f in "${TMP_FILES[@]}"; do [[ -f "$f" ]] && rm -f "$f"; done; }
trap cleanup EXIT

# ─── Argument Parsing ───────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--screen)   SCREEN="$2";            shift 2 ;;
        -t|--tts)      TTS_INPUT="$(realpath "$2" 2>/dev/null || echo "$2")";         shift 2 ;;
        -f|--sfx)      SFX_DIR="$(realpath "$2" 2>/dev/null || echo "$2")";           shift 2 ;;
        -o|--output)   OUTPUT="$2";            shift 2 ;;
        -l|--lang)     LANG="$2";              shift 2 ;;
        -d|--duration) OVERRIDE_DURATION="$2"; shift 2 ;;
        --dry-run)     DRY_RUN=true;           shift   ;;
        --no-zoom)     ENABLE_ZOOM=false;      shift   ;;
        --no-text)     ENABLE_TEXT=false;      shift   ;;
        --no-sfx)      ENABLE_SFX=false;       shift   ;;
        -h|--help)
            sed -n '/^# Usage:/,/^###/p' "$0" | head -n -1 | sed 's/^# \?//'
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ─── Validate ───────────────────────────────────────────────────────────────
[[ -z "$SCREEN" ]] && { echo "ERROR: Screen recording required (-s)"; exit 1; }
[[ -f "$SCREEN" ]] || { echo "ERROR: Not found: $SCREEN"; exit 1; }
SCREEN="$(realpath "$SCREEN")"
mkdir -p "$(dirname "$OUTPUT")"
OUTPUT="$(realpath "$(dirname "$OUTPUT")")/$(basename "$OUTPUT")"

# ─── Detect Font ────────────────────────────────────────────────────────────
find_font() {
    [[ -n "$FONT_PATH" && -f "$FONT_PATH" ]] && { echo "$FONT_PATH"; return; }
    local candidates=(
        /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
        /usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf
        /usr/share/fonts/truetype/noto/NotoSans-Bold.ttf
        /usr/share/fonts/TTF/DejaVuSans-Bold.ttf
        /usr/share/fonts/liberation-sans/LiberationSans-Bold.ttf
        /usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf
        /System/Library/Fonts/Helvetica.ttc
    )
    for f in "${candidates[@]}"; do [[ -f "$f" ]] && { echo "$f"; return; }; done
    find /usr/share/fonts -name "*Bold*.ttf" 2>/dev/null | head -1
}

FONT=$(find_font)
if [[ -n "$FONT" ]]; then
    echo "Font: $FONT"
    FONT_ARG="fontfile=${FONT}"
else
    echo "WARNING: No bold font found – text overlays will use ffmpeg default"
    FONT_ARG=""
fi

# ─── Probe Screen Recording ────────────────────────────────────────────────
echo "Probing screen recording..."
SRC_W=$(ffprobe -v quiet -select_streams v:0 -show_entries stream=width  -of csv=p=0 "$SCREEN")
SRC_H=$(ffprobe -v quiet -select_streams v:0 -show_entries stream=height -of csv=p=0 "$SCREEN")
SRC_FPS=$(ffprobe -v quiet -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$SCREEN")
SRC_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$SCREEN" | cut -d. -f1)
echo "  Source: ${SRC_W}×${SRC_H} @ ${SRC_FPS}fps, ${SRC_DUR}s"

OUT_W=1080
OUT_H=1920

# ─── Prepare TTS Audio ─────────────────────────────────────────────────────
TTS_FILE=""
TTS_COUNT=0
TTS_DUR=0

prepare_tts() {
    [[ -z "$TTS_INPUT" ]] && { echo "No TTS provided – skipping narration"; return; }

    if [[ -f "$TTS_INPUT" ]]; then
        TTS_FILE="$TTS_INPUT"
        TTS_COUNT=1
        TTS_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$TTS_FILE")
        echo "TTS: single file (${TTS_DUR}s)"
        return
    fi

    if [[ -d "$TTS_INPUT" ]]; then
        local clips=()
        while IFS= read -r -d '' f; do clips+=("$(realpath "$f")"); done \
            < <(find "$TTS_INPUT" -maxdepth 1 \( -name "*.mp3" -o -name "*.wav" -o -name "*.ogg" -o -name "*.m4a" \) -print0 | sort -z)

        TTS_COUNT=${#clips[@]}
        [[ $TTS_COUNT -eq 0 ]] && { echo "WARNING: TTS directory empty"; return; }

        echo "TTS: $TTS_COUNT clips in directory"

        # Concatenate all clips with tiny silence gap between them
        local concat_file
        concat_file=$(mktemp /tmp/compose-tts-XXXXXX.txt)
        TMP_FILES+=("$concat_file")
        for clip in "${clips[@]}"; do
            echo "file '$clip'" >> "$concat_file"
        done

        TTS_FILE=$(mktemp /tmp/compose-tts-full-XXXXXX.mp3)
        TMP_FILES+=("$TTS_FILE")
        ffmpeg -y -f concat -safe 0 -i "$concat_file" \
            -af "apad=pad_dur=0.5" \
            -c:a libmp3lame -q:a 2 "$TTS_FILE" 2>/dev/null
        TTS_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$TTS_FILE")
        echo "  Concatenated → ${TTS_DUR}s"
    fi
}

prepare_tts

# ─── Determine Total Duration ──────────────────────────────────────────────
if [[ -n "$OVERRIDE_DURATION" ]]; then
    DURATION="$OVERRIDE_DURATION"
elif [[ -n "$TTS_DUR" && "$TTS_DUR" != "0" ]]; then
    DURATION=$(echo "$TTS_DUR" | cut -d. -f1)
    # Add 3s buffer for outro/CTA
    DURATION=$((DURATION + 3))
else
    DURATION=$SRC_DUR
fi
[[ -z "$DURATION" || "$DURATION" == "N/A" ]] && DURATION=45
echo "Total duration: ${DURATION}s"

# ─── Prepare Sound Effects ──────────────────────────────────────────────────
declare -A SFX_MAP=()

prepare_sfx() {
    [[ "$ENABLE_SFX" == "false" ]] && { echo "SFX disabled"; return; }
    [[ ! -d "$SFX_DIR" ]] && { echo "SFX dir not found: $SFX_DIR"; return; }

    local count
    count=$(find "$SFX_DIR" -maxdepth 1 \( -name "*.wav" -o -name "*.mp3" -o -name "*.ogg" \) | wc -l)
    [[ $count -eq 0 ]] && { echo "No SFX files"; return; }

    echo "SFX: $count files in $SFX_DIR"
    for f in "$SFX_DIR"/*.wav "$SFX_DIR"/*.mp3 "$SFX_DIR"/*.ogg; do
        [[ -f "$f" ]] || continue
        local name
        name=$(basename "$f" | sed 's/\.[^.]*$//' | tr '[:upper:]' '[:lower:]')
        SFX_MAP["$name"]="$(realpath "$f")"
    done
}

prepare_sfx

# ─── Define SFX Timeline ───────────────────────────────────────────────────
# Format: sfx_name@time_seconds
# Timed to match the English TTS script:
#   0-4s   hook        → whoosh at start
#   4-10s  agents1     → ding at 5s
#   10-17s agents2     → ding at 11s
#   17-23s ship        → pop at 18s
#   23-30s future      → success at 24s
#   30-36s outro       → pop at 31s, click at 34s
#   36-39s CTA buffer  → whoosh at 37s
define_sfx_timeline() {
    local entries=()
    local sfx_at=(
        "whoosh@0.0"
        "ding@5.0"
        "ding@11.0"
        "pop@18.0"
        "success@24.0"
        "pop@31.0"
        "click@34.0"
        "whoosh@37.0"
    )
    for entry in "${sfx_at[@]}"; do
        local name="${entry%@*}"
        local time="${entry#*@}"
        # Only include if we have this SFX file and time < duration
        if [[ -n "${SFX_MAP[$name]+_}" ]]; then
            local t_int=${time%.*}
            [[ $t_int -lt $DURATION ]] && entries+=("$entry")
        fi
    done
    printf '%s\n' "${entries[@]}"
}

# ─── Build Filter Complex Script ───────────────────────────────────────────
# Written to a temp file to avoid all shell-escaping nightmares
build_filter() {
    local filter_file
    filter_file=$(mktemp /tmp/compose-filter-XXXXXX.txt)
    TMP_FILES+=("$filter_file")

    # ── VIDEO CHAIN ──
    local v=""

    # 1) Crop source to 9:16 from center
    v+="[0:v]crop=ih*9/16:ih:iw/2-iw*9/32:0"

    # 2) Scale + optional Ken Burns zoom/pan
    if [[ "$ENABLE_ZOOM" == "true" ]]; then
        local zoom=1.15
        local sw sh
        sw=$(echo "$OUT_W * $zoom" | bc | cut -d. -f1)
        sh=$(echo "$OUT_H * $zoom" | bc | cut -d. -f1)
        v+=",scale=${sw}:${sh}"
        # Slow oscillating crop offset = gentle pan effect
        v+=",crop=${OUT_W}:${OUT_H}"
        v+=":(${sw}-${OUT_W})/2+sin(t*0.5)*30"
        v+=":(${sh}-${OUT_H})/2+cos(t*0.3)*20"
    else
        v+=",scale=${OUT_W}:${OUT_H}"
    fi

    # 3) FPS + pixel format
    v+=",fps=30,format=yuv420p"

    # 4) Text overlays
    if [[ "$ENABLE_TEXT" == "true" ]]; then
        if [[ "$LANG" == "es" ]]; then
            v+=",drawtext=${FONT_ARG}:text='5 AGENTES':fontsize=80:fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h/5:enable='between(t,1.5,5)'"
            v+=",drawtext=${FONT_ARG}:text='CONSTRUYENDO\nJUNTOS':fontsize=68:fontcolor=#00ff88:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h/3:enable='between(t,7,11)'"
            v+=",drawtext=${FONT_ARG}:text='EN TIEMPO REAL':fontsize=56:fontcolor=#ff9800:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h/2:enable='between(t,15,19)'"
            v+=",drawtext=${FONT_ARG}:text='HTML  CSS  JS\nTESTS  DOCS':fontsize=48:fontcolor=#00bfff:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h*0.55:enable='between(t,23,28)'"
            v+=",drawtext=${FONT_ARG}:text='LISTO PARA\nINTENTARLO?':fontsize=72:fontcolor=yellow:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h/3:enable='between(t,34,39)'"
            v+=",drawtext=${FONT_ARG}:text='github.com/tu-proyecto':fontsize=36:fontcolor=white:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h*0.85:enable='between(t,40,45)'"
        else
            v+=",drawtext=${FONT_ARG}:text='5 AI AGENTS':fontsize=80:fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h/5:enable='between(t,1.5,5)'"
            v+=",drawtext=${FONT_ARG}:text='BUILDING\nTOGETHER':fontsize=68:fontcolor=#00ff88:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h/3:enable='between(t,7,11)'"
            v+=",drawtext=${FONT_ARG}:text='IN REAL TIME':fontsize=56:fontcolor=#ff9800:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h/2:enable='between(t,15,19)'"
            v+=",drawtext=${FONT_ARG}:text='HTML  CSS  JS\nTESTS  DOCS':fontsize=48:fontcolor=#00bfff:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h*0.55:enable='between(t,23,28)'"
            v+=",drawtext=${FONT_ARG}:text='READY TO\nTRY IT?':fontsize=72:fontcolor=yellow:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h/3:enable='between(t,34,39)'"
            v+=",drawtext=${FONT_ARG}:text='github.com/your-project':fontsize=36:fontcolor=white:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h*0.85:enable='between(t,40,45)'"
        fi
    fi

    v+="[vout]"
    echo -n "$v" > "$filter_file"

    # ── AUDIO CHAIN ──
    local has_audio=false
    local labels=()

    if [[ -n "$TTS_FILE" && -f "$TTS_FILE" ]] || [[ "$ENABLE_SFX" == "true" ]]; then
        echo -n ";" >> "$filter_file"

        # TTS: volume adjust + extend to cover screen loop
        if [[ -n "$TTS_FILE" && -f "$TTS_FILE" ]]; then
            echo -n "[1:a]volume=${TTS_VOLUME},apad=pad_dur=${DURATION}[tts]" >> "$filter_file"
            labels+=("[tts]")
            has_audio=true
        fi

        # SFX with adelay for each timed event
        local sfx_timeline
        sfx_timeline=$(define_sfx_timeline)

        if [[ -n "$sfx_timeline" ]]; then
            # Map unique SFX files → input indices
            local -a sfx_files=()
            local -A sfx_idx_map=()
            local base_idx=1
            [[ -n "$TTS_FILE" && -f "$TTS_FILE" ]] && base_idx=2

            while IFS= read -r entry; do
                local name="${entry%@*}"
                [[ -z "$name" ]] && continue
                local path="${SFX_MAP[$name]}"
                if [[ -z "${sfx_idx_map[$path]+_}" ]]; then
                    sfx_files+=("$path")
                    sfx_idx_map["$path"]=$(( ${#sfx_files[@]} + base_idx - 1 ))
                fi
            done <<< "$sfx_timeline"

            # Generate delay filters
            local sfx_n=0
            while IFS= read -r entry; do
                local name="${entry%@*}"
                local time="${entry#*@}"
                [[ -z "$name" || -z "$time" ]] && continue

                local path="${SFX_MAP[$name]}"
                local idx="${sfx_idx_map[$path]}"
                local delay_ms
                delay_ms=$(echo "$time * 1000" | bc | cut -d. -f1)

                if [[ "$has_audio" == "true" || $sfx_n -gt 0 ]]; then
                    echo -n ";" >> "$filter_file"
                fi

                echo -n "[${idx}:a]adelay=${delay_ms}|${delay_ms},volume=${SFX_VOLUME}[sfx${sfx_n}]" >> "$filter_file"
                labels+=("[sfx${sfx_n}]")
                has_audio=true
                ((sfx_n++)) || true
            done <<< "$sfx_timeline"
        fi

        # Mix all audio streams
        if [[ ${#labels[@]} -gt 0 ]]; then
            echo -n ";" >> "$filter_file"
            if [[ ${#labels[@]} -eq 1 ]]; then
                echo -n "${labels[0]}[aout]" >> "$filter_file"
            else
                for l in "${labels[@]}"; do echo -n "$l" >> "$filter_file"; done
                echo -n "amix=inputs=${#labels[@]}:duration=longest:dropout_transition=2[aout]" >> "$filter_file"
            fi
        fi
    fi

    echo "$filter_file"
}

# ─── Build FFmpeg Command ──────────────────────────────────────────────────
FILTER_FILE=$(build_filter)

CMD=(ffmpeg -y)

# Input 0: Screen recording (loop if shorter than total duration)
if (( SRC_DUR < DURATION )); then
    echo "Screen recording (${SRC_DUR}s) shorter than output (${DURATION}s) – will loop"
    CMD+=(-stream_loop -1 -i "$SCREEN")
else
    CMD+=(-i "$SCREEN")
fi

# Input 1: TTS audio
HAS_TTS=false
if [[ -n "$TTS_FILE" && -f "$TTS_FILE" ]]; then
    CMD+=(-i "$TTS_FILE")
    HAS_TTS=true
fi

# Inputs 2+: Unique SFX files
SFX_INPUTS=()
SFX_SEEN=()
SFX_TIMELINE=$(define_sfx_timeline)

if [[ "$ENABLE_SFX" == "true" && -n "$SFX_TIMELINE" ]]; then
    while IFS= read -r entry; do
        name="${entry%@*}"
        [[ -z "$name" ]] && continue
        path="${SFX_MAP[$name]}"
        already=false
        for seen in "${SFX_SEEN[@]+"${SFX_SEEN[@]}"}"; do
            [[ "$seen" == "$path" ]] && already=true && break
        done
        if [[ "$already" == "false" ]]; then
            CMD+=(-i "$path")
            SFX_INPUTS+=("$path")
            SFX_SEEN+=("$path")
        fi
    done <<< "$SFX_TIMELINE"
fi

# Filter complex from file (no escaping issues)
CMD+=(-filter_complex_script "$FILTER_FILE")

# Map outputs
CMD+=(-map "[vout]")
if [[ "$HAS_TTS" == "true" ]] || [[ ${#SFX_INPUTS[@]} -gt 0 ]]; then
    CMD+=(-map "[aout]")
fi

# Encoding
CMD+=(-c:v libx264 -preset "$PRESET" -crf "$CRF")
CMD+=(-c:a aac -b:a 192k -ar 48000)
CMD+=(-movflags +faststart -pix_fmt yuv420p)
CMD+=(-t "$DURATION")

# Metadata
CMD+=(-metadata "title=5 AI Agents Build an App")
CMD+=(-metadata "comment=Generated by multi-agent video composer")
CMD+=("$OUTPUT")

# ─── Print Summary ─────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║           VIDEO COMPOSER PIPELINE                ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Screen:    $(basename "$SCREEN")"
echo "║  TTS clips: $TTS_COUNT  (${TTS_DUR}s)"
echo "║  SFX:       ${#SFX_INPUTS[@]} unique files"
echo "║  Language:  $LANG"
echo "║  Zoom:      $ENABLE_ZOOM"
echo "║  Text:      $ENABLE_TEXT"
echo "║  Duration:  ${DURATION}s"
echo "║  Output:    $(basename "$OUTPUT")"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ─── Dry Run ───────────────────────────────────────────────────────────────
if [[ "$DRY_RUN" == "true" ]]; then
    echo "═══ DRY RUN ═══"
    echo ""
    echo "FFmpeg command:"
    printf '  %q \\\n' "${CMD[@]}" | sed '$s/ \\$//'
    echo ""
    echo "Filter complex:"
    sed 's/;/;\n/g' "$FILTER_FILE"
    echo ""
    echo "SFX timeline:"
    echo "$SFX_TIMELINE" | sed 's/^/  /'
    exit 0
fi

# ─── Execute ───────────────────────────────────────────────────────────────
echo "Composing video..."
echo ""

"${CMD[@]}" 2>&1 | while IFS= read -r line; do
    if [[ "$line" == *"frame="* ]]; then
        frame=$(echo "$line" | grep -oP 'frame=\s*\K[0-9]+' 2>/dev/null || true)
        [[ -n "$frame" ]] && printf "\r  Encoding frame %s..." "$frame"
    elif [[ "$line" == *"error"* || "$line" == *"Error"* ]]; then
        echo "  ⚠ $line" >&2
    fi
done
true

# ─── Verify ────────────────────────────────────────────────────────────────
if [[ -f "$OUTPUT" ]]; then
    size=$(du -h "$OUTPUT" | cut -f1)
    out_dur=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTPUT" | cut -d. -f1)

    echo ""
    echo ""
    echo "╔══════════════════════════════════════════════════╗"
    echo "║        VIDEO COMPOSED SUCCESSFULLY ✓             ║"
    echo "╠══════════════════════════════════════════════════╣"
    echo "║  File:     $OUTPUT"
    echo "║  Size:     $size"
    echo "║  Duration: ${out_dur}s"
    echo "║  Format:   ${OUT_W}×${OUT_H} (9:16 vertical)"
    echo "╚══════════════════════════════════════════════════╝"
    echo ""
    echo "  Preview:  ffplay \"$OUTPUT\""
    echo "  Upload:   Ready for TikTok / Reels / Shorts"
else
    echo "ERROR: Composition failed – no output file"
    exit 1
fi
