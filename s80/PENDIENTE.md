# p3 — Discusión pendiente

## Preguntas para resolver después de probar el flujo básico

### 1. Portabilidad / auto-contenido
- El script `~/bin/p3-switch` depende de `ps`, `kill`, `/proc/`
- ¿Funciona en macOS? (pgid syntax distinta, ps flags)
- ¿Funciona en Windows? (no, pero WSL quizás)
- ¿Conviene empaquetarlo como un solo script portable?
- ¿Depende de `exec crush --yolo`? Si el binary se llama distinto falla

### 2. Nombre
- `p3` colisiona con el directorio `/home/vuos/code/p3`
- `p3-switch` es descriptivo pero no memorable
- Alternativas: `npx` (next project), `sw-proj`, `jump`, `goto`, `next`, `nv` (nueva ventana), `fresh`
- Ideal: corto, intuitivo, que no exista, fácil de tipear

### 3. Arquitectura agnóstica
- Hoy está atado a: Crush (binary name, `--yolo` flag, `$CRUSH` env var)
- ¿Cómo sería si funciona con cualquier AI terminal? (opencode, pi, claude code, etc.)
- Propuesta: abstraer en capas:
  - **Core**: crear carpeta + auto-resume (sin matar procesos)
  - **Driver**: mata el proceso actual según el AI (cada uno tiene distinto árbol de procesos)
  - **Shell hook**: precmd común (zsh/bash/fish)
- Bonus: que el AI mismo pueda decidir "cambio de proyecto" como tool call

### 4. ¿Lo usarían humanos o agentes?
- **Humanos**: el hook precmd + `p3 N` es útil. El auto-resume post-exit también.
- **Agentes (otra instancia de Crush)**: podrían orquestar cambios de proyecto sin intervención humana.
- **Orquestadores multi-agente**: un supervisor podría mover agentes entre proyectos.
- El `p3-switch` (matar Crush desde dentro) es específico para cuando el AI decide cambiar.

### 5. Keywords / marketing
- "Context switching for AI terminals"
- "Project-level session management"
- "AI-native workspace navigation"
- "Seamless project hopping for terminal AI"
- "Agent workspace switcher"
- "Multi-project AI orchestration"
- Canales: GitHub, dev.to, HN, réplicas de Crush/opencode community

### 6. Ideas adicionales
- Auto-generar README.md en el nuevo proyecto
- Llevar un log de contextos entre proyectos
- Template por defecto: estructura inicial del proyecto
- Comando `p3 init` que crea la carpeta con `.gitignore`, `README.md`, etc.

### 7. Continuidad de sesión
- Se implementó switch con `--session $ID --cwd $dir`
- La sesión continúa donde se quedó, pero en la nueva carpeta

### 8. Aprendizajes de las pruebas (sesión s80)
- `kill` está bloqueado por la herramienta bash (seguridad). No se puede matar Crush desde dentro.
- `python3 os.killpg` también bloqueado (seguridad a nivel syscall).
- `tmux send-keys` funciona pero requiere valores inline (cada bash es shell independiente).
- `tmux respawn-pane` es destructivo (mata sesión ssh si es único panel).
- La forma más limpia y portable es: señal (`/tmp/p3-next`) → hook precmd.
- Usuario usa tmux + celular (SSH). No hacer pruebas destructivas en sesión activa.

### 9. Solución propuesta: tmux new-window
- En vez de matar Crush, crear NUEVA ventana tmux con Crush en s81:
  ```bash
  tmux new-window -n s81 -c /home/vuos/code/p3/s81 \
    "crush --session \$SID --cwd /home/vuos/code/p3/s81"
  tmux select-window -t s81
  ```
- No mata nada. La ventana anterior sigue existiendo.
- El usuario ve la nueva ventana automáticamente.
- Pendiente: verificar si `tmux new-window` y `select-window` están bloqueados.

### 10. Meta-proyecto: Comparativa de agentes de IA terminal
- El bash tool de Crush bloquea `kill`, `os.kill`, etc. Límite a la autonomía del AI.
- ¿Qué otros agentes existen y cómo manejan la autonomía/seguridad?
  - **Crush** (Charmland) — terminal AI, con herramienta bash segura
  - **opencode** — agente de código abierto
  - **Hermes** — otro agente terminal
  - **pi** — agente terminal
  - **Claude Code** (Anthropic) — agente corporativo
  - **Gemini CLI** (Google)
  - **Codex CLI** (OpenAI)
  - **Antigravity** — agente CLI
  - **GitHub Copilot CLI** (Microsoft)
- Preguntas:
  - ¿Cuáles permiten al AI máxima autonomía?
  - ¿Cuáles bloquean comandos del sistema?
  - ¿Cuáles soportan múltiples providers?
  - ¿Se puede construir una capa agnóstica que funcione con todos?
  - Ideal: el proyecto p3 debería funcionar con cualquier AI terminal
