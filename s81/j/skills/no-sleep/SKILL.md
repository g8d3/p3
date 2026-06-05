# Regla: No sleep, no polling

**Todo agente en este sistema debe cumplir:**

1. **NUNCA uses `sleep`** en bash, scripts, loops, ni ningún comando.
2. **NUNCA hagas polling** (esperar X segundos y revisar).
3. **Todo es event-driven**: escribí al bus (`~/.j/bus/`), usá `tmux send-keys`, o esperá a que te hablen.
4. **Si necesitás saber si algo terminó**: que el otro agente te escriba cuando termine. No lo revises vos.
5. **Si necesitás coordinar**: usá `tmux send-keys -t <target> "<mensaje>" Enter`. El receptor responde cuando termina.

## Por qué

- `sleep` + polling = sistema lento, reactivo, y difícil de depurar
- Eventos = sistema rápido, autónomo, y escalable
- `tmux send-keys` es el mecanismo de comunicación
- `~/.j/bus/` es el almacenamiento persistente de mensajes

## Excepciones

Ninguna. Ni siquiera un `sleep 0.1`. Si creés que necesitás un sleep, rediseñá el flujo para que sea event-driven.
