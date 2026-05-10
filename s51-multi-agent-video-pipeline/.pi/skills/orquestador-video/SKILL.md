---
name: orquestador-video
description: Orquesta múltiples agentes pi para producción de video. Crea ventanas tmux con agentes especializados (Director, Remotion, AI Gen, Audio, Shorts, Editor, Quality), monitor en vivo y dashboard web. Cada agente espera con chat vacío hasta recibir instrucciones (0 tokens gastados mientras espera).
---

# 🎬 Orquestador de Video

Sistema multi-agente para producción de video. Cada agente corre en su propia ventana tmux con pi ocioso (chat vacío). Cuando un agente termina, envía un mensaje al siguiente agente via `tmux send-keys`.

## Estructura

```
proyecto/
├── agentes/           # Tareas para cada agente
│   ├── 00-director.md
│   ├── 01-remotion.md
│   ├── 02-aigen.md
│   ├── 03-audio.md
│   ├── 04-shorts.md
│   ├── 05-editor.md
│   └── 07-quality.md
├── templates/
│   ├── escenas.yaml   # Especificación de escenas (generada por Director)
│   └── efectos.md     # Biblioteca de efectos
├── grupos/            # Configuración de grupos
├── tools/
│   ├── monitor.py     # Captura tmux + reportes → live.json
│   ├── dashboard.html # Dashboard web con tablas
│   └── dashboard.sh   # Dashboard terminal (deprecated, usar web)
├── reportes/          # Reportes JSON de cada agente + live.json
└── output/
    ├── clips/
    ├── audio/
    └── renders/
```

## Setup inicial

```bash
# 1. Ir al proyecto
cd /home/vuos/code/p3/s51

# 2. Copiar agentes, templates, tools si no existen
cp -r .pi/skills/orquestador-video/agentes . 2>/dev/null
cp -r .pi/skills/orquestador-video/templates . 2>/dev/null  
cp -r .pi/skills/orquestador-video/tools . 2>/dev/null
cp -r .pi/skills/orquestador-video/grupos . 2>/dev/null
mkdir -p reportes output/{clips,audio,renders}

# 3. Instalar dependencias del monitor
pip install -q -r .pi/skills/orquestador-video/requirements.txt 2>/dev/null || true

# 4. Crear ventanas tmux (desde cualquier terminal)
bash .pi/skills/orquestador-video/tools/crear_ventanas.sh
```

## Uso

### Iniciar sesión
```bash
tmux attach -t video
```

### Navegación rápida

| Tecla | Ventana |
|-------|---------|
| `Ctrl+B 0` | Director |
| `Ctrl+B 1` | Grupo A - Remotion |
| `Ctrl+B 2` | Grupo B - AI Gen |
| `Ctrl+B 3` | Grupo C - Audio |
| `Ctrl+B 4` | Grupo D - Shorts |
| `Ctrl+B 5` | Grupo E - Editor |
| `Ctrl+B 6` | Quality |
| `Ctrl+B 7` | Monitor (live.json) |
| `Ctrl+B 8` | Web Server (puerto 8080) |
| `Ctrl+B 9` | Bash compartido |

### Flujo típico

```bash
# Ventana 0 (Director): darle el tema
# (ya está con pi, solo escribir el mensaje)
"Quiero un video de 60s sobre el Big Bang, 6 escenas, cinematic"

# Cuando el Director termina, NOTIFICAR a los grupos:
tmux send-keys -t video:1 "escenas.yaml listo. Lee agentes/01-remotion.md y ejecuta." Enter
tmux send-keys -t video:2 "escenas.yaml listo. Lee agentes/02-aigen.md y ejecuta." Enter
tmux send-keys -t video:3 "escenas.yaml listo. Lee agentes/03-audio.md y ejecuta." Enter
tmux send-keys -t video:4 "escenas.yaml listo. Lee agentes/04-shorts.md y ejecuta." Enter

# Cuando los grupos terminen renders, NOTIFICAR a Quality:
tmux send-keys -t video:6 "Hay renders listos. Lee agentes/07-quality.md y evalúa." Enter

# Si Quality rechaza, Director itera y re-notifica
```

### Dashboard Web
```
http://localhost:8080/tools/dashboard.html
```
Muestra dos tablas actualizadas cada 2s:
- **Estado de Agentes**: nombre, resumen, última tarea
- **Tareas Recientes**: tarea, agente, tipo

### Monitoreo
El monitor (`tools/monitor.py`) corre en la ventana 7 y captura:
- Output de todos los paneles tmux cada 2s
- Reportes JSON de cada agente
- Escribe `reportes/live.json` para el dashboard

## Principio clave

Los agentes que esperan a otros **NO deben hacer while loops ni tool calls**. Deben estar con **pi abierto y chat vacío**. Cuando el agente anterior termina, envía un mensaje via `tmux send-keys`. Así se gastan **0 tokens** mientras esperan.

## Notas
- El web server corre con `python3 -m http.server 8080`
- Los reportes JSON los escribe cada agente al trabajar
- El monitor actualiza `live.json` cada 2 segundos
- Los dashboards (terminal y web) son intercambiables

## Archivos de referencia
- `agentes/*.md` — Tareas detalladas para cada agente
- `templates/efectos.md` — Biblioteca de movimientos de cámara, transiciones, iluminación
- `templates/escenas.yaml` — Especificación de escenas (ejemplo)
- `grupos/*.md` — Configuración de qué agentes forman cada grupo
