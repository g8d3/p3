# Handoff s81 → s82

## Contexto de la conversación en s81

En s81 continuamos la discusión de PENDIENTE.md desde s80. Temas clave:

### Visión general (el "verdadero producto")
- El sistema `p3` empezó como un "cambiar de carpeta", pero evolucionó a **pasamanos de contexto entre sesiones de AI**.
- La meta es **orquestación autónoma de agentes**: que un agente pase el testigo a otro con memoria de lo que se hizo, decisiones, estado actual.
- El usuario usa **Android + Termux + SSH + tmux + dictado** de Google — todo script debe funcionar con teclado mínimo, latencia alta, sin flags memorables.

### Contexto del usuario (historial)
El usuario tiene un ecosistema enorme ya construido:
- **`/home/vuos/code/.agents/skills/orquestar-agentes/SKILL.md`** — sistema de orquestación multi-agente con tmux, bus de mensajes (inotify), supervisor, ciclador autónomo.
- **`/home/vuos/code/.agents/roadmap/aan-prototype-plan.md`** — plan para Autonomous Agent Network.
- **Decenas de proyectos en `/home/vuos/code/p3/`** — desde trading bots hasta video pipelines (ver `/home/vuos/code/p3/FOLDER_INDEX.md`).
- El usuario ya construyó **s50-multi-agent-orchestrator**, **s51-multi-agent-video-pipeline**, **s63-agent-hub**.
- También hay un **`/home/vuos/code/spacebot/AGENTS.md`** con arquitectura multi-proceso (Channel, Branch, Worker, Compactor, Cortex).

### Lo que se construyó en s80-s81
- **`~/bin/p3`** — script bash para listar/crear/ir a proyectos s{N}
- **`~/bin/p3-switch`** — cambia de proyecto (crea carpeta + escribe `/tmp/p3-next` + mata Crush)
- Hook zsh precmd para auto-resume
- `/tmp/p3-next` — archivo señal: línea 1 = directorio, línea 2 = session-id

### Problemas actuales
1. `kill` está bloqueado en Crush bash tool. **Solución**: usar `tmux kill-window` como driver.
2. Hay 2 ventanas tmux: **0** (node-) y **3** (proy-s81*, donde estamos). El usuario prefiere estar en ventana 0.
3. El `source ~/.zshrc` no se ha corrido aún (hook precmd no activo).
4. La sesión original `b33dd271a9a26893` de s80 sigue activa.

### Opiniones de Crush sobre temas pendientes
Discutimos los 7 puntos de PENDIENTE.md. Decisiones clave:

1. **Portabilidad**: usar tmux como driver principal (cross-platform macOS/Linux/WSL), evitar kill/ps.
2. **Nombre**: propuesta **`j`** (jump) — una letra, fácil de tipear en mobile.
3. **Arquitectura agnóstica**: 3 capas (Core, Driver, Shell hook). El driver se selecciona por detección del AI.
4. **Humanos vs agentes**: optimizar para agente→agente, humano es bonus.
5. **Marketing**: "Agent workspace switcher for AI terminals".
6. **Ideas extra**: `j init`, `j log` (context.md), `j list`.
7. **Comparativa AI terminals**: Crush tiene `--session + --cwd`, las otras no — pero tmux kill-window funciona para todas.

### Lo que Crush se queda haciendo en s81
Va a construir el **script `j` unificado** que:
- Sea un solo script en `~/bin/j`
- Use tmux como driver default (funciona en mobile)
- Use la ventana 0
- Cree `context.md` en cada proyecto
- Detecte el AI y use driver correcto
- Sea agnóstico y portable

---

## Para el agente en s82

El usuario quiere discutir **otros detalles** — posiblemente sobre:
- Multi-agent orchestration
- AAN (Autonomous Agent Network)
- Otros temas de su roadmap

Tiene todo el ecosistema en `/home/vuos/code/.agents/` y `p3/FOLDER_INDEX.md`.

**Estilo de interacción**: usuario usa dictado por voz desde Termux en Android. Respuestas concisas, acción directa. No le gustan los preámbulos. Prefiere que el AI haga y luego él revisa.

### Sesión
- s82 no existe aún. Hay que crearla.
- Ventana actual: `main:3` (proy-s81). Crear en `main:4` o donde prefiera.
- La sesión activa de Crush en s81 es la actual — no hacer `exit` ni matar nada que afecte s81.
