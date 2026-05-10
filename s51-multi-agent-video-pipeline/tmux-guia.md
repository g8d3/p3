# 🪟 Cómo crear las ventanas de tmux para los agentes
## (Todo desde UNA SOLA línea, sin reusar ventanas)

### Opción 1: Script completo (recomendado)
Copia y pega esto en UNA terminal:

```bash
# Mata sesión anterior si existe
tmux kill-session -t video 2>/dev/null

# Crea sesión con la primera ventana (Directorio del proyecto)
cd /home/vuos/code/p3/s51
tmux new-session -s video -d -c /home/vuos/code/p3/s51
tmux rename-window -t video:0 'Director'

# Crea el resto de ventanas nuevas
tmux new-window -t video -c /home/vuos/code/p3/s51 -n 'GrupoA-Remotion'
tmux new-window -t video -c /home/vuos/code/p3/s51 -n 'GrupoB-AI'
tmux new-window -t video -c /home/vuos/code/p3/s51 -n 'GrupoC-Audio'
tmux new-window -t video -c /home/vuos/code/p3/s51 -n 'GrupoD-Shorts'
tmux new-window -t video -c /home/vuos/code/p3/s51 -n 'GrupoE-Editor'
tmux new-window -t video -c /home/vuos/code/p3/s51 -n 'Quality'
tmux new-window -t video -c /home/vuos/code/p3/s51 -n 'Visor'  # Para ver reportes

# Adjunta a la sesión
tmux attach -t video
```

### Opción 2: Comando único (copia y pega todo junto)
```bash
tmux kill-session -t video 2>/dev/null; cd /home/vuos/code/p3/s51 && tmux new-session -s video -d -c /home/vuos/code/p3/s51 -n Director && tmux new-window -t video -c /home/vuos/code/p3/s51 -n GrupoA-Remotion && tmux new-window -t video -c /home/vuos/code/p3/s51 -n GrupoB-AI && tmux new-window -t video -c /home/vuos/code/p3/s51 -n GrupoC-Audio && tmux new-window -t video -c /home/vuos/code/p3/s51 -n GrupoD-Shorts && tmux new-window -t video -c /home/vuos/code/p3/s51 -n GrupoE-Editor && tmux new-window -t video -c /home/vuos/code/p3/s51 -n Quality && tmux new-window -t video -c /home/vuos/code/p3/s51 -n Visor && tmux attach -t video
```

### Navegación rápida

| Tecla | Va a |
|-------|------|
| `Ctrl+B 0` | Director |
| `Ctrl+B 1` | Grupo A - Remotion |
| `Ctrl+B 2` | Grupo B - AI Gen |
| `Ctrl+B 3` | Grupo C - Audio |
| `Ctrl+B 4` | Grupo D - Shorts |
| `Ctrl+B 5` | Grupo E - Editor |
| `Ctrl+B 6` | Quality |
| `Ctrl+B 7` | Visor de reportes |
| `Ctrl+B n` / `p` | Siguiente / anterior |
| `Ctrl+B w` | Lista de ventanas |
| `Ctrl+B d` | Desconectar (todo sigue) |
| `Ctrl+B ,` | Renombrar ventana actual |

Para reconectar después de `Ctrl+B d`:
```bash
tmux attach -t video
```
