#!/usr/bin/env bash
set -euo pipefail

# Genera TODAS las variaciones de video
# Español × Estilos + Inglés × Estilos

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="$PROJECT_DIR/output"
SCREEN="$PROJECT_DIR/recordings/screen.mp4"
mkdir -p "$OUTPUT"

# Verificar que existe la grabación
if [[ ! -f "$SCREEN" ]]; then
    echo "❌ No hay grabación de pantalla: $SCREEN"
    exit 1
fi

echo "🎬 Generando variaciones de video..."
echo ""

# Duración objetivo
TARGET_DUR=45

# Textos por idioma
declare -A TEXTS_ES=(
    [hook]="5 AGENTES DE IA"
    [subtitle]="CONSTRUYENDO UNA APP"
    [detail]="EN PARALELO • SIN HUMANOS"
    [agents]="HTML • CSS • JS • TESTS • DOCS"
    [process]="CADA UNO EN SU CARPETA"
    [speed]="RESULTADO EN 30 SEGUNDOS"
    [result]="1341 LINEAS DE CODIGO"
    [end]="ESTO ES EL FUTURO"
)

declare -A TEXTS_EN=(
    [hook]="5 AI AGENTS"
    [subtitle]="BUILDING AN APP"
    [detail]="IN PARALLEL • NO HUMANS"
    [agents]="HTML • CSS • JS • TESTS • DOCS"
    [process]="EACH IN THEIR OWN FOLDER"
    [speed]="RESULT IN 30 SECONDS"
    [result]="1341 LINES OF CODE"
    [end]="THIS IS THE FUTURE"
)

# Estilos de creadores
STYLES=("fireship" "networkchuck" "tiktok" "theo")

# Colores por estilo
declare -A STYLE_COLORS=(
    [fireship]="#f44336"      # Rojo fuego
    [networkchuck]="#4CAF50"   # Verde
    [tiktok]="#000000"         # Negro
    [theo]="#2196F3"           # Azul
)

# Tamaños de fuente por estilo
declare -A STYLE_FONT_SIZE=(
    [fireship]="80"    # Grande, impactante
    [networkchuck]="72" # Mediano, claro
    [tiktok]="64"      # Más pequeño, rápido
    [theo]="68"        # Limpio, profesional
)

generate_video() {
    local lang="$1"
    local style="$2"
    local output_file="$OUTPUT/video-${lang}-${style}.mp4"
    
    echo "  🎥 Generando: ${lang}-${style}"
    
    # Seleccionar textos según idioma
    if [[ "$lang" == "es" ]]; then
        declare -n TEXTS=TEXTS_ES
    else
        declare -n TEXTS=TEXTS_EN
    fi
    
    local color="${STYLE_COLORS[$style]}"
    local font_size="${STYLE_FONT_SIZE[$style]}"
    
    # Crear video con textos
    ffmpeg -y -stream_loop 4 -i "$SCREEN" \
        -vf "crop=ih*9/16:ih:iw/2-ih*9/32:0,scale=1080:1920,\
drawtext=text='${TEXTS[hook]}':fontsize=$((font_size+10)):fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h/6:enable='between(t,2,7)',\
drawtext=text='${TEXTS[subtitle]}':fontsize=$font_size:fontcolor=${color}:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h/4:enable='between(t,7,12)',\
drawtext=text='${TEXTS[detail]}':fontsize=$((font_size-8)):fontcolor=#ffeb3b:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h/3:enable='between(t,12,17)',\
drawtext=text='${TEXTS[agents]}':fontsize=$((font_size-12)):fontcolor=#00bcd4:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h/2:enable='between(t,17,23)',\
drawtext=text='${TEXTS[process]}':fontsize=$((font_size-4)):fontcolor=#e91e63:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h*2/5:enable='between(t,23,29)',\
drawtext=text='${TEXTS[speed]}':fontsize=$((font_size-8)):fontcolor=#4CAF50:borderw=2:bordercolor=black:x=(w-text_w)/2:y=h/2:enable='between(t,29,35)',\
drawtext=text='${TEXTS[result]}':fontsize=$font_size:fontcolor=#ff9800:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h*2/5:enable='between(t,35,41)',\
drawtext=text='${TEXTS[end]}':fontsize=$((font_size+8)):fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2:y=h/3:enable='between(t,41,47)'" \
        -c:v libx264 -preset fast -crf 23 \
        -t $TARGET_DUR \
        "$output_file" 2>/dev/null
    
    # Agregar audio TTS si existe
    if [[ "$lang" == "en" ]] && ls "$PROJECT_DIR/audio-en/"*.mp3 2>/dev/null | head -1 > /dev/null; then
        # Crear silencio para rellenar
        ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=mono -t 5 /tmp/silence-5s.mp3 2>/dev/null
        
        # Concatenar clips TTS
        for f in "$PROJECT_DIR/audio-en/"clip-*.mp3; do echo "file '$f'"; done > /tmp/tts-var.txt
        echo "file '/tmp/silence-5s.mp3'" >> /tmp/tts-var.txt
        ffmpeg -y -f concat -safe 0 -i /tmp/tts-var.txt -c copy /tmp/tts-var-full.mp3 2>/dev/null
        
        # Mezclar
        ffmpeg -y -i "$output_file" -i /tmp/tts-var-full.mp3 \
            -i "$PROJECT_DIR/sfx/ding.mp3" \
            -i "$PROJECT_DIR/sfx/pop.mp3" \
            -filter_complex "[1:a]volume=1.0[tts];[2:a]adelay=12000|12000,volume=0.3[ding];[3:a]adelay=23000|23000,volume=0.3[pop];[tts][ding][pop]amix=inputs=3:duration=first[aout]" \
            -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 128k -shortest \
            "${output_file}.tmp" 2>/dev/null && mv "${output_file}.tmp" "$output_file"
    fi
    
    local dur=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$output_file" 2>/dev/null | cut -d. -f1)
    local size=$(ls -lh "$output_file" | awk '{print $5}')
    echo "     ✓ ${dur}s, ${size}"
}

# Generar TODAS las variaciones
for lang in es en; do
    echo "━━━ Idioma: $lang ━━━"
    for style in "${STYLES[@]}"; do
        generate_video "$lang" "$style"
    done
    echo ""
done

echo "✅ Todas las variaciones generadas:"
echo ""
ls -lh "$OUTPUT"/*.mp4 | awk '{print "  📹 " $9 " (" $5 ")"}'
echo ""
echo "Total: $(ls -1 "$OUTPUT"/*.mp4 | wc -l) videos"
