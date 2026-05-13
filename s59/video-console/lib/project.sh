#!/bin/bash
# ==============================================================================
# lib/project.sh — Gestión de proyectos de video
# ==============================================================================

PROJECT_FILE="project.json"

# Inicializar proyecto
project_init() {
    local name="${1:-intro}"
    local duration="${2:-5}"
    cat > "$PROJECT_FILE" <<EOF
{
  "name": "$name",
  "duration": $duration,
  "fps": 30,
  "width": 1920,
  "height": 1080,
  "scenes": [],
  "audio": {
    "tts": null,
    "music": null,
    "sfx": []
  },
  "created": "$(date -Iseconds)"
}
EOF
    echo "Project '$name' initialized"
}

# Añadir escena
project_add_scene() {
    local type="${1:?Scene type required}"
    local start="${2:?Start time required}"
    local duration="${3:?Duration required}"
    shift 3
    local params="$*"

    python3 -c "
import json
with open('$PROJECT_FILE') as f:
    p = json.load(f)
p['scenes'].append({
    'type': '$type',
    'start': $start,
    'duration': $duration,
    'params': '$params'
})
with open('$PROJECT_FILE', 'w') as f:
    json.dump(p, f, indent=2)
print('Scene added: $type @ ${start}s')
" 2>/dev/null || echo "Error adding scene"
}

# Añadir segmento visual (scene background)
project_add_segment() {
    local mode="${1:?Segment mode required}"
    local start="${2:?Start time required}"
    local end="${3:?End time required}"

    python3 -c "
import json
with open('$PROJECT_FILE') as f:
    p = json.load(f)
if 'segments' not in p:
    p['segments'] = []
p['segments'].append({'mode': '$mode', 'start': $start, 'end': $end})
with open('$PROJECT_FILE', 'w') as f:
    json.dump(p, f, indent=2)
print('Segment added: $mode ${start}s-${end}s')
" 2>/dev/null
}

# Añadir SFX al proyecto
project_add_sfx() {
    local name="${1:?SFX name required}"
    local at="${2:?Timestamp required}"
    local vol="${3:-0.5}"

    python3 -c "
import json
with open('$PROJECT_FILE') as f:
    p = json.load(f)
p['audio']['sfx'].append({
    'name': '$name',
    'at': $at,
    'volume': $vol
})
with open('$PROJECT_FILE', 'w') as f:
    json.dump(p, f, indent=2)
print('SFX added: $name @ ${at}s')
" 2>/dev/null || echo "Error adding SFX"
}

# Ver proyecto
project_status() {
    if [ ! -f "$PROJECT_FILE" ]; then
        echo "No project. Run: video init <name>"
        return
    fi
    python3 -c "
import json
with open('$PROJECT_FILE') as f:
    p = json.load(f)
print(f'Project: {p[\"name\"]}')
print(f'Duration: {p[\"duration\"]}s')
print(f'Scenes: {len(p[\"scenes\"])}')
for s in p['scenes']:
    print(f'  [{s[\"start\"]}s] {s[\"type\"]}: {s[\"params\"][:60]}')
print(f'SFX: {len(p[\"audio\"][\"sfx\"])}')
for s in p['audio']['sfx']:
    print(f'  [{s[\"at\"]}s] {s[\"name\"]} (vol: {s[\"volume\"]})')
" 2>/dev/null
}
