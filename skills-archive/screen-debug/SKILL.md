---
name: screen-debug
description: >
  Debug GUI applications using accessibility APIs + vision models.
  First tries xdotool/xprop/at-spi2 for structured window/dialog info.
  Falls back to screenshot + vision model if accessibility is insufficient.
  Use when orchestrator is stuck, process hangs with no output,
  there are dialogs blocking initialization, or display state is unknown.
  Trigger patterns: crash dialog, window not found, process alive but stuck,
  unknown display state, GUI app not responding as expected.
allowed-tools: Bash
---

# Screen Debug Skill — Accesibilidad + Visión

## ¿Cuándo usar esta skill?

Usa esta skill cuando el contexto indica **uno o más** de estos patrones:

| Patrón | Ejemplo |
|---|---|
| Proceso vivo pero sin progreso | OBS dice "Crash detected" y no avanza |
| Diálogos bloqueantes | Modal de recovery, popup de error, wizard |
| Display state desconocido | No sabemos qué hay en la pantalla |
| GUI no responde como espera | App arranca pero websocket no aparece |
| Debug visual necesario | "No puedo ver qué está pasando" |

## ⚠️ Regla #1: Detectar displays activos (nunca asumir que no hay)

**Error común:** Mirar la variable `$DISPLAY`, verla vacía, y concluir "no hay displays".

**La forma correcta** es escanear:

```bash
# 0.0 — Escanear todos los displays disponibles en el sistema
scan_displays() {
    local displays=()
    
    # Método 1: Sockets X11
    for sock in /tmp/.X11-unix/X*; do
        [ -e "$sock" ] && displays+=(":${sock##*X}")
    done
    
    # Método 2: Procesos Xorg en ejecución
    while read -r pid disp; do
        displays+=("$disp")
    done < <(ps aux | grep -oP 'Xorg.*displayfd \K\d+' | while read fd; do
        [ -e "/proc/$(ps aux | grep "Xorg.*displayfd $fd" | grep -v grep | awk '{print $2}')/fd/$fd" ] && echo ":$(cat /proc/*/fd/$fd 2>/dev/null)"
    done 2>/dev/null)
    
    # Método 3: Xvfb en ejecución
    ps aux | grep -oP 'Xvfb.*:(\d+)' | grep -oP ':\d+' 2>/dev/null
    
    # Método 4: logind sessions activas
    loginctl seat-status seat0 2>/dev/null | grep -oP 'Display :\d+' | grep -oP ':\d+'
    
    # Unicidad
    printf '%s\n' "${displays[@]}" | sort -u
}

# Uso:
for disp in $(scan_displays); do
    if DISPLAY="$disp" xdotool getmouselocation &>/dev/null; then
        echo "✅ Display $disp responde"
        # trabajar con este display
    fi
done
```

## Pipeline de diagnóstico

### Fase 1 — Detectar displays

Siempre empezar escaneando displays como arriba. No confiar en `$DISPLAY`.

### Fase 2 — Accesibilidad (xdotool)

Para CADA display detectado:

```bash
# 2.1 Listar ventanas
WINDOWS=$(DISPLAY=$disp xdotool search . 2>/dev/null)
for id in $WINDOWS; do
    name=$(DISPLAY=$disp xdotool getwindowname "$id" 2>/dev/null)
    geo=$(DISPLAY=$disp xdotool getwindowgeometry "$id" 2>/dev/null | paste -sd ' ')
    echo "[$id] $name | $geo"
done
```

```bash
# 2.2 Propiedades de ventana sospechosa
xprop -id $WINDOW_ID WM_CLASS WM_NAME _NET_WM_WINDOW_TYPE 2>/dev/null
```

```bash
# 2.3 Jerarquía de widgets (at-spi2, si está disponible)
gdbus introspect --session --dest org.a11y.atspi --object-path /org/a11y/atspi/accessible/root 2>/dev/null
```

### Fase 3 — Captura + Visión (fallback si Fase 2 es insuficiente)

**⚠️ Regla: No redimensionar ni comprimir la imagen.**
Benchmark real (ver `s59-model-analysis/`) demostró que el tamaño de imagen **no afecta el tiempo de respuesta** — el modelo internamente redimensiona a resolución fija. Redimensionar solo añade latencia de preprocesamiento.

```bash
# 3.1 Capturar screenshot DIRECTA del display (sin redimensionar)
import -display "$disp" -window root /tmp/screen-debug-shot.png
```

Luego usar el **modelo vision más rápido**. Benchmark (2026-05-14, MiMo-V2.5):

| Modelo | Tiempo promedio | Prioridad |
|---|---|---|
| **MiMo-V2.5** | **~10s** 🥇 | Usar SIEMPRE primero |
| Qwen3.6 Plus | ~25s | Usar si MiMo falla o da resultado ambiguo |
| Qwen3.5 Plus | ~28s | Alternativa |
| Kimi K2.5 | ~31s | Alternativa |
| Kimi K2.6 | ~41s | Usar SOLO si se necesita mucho detalle |

```bash
# 3.2 Analizar con MiMo-V2.5 (más rápido: ~10s)
opencode run 'Describe what is on this screen in detail.
- What windows/dialogs are visible?
- What text/buttons do they contain?
- Is there any dialog blocking the application?
- What is the overall state?' --model opencode-go/mimo-v2.5 --file /tmp/screen-debug-shot.png

# 3.3 Si MiMo dió resultado ambiguo, retry con Qwen3.6 Plus (~25s)
opencode run 'Describe what is on this screen in detail.
Is there any blocking dialog?' --model opencode-go/qwen3.6-plus --file /tmp/screen-debug-shot.png

# 3.4 Solo si se necesita análisis forense detallado, Kimi K2.6 (~41s)
opencode run 'Describe this screen exhaustively: every visible element,
every text label, every button.' --model opencode-go/kimi-k2.6 --file /tmp/screen-debug-shot.png
```

### Fase 4 — Acción correctiva

Basado en el diagnóstico combinado (accesibilidad + visión):

```bash
# Cerrar diálogo en el display correcto
DISPLAY=$disp xdotool windowactivate $WID key --clearmodifiers Return
DISPLAY=$disp xdotool windowactivate $WID key --clearmodifiers alt+n
DISPLAY=$disp xdotool windowkill $WID
DISPLAY=$disp import -window root /tmp/screen-debug-after.png
```

## Estrategia de selección de modelo vision (basada en benchmark)

1. **MiMo-V2.5** 🥇 — **default.** Más rápido (~10s), suficiente para diagnóstico de UI
2. **Qwen3.6 Plus** 🥈 — retry si MiMo da resultado ambiguo (~25s, mejor con textos)
3. **Kimi K2.6** 🥉 — solo para análisis forense detallado (~41s)

Benchmark completo en `s59-model-analysis/opencode-go-modelos-vision.md`.

## Notas

- **NUNCA** asumir que no hay displays porque `$DISPLAY` está vacío.
  Escanear `/tmp/.X11-unix/`, procesos Xorg, Xvfb, y logind.
- **NUNCA** redimensionar ni comprimir la screenshot antes de enviarla al modelo.
  No mejora velocidad y puede empeorar la calidad de descripción.
- Si no hay ningún display, entonces sí se puede iniciar Xvfb como fallback.
- La accesibilidad (at-spi2) no siempre está instalada.
- xdotool es la herramienta más confiable para interactuar con ventanas.
