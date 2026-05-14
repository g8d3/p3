#!/usr/bin/env bash
# reindex.sh — Hybrid reindex: bash pre-scan + AI descriptions
# Usage: ./reindex.sh [--dry-run]
# Config: REINDEX_AGENT=pi|opencode|hermes (default: pi)
set -euo pipefail

cd "$(dirname "$0")"
DRY_RUN="${1:-}"
INDEX="FOLDER_INDEX.md"
TASK_FILE="/tmp/reindex-prompt-$$.md"

cleanup() { rm -f "$TASK_FILE"; }
trap cleanup EXIT

echo "🔍 Escaneando directorios nuevos..."

# ── 1. Encontrar directorios s* no indexados ──
declare -a NEW_DIRS=()
for dir in s*; do
    [ -d "$dir" ] || continue
    # Normal: el directorio aparece exactamente en el índice?
    if grep -q "| \`$dir\`" "$INDEX" 2>/dev/null; then
        continue
    fi
    
    # Caso especial: el índice tiene sXX-scratch pero el dir real es otro
    # Ej: índice tiene "s49-scratch" pero existe "s49-ai-companies-finance"
    base="${dir%%-*}"  # sXX
    # Si el índice tiene un sXX-scratch que corresponde a este base, lo marcamos como desactualizado
    scratch_entry=""
    if grep -q "| \`${base}-scratch\`" "$INDEX" 2>/dev/null; then
        scratch_entry="${base}-scratch"
        echo "   ⚠️  '$dir' reemplazará la entrada obsoleta '$scratch_entry' en el índice"
    fi
    
    NEW_DIRS+=("$dir|$scratch_entry")
done

