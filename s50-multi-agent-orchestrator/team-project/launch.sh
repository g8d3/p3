#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIDS_DIR="$PROJECT_DIR/.pids"
LOGS_DIR="$PROJECT_DIR/.logs"
TIMELINE="$PROJECT_DIR/.timeline"
mkdir -p "$PIDS_DIR" "$LOGS_DIR"

# Colores para el timeline
declare -A COLORS=(
    [html]="🟧"
    [css]="🟦"
    [js]="🟨"
    [tests]="🟪"
    [docs]="🟩"
)

# Agentes: nombre → subdirectorio → tarea
declare -A AGENTS=(
    [html]="html|Create index.html with semantic HTML5: header, nav, main, footer, todo list container, add form, ARIA labels."
    [css]="css|Create style.css with modern dark theme, hover effects, transitions, responsive design, CSS variables."
    [js]="js|Create app.js: add/complete/delete todos, filter all/active/completed, localStorage persistence, vanilla JS."
    [tests]="tests|Create test.html with unit tests for add/toggle/delete/filter/localStorage. Simple test runner."
    [docs]="docs|Create README.md (overview, how to run, structure, features) and CHANGELOG.md."
)

log_timeline() {
    local agent="$1"
    local status="$2"
    local msg="$3"
    local ts
    ts=$(date +%s%N | cut -c1-13)  # milliseconds
    local time_str
    time_str=$(date +%H:%M:%S)
    echo "${ts}|${time_str}|${agent}|${status}|${msg}" >> "$TIMELINE"
}

start_agents() {
    # Limpiar timeline anterior
    > "$TIMELINE"
    echo "🚀 Lanzando 5 agentes..."
    echo ""

    for name in "${!AGENTS[@]}"; do
        IFS='|' read -r subdir task <<< "${AGENTS[$name]}"
        local work_dir="$PROJECT_DIR/$subdir"
        local pid_file="$PIDS_DIR/${name}.pid"

        # Saltar si ya está corriendo
        if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            echo "  ⏭️  $name ya está corriendo"
            continue
        fi

        log_timeline "$name" "START" "Agente iniciado"

        echo "  ${COLORS[$name]} Lanzando $name → $subdir/"

        # Lanzar pi en background con logging
        (
            cd "$work_dir"
            log_timeline "$name" "WORKING" "Generando código..."
            
            # Capturar output y loggear
            OUTPUT=$(pi -p "$task" --no-session 2>&1)
            EXIT_CODE=$?
            
            if [[ $EXIT_CODE -eq 0 ]]; then
                log_timeline "$name" "DONE" "Completado ✓"
            else
                log_timeline "$name" "ERROR" "Falló (exit code $EXIT_CODE)"
            fi
            
            rm -f "$pid_file"
        ) &

        echo $! > "$pid_file"
    done

    echo ""
    echo "📊 Monitorear en tiempo real:"
    echo "   ./timeline.sh          # Timeline en vivo"
    echo "   ./launch.sh status     # Estado actual"
    echo "   ./launch.sh stop       # Detener todos"
}

stop_agents() {
    echo "🛑 Deteniendo todos los agentes..."
    for pid_file in "$PIDS_DIR"/*.pid; do
        [[ -f "$pid_file" ]] || continue
        local name
        name=$(basename "$pid_file" .pid)
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            log_timeline "$name" "STOPPED" "Detenido por usuario"
        fi
        rm -f "$pid_file"
    done
}

stop_one() {
    local name="$1"
    local pid_file="$PIDS_DIR/${name}.pid"
    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            log_timeline "$name" "STOPPED" "Detenido por usuario"
            echo "🛑 $name detenido"
        fi
        rm -f "$pid_file"
    else
        echo "❌ $name no está corriendo"
    fi
}

show_status() {
    echo "📊 Estado de los agentes:"
    echo "────────────────────────────────────────"
    for name in html css js tests docs; do
        local pid_file="$PIDS_DIR/${name}.pid"
        if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            echo "  ${COLORS[$name]} $name  │ 🟢 corriendo (pid $(cat "$pid_file"))"
        elif grep -q "${name}|DONE" "$TIMELINE" 2>/dev/null; then
            echo "  ${COLORS[$name]} $name  │ ✅ completado"
        elif grep -q "${name}|ERROR" "$TIMELINE" 2>/dev/null; then
            echo "  ${COLORS[$name]} $name  │ ❌ error"
        else
            echo "  ${COLORS[$name]} $name  │ ⚪ inactivo"
        fi
    done
    echo "────────────────────────────────────────"
}

case "${1:-help}" in
    start)    start_agents ;;
    stop)     stop_agents ;;
    stop-one) stop_one "${2:-}" ;;
    status)   show_status ;;
    *)
        echo "Uso: $0 {start|stop|stop-one <name>|status}"
        echo ""
        echo "Agentes: html, css, js, tests, docs"
        ;;
esac
