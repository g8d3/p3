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

## 7. Continuidad de sesión
- Se implementó switch con `--session $ID --cwd $dir`
- La sesión continúa exactamente donde se quedó, pero en la nueva carpeta
- Se necesita `source ~/.zshrc` una vez para activar el hook
- Compatible con tmux (PGID kill no afecta tmux)