if [ ${#NEW_DIRS[@]} -eq 0 ]; then
    echo "✅ No hay directorios nuevos. Todo al día."
    exit 0
fi

# ── 2. Separar vacíos de no vacíos ──
declare -a EMPTY=()
declare -a NONEMPTY=()
for entry in "${NEW_DIRS[@]}"; do
    dir="${entry%%|*}"
    if [ -z "$(ls -A "$dir" 2>/dev/null)" ]; then
        EMPTY+=("$dir")
    else
        NONEMPTY+=("$entry")
    fi
done

if [ ${#EMPTY[@]} -gt 0 ]; then
    echo "⏭️  Ignorando directorios vacíos: ${EMPTY[*]}"
fi

if [ ${#NONEMPTY[@]} -eq 0 ]; then
    echo "✅ Solo había directorios vacíos. Nada que indexar."
    exit 0
fi

# ── 3. Recolectar info de cada proyecto ──
echo "📋 Recolectando información de proyectos..."
declare -a DIR_LIST=()
INFO=""
for entry in "${NONEMPTY[@]}"; do
    dir="${entry%%|*}"
    DIR_LIST+=("$dir")
    
    INFO+=$'\n## '"$dir"$'\n'
    
    # File tree (excluyendo build artifacts y cachés)
    INFO+="File tree:"$'\n'
    INFO+='```'$'\n'
    INFO+="$(find "$dir" -type f \
        -not -path '*/.git/*' \
        -not -path '*/node_modules/*' \
        -not -path '*/__pycache__/*' \
        -not -path '*/.venv/*' \
        -not -path '*/venv/*' \
        -not -path '*/build/*' \
        -not -path '*/target/*' \
        -not -path '*/dist/*' \
        -not -path '*/.next/*' \
        2>/dev/null | sort | awk 'NR<=20' 2>/dev/null || true)"$'\n'
    INFO+='```'$'\n'
    
    # README snippet
    if [ -f "$dir/README.md" ]; then
        INFO+="README.md header:"$'\n'
        INFO+='```'$'\n'
        INFO+="$(head -5 "$dir/README.md" 2>/dev/null)"$'\n'
        INFO+='```'$'\n'
    fi
    
    # package.json description
    if [ -f "$dir/package.json" ]; then
        DESC=$(python3 -c "
import json
try:
    p = json.load(open('$dir/package.json'))
    d = p.get('description', '')
    s = p.get('scripts', {})
    deps = list(p.get('dependencies', {}).keys())[:5]
    print(f'Description: {d}' if d else 'No description')
    if deps: print(f'Key deps: {\", \".join(deps)}')
    if s: print(f'Scripts: {\", \".join(list(s.keys())[:5])}')
except: print('(could not parse)')" 2>/dev/null || echo "(error reading package.json)")
        INFO+="$DESC"$'\n'
    fi
    
    # pyproject.toml
    if [ -f "$dir/pyproject.toml" ]; then
        DESC=$(grep -m1 'description' "$dir/pyproject.toml" 2>/dev/null || echo "")
        INFO+="pyproject.toml: ${DESC:-'(no description field)'}"$'\n'
    fi
    
    # Extensiones de archivos dominantes (para dar pistas)
    EXTS=$(find "$dir" -type f \
        -not -path '*/.git/*' \
        -not -path '*/node_modules/*' \
        -not -path '*/__pycache__/*' \
        -not -path '*/.venv/*' \
        2>/dev/null | sed 's/.*\.//' | sort | uniq -c | sort -rn | awk 'NR<=5 {print $2}')
    if [ -n "$EXTS" ]; then
        INFO+="File types: $(echo $EXTS)"$'\n'
    fi
    INFO+=$'\n'
done

# ── 4. Construir el prompt para el AI ──
cat > "$TASK_FILE" << PROMPTEOF
# Reindex Task

I need descriptions for new project directories under /home/vuos/code/p3.
Below is the file tree and metadata for each new directory.

## Rules
- Suggest a kebab-case name suffix for each directory (e.g., "my-project" from sXX → sXX-my-project)
- Write a one-line description (max 200 chars) in plain English explaining what the project does
- Format each response line exactly like: \`sXX-name-suffix | One-line description.\`
- **CRITICAL: Output ONLY the lines below. No greetings, no explanations, no markdown code blocks.**
- Preserve the order of directories as listed below

## Directories to describe
$(echo "$INFO")

## Output format (ONLY this, absolutely no other text):
\`sXX-name-suffix | Description.\`
\`sXX-name-suffix | Description.\`
PROMPTEOF

echo ""
echo "🤖 Invocando AI agent para generar descripciones..."

# ── 5. Llamar al AI agent ──
AGENT="${REINDEX_AGENT:-pi}"
DESCRIPTIONS=""

case "$AGENT" in
    pi)
        echo "   Usando: pi (modo print, timeout 120s)"
        timeout 120 pi -p "@$TASK_FILE" > "$TASK_FILE.out" 2>/dev/null || true
        DESCRIPTIONS=$(cat "$TASK_FILE.out" 2>/dev/null || true)
        rm -f "$TASK_FILE.out"
        ;;
    opencode)
        echo "   Usando: opencode (timeout 120s)"
        timeout 120 opencode run "@$TASK_FILE" --model openrouter/anthropic/claude-sonnet-4 > "$TASK_FILE.out" 2>/dev/null || true
        DESCRIPTIONS=$(cat "$TASK_FILE.out" 2>/dev/null || true)
        rm -f "$TASK_FILE.out"
        ;;
    hermes)
        echo "   Usando: hermes (timeout 120s)"
        timeout 120 hermes run "@$TASK_FILE" > "$TASK_FILE.out" 2>/dev/null || true
        DESCRIPTIONS=$(cat "$TASK_FILE.out" 2>/dev/null || true)
        rm -f "$TASK_FILE.out"
        ;;
    *)
        echo "❌ Agente desconocido: $AGENT"
        echo "   Usa REINDEX_AGENT=pi|opencode|hermes"
        exit 1
        ;;
esac

if [ -z "$DESCRIPTIONS" ]; then
    echo ""
    echo "❌ El AI agent no produjo output."
    echo "   Posibles causas:"
    echo "   - REINDEX_AGENT=$AGENT no está instalado o configurado"
    echo "   - El modelo no está disponible (revisa API keys)"
    echo ""
    echo "   Prueba: REINDEX_AGENT=opencode ./reindex.sh"
    echo "   O:     pi -p \"@$TASK_FILE\""
    exit 1
fi

echo ""
echo "✅ Respuesta del AI (raw):"
echo "────────────────────"
echo "$DESCRIPTIONS" | head -30
echo "────────────────────"

# ── 6. Aplicar cambios ──
echo ""
echo "📝 Aplicando cambios..."

# Filtrar solo líneas con el formato esperado: sXX-name | description
# Esto elimina intro del AI, bloques markdown, etc.
CLEAN=$(echo "$DESCRIPTIONS" | grep -oE 's[0-9]+-[a-zA-Z0-9_-]+ *\| *[^|]+' || true)

if [ -z "$CLEAN" ]; then
    echo "⚠️  No se pudieron extraer descripciones del output del AI."
    echo "   Output recibido:"
    echo "$DESCRIPTIONS"
    exit 1
fi

while IFS='|' read -r folder desc; do
    folder=$(echo "$folder" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr -d '`')
    desc=$(echo "$desc" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [ -z "$folder" ] && continue
    
    base="${folder%%-*}"  # sXX
    
    # Encontrar el directorio real en DIR_LIST
    real_dir=""
    for d in "${DIR_LIST[@]}"; do
        if [[ "$d" == "$base"* ]]; then
            real_dir="$d"
            break
        fi
    done
    
    if [ -z "$real_dir" ]; then
        echo "   ⚠️  No se encontró directorio para $folder, saltando"
        continue
    fi
    
    # Renombrar si el nombre sugerido es diferente
    if [ "$real_dir" != "$folder" ]; then
        if [ -d "$folder" ]; then
            echo "   ⚠️  Ya existe $folder (no se renombra)"
        else
            echo "   📁 Renombrando: $real_dir → $folder"
            if [ "$DRY_RUN" != "--dry-run" ]; then
                mv "$real_dir" "$folder"
            else
                echo "      (dry-run)"
            fi
        fi
    fi
    
    # Eliminar entrada obsoleta sXX-scratch si existe
    scratch_entry="${base}-scratch"
    if grep -q "| \`$scratch_entry\`" "$INDEX" 2>/dev/null; then
        echo "   🗑️  Eliminando entrada obsoleta: $scratch_entry"
        if [ "$DRY_RUN" != "--dry-run" ]; then
            sed -i "/| \`$scratch_entry\`/d" "$INDEX"
        else
            echo "      (dry-run) sed -i '/| \`$scratch_entry\`/d' $INDEX"
        fi
    fi
    
    # Agregar al índice
    if ! grep -q "| \`$folder\`" "$INDEX" 2>/dev/null; then
        echo "   📄 Agregando: | \`$folder\` | $desc |"
        if [ "$DRY_RUN" != "--dry-run" ]; then
            echo "| \`$folder\` | $desc |" >> "$INDEX"
        fi
    else
        echo "   ℹ️  Ya existe entrada para $folder (actualizando descripción)"
        if [ "$DRY_RUN" != "--dry-run" ]; then
            sed -i "s/| \`$folder\` |.*$/| \`$folder\` | $desc |/" "$INDEX"
        fi
    fi
done <<< "$CLEAN"

# Reordenar el índice por número de folder
if [ "$DRY_RUN" != "--dry-run" ]; then
    echo "   🔄 Reordenando índice numéricamente..."
    HEADER=$(head -3 "$INDEX")
    ROWS=$(tail -n +4 "$INDEX")
    echo "$HEADER" > "$INDEX"
    echo "" >> "$INDEX"
    echo "$ROWS" | sort -t'-' -k1.2n >> "$INDEX"
fi

echo ""
echo "✅ Reindex completado."
echo "   Directorios vacíos ignorados: ${#EMPTY[@]}"
echo "   Directorios procesados: ${#NONEMPTY[@]}"
echo ""
echo "📎 Revisa: $INDEX"
