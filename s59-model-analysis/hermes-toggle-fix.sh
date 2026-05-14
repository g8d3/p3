#!/bin/bash
# hermes-toggle-fix.sh - Cambia entre Hermes ORIGINAL y Hermes FIX (Termux)
#
# Uso:
#   ./hermes-toggle-fix.sh         # Muestra estado actual
#   ./hermes-toggle-fix.sh on      # Activa el fix
#   ./hermes-toggle-fix.sh off     # Desactiva el fix (vuelve al original)
#
# Estado se guarda en ~/.hermes/hermes-tui-fix-status

set -e

TUI_DIR="$HOME/.hermes/hermes-agent/ui-tui"
STATUS_FILE="$HOME/.hermes/hermes-tui-fix-status"
INK_SRC="$TUI_DIR/packages/hermes-ink/src/ink/log-update.ts"
INK_DIST="$TUI_DIR/packages/hermes-ink/dist/entry-exports.js"

# Backup del bundle original (solo la primera vez)
if [ ! -f "$INK_DIST.original" ]; then
    echo "📦 Creando backup del bundle original..."
    cd "$TUI_DIR"
    git stash push -m "hermes-termux-backup" -- "$INK_SRC" 2>/dev/null || true
    npm run build --prefix packages/hermes-ink --silent 2>/dev/null
    cp "$INK_DIST" "$INK_DIST.original"
    echo "   ✓ Backup guardado en $INK_DIST.original"
    git stash pop 2>/dev/null || true
    npm run build --prefix packages/hermes-ink --silent 2>/dev/null
fi

case "${1:-status}" in
    on|1|yes)
        echo "🔧 Activando fix Termux..."
        cd "$TUI_DIR"
        git stash show -p > /dev/null 2>&1 && git stash pop 2>/dev/null || true
        npm run build --prefix packages/hermes-ink --silent 2>/dev/null
        echo "✅ FIX ACTIVADO - Hermes TUI ya no saltará en Termux"
        echo "fixed" > "$STATUS_FILE"
        ;;
    off|0|no)
        echo "🔙 Restaurando Hermes ORIGINAL..."
        cp "$INK_DIST.original" "$INK_DIST"
        echo "✅ ORIGINAL RESTAURADO - Hermes TUI con comportamiento original"
        echo "original" > "$STATUS_FILE"
        ;;
    status)
        if [ -f "$STATUS_FILE" ]; then
            echo "📊 Estado actual: $(cat "$STATUS_FILE")"
        else
            echo "📊 Estado actual: fixed (por defecto)"
        fi
        echo ""
        echo "Para cambiar:"
        echo "  ./hermes-toggle-fix.sh on   → Activar fix (no salta)"
        echo "  ./hermes-toggle-fix.sh off  → Original (puede saltar)"
        ;;
    *)
        echo "Uso: $0 {on|off|status}"
        exit 1
        ;;
esac
