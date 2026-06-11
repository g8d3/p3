---
name: cdp
description: "Control total del browser con agent-browser (CLI) + Chrome CDP. Usa agent-browser para navegar, click, fill, snapshot con refs. Usa cdp.sh para lanzar Chrome con tu perfil y remote debugging. Trigger: browser, chrome, navegar, click, scrape, agente browser."
---

# Browser automation

## agent-browser (manipulación principal)

CLI Rust nativa. Output con refs (@e1). Mínimo tokens.

```bash
# 1. ABRIR
agent-browser open <url>

# 2. VER ELEMENTOS (saca refs @e1, @e2...)
agent-browser snapshot -i

# 3. INTERACTUAR CON REFS
agent-browser click @e1
agent-browser fill @e2 "texto"
agent-browser select @e3 "opcion"
agent-browser scroll down

# 4. EXTRAER INFO
agent-browser get text @e1      # texto de un elemento
agent-browser get title         # título de la página
agent-browser get url           # URL actual
agent-browser snapshot          # árbol de accesibilidad completo
agent-browser screenshot        # captura visual (agrega --full para full page)
agent-browser pdf page.pdf      # PDF

# 5. DEBUG (CONSOLA Y ERRORES)
agent-browser console            # Ver logs de consola
agent-browser console --clear    # Limpiar console
agent-browser errors             # Ver errores de página (con stack traces)
agent-browser errors --bail      # Parar en el primer error

# 6. CERRAR
agent-browser close
```

Flujo: `open` → `snapshot -i` → click/fill → `snapshot -i` (repetir) → `close`

**Integración con tu Chrome**: lanza `cdp.sh` primero, luego usa `--cdp 9222`:
```bash
~/.agents/skills/cdp/cdp.sh
agent-browser --cdp 9222 snapshot -i
```

## cdp.sh (lanzar Chrome con tu perfil)

Script auto-contenido. Carga config desde `~/.config/cdp-skill/config.sh`.

```bash
# Lanzar Chrome con tu perfil
~/.agents/skills/cdp/cdp.sh

# Override rápido
CDP_PORT=9333 CDP_MODE=headless ~/.agents/skills/cdp/cdp.sh

# Verificar CDP
curl -s http://localhost:${CDP_PORT:-9222}/json/version | jq '{Browser, webSocketDebuggerUrl}'
```

### Env vars (defaults genéricos)

| Var | Default | Descripción |
|-----|---------|-------------|
| `CDP_PORT` | `9222` | Puerto debugging |
| `CDP_DIR` | `~/.local/share/cdp-profile` | Directorio perfil Chrome |
| `CDP_PROFILE` | `""` | Nombre del perfil (opcional) |
| `CDP_MODE` | `auto` | `headed`, `headless`, o `auto` |

### Config personal (`~/.config/cdp-skill/config.sh`)

```bash
: "${CDP_DIR:=$HOME/apps/test-dec-2025}"
: "${CDP_PROFILE:=Profile 1}"
: "${CDP_MODE:=headed}"
```
