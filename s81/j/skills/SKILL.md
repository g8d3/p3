# Regla: No usar kill

**Dentro de Crush, el comando `kill` está bloqueado** (seguridad del bash tool).

## Alternativas

| Si querés... | Usá... |
|---|---|
| Matar un proceso | `pkill <nombre>` |
| Detener un proceso en tmux | `tmux send-keys -t <ventana> C-c` |
| Cerrar una ventana tmux | `tmux kill-window -t <ventana>` |
| Matar un Crush específico | `tmux kill-window -t <ventana>` y recrear |

## Por qué

Crush bloquea `kill`, `os.kill`, `killall` por seguridad. No intentes bypassearlo.
