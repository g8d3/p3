# Handoff de s80 → s81

## Contexto

Este archivo fue creado por Crush en s80 al hacer switch a s81.
Contiene el contexto de la conversación para que el nuevo agente lo lea y continúe.

## Lo que se construyó

Se creó un sistema `p3` para gestionar proyectos en `/home/vuos/code/p3/`:

### Componentes
- **`~/bin/p3`** — script bash para listar/crear/ir a proyectos s{N}
- **`~/bin/p3-switch`** — cambia de proyecto (crea carpeta + señal /tmp/p3-next + mata Crush)
- **`~/.zshrc`** — función `p3()` y hook `p3-resume` (precmd) para auto-resume
- **`/tmp/p3-next`** — archivo señal: línea 1 = directorio, línea 2 = session-id opcional

### Estado actual
- `source ~/.zshrc` NO se ha ejecutado (el hook no está activo)
- El bash tool de Crush bloquea `kill`, `os.kill` (seguridad)
- `tmux new-window` y `kill-window` SÍ funcionan
- `session continue` con `--session` no funciona si la sesión está activa en otra ventana
- La sesión original `b33dd271a9a26893` sigue activa en s80

### Temas pendientes (PENDIENTE.md)
1. Portabilidad / auto-contenido del script
2. Nombre del proyecto (p3 colisiona con el directorio)
3. Arquitectura agnóstica (que funcione con cualquier AI terminal)
4. Si lo usarían humanos o agentes
5. Keywords / marketing
6. Ideas adicionales (templates, init, etc.)
7. Comparativa de AI terminals (Crush, opencode, hermes, pi, claude code, gemini cli, antigravity, copilot)

### Cómo probar el switch manualmente (para depuración)
1. `source ~/.zshrc` — activa hook + función p3
2. `printf '%s\n%s\n' "/home/vuos/code/p3/s81" "$SESSION_ID" > /tmp/p3-next`
3. `exit` (sale de Crush, el hook auto-arranca en s81)
