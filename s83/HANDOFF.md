# Handoff s81 → s82

## Resumen del sistema

Se construyó un sistema de agentes autónomos `j` en /home/vuos/code/p3/s81/.
El estado actual está documentado en PENDIENTE.md.

## Ventanas tmux (al salir de s81)
0: usr (conversación principal)
1: st (status, watch -n 1 bash ~/.j/bin/j-status)
2: dev (implementa)
3: buf (coordina)
4: tst (prueba)
5: bld (construye)

## Daemons corriendo
- jd en ~/.j/bin/jd (modos alerta y ronda)

## Bugs principales
Ver PENDIENTE.md — 6 bugs conocidos.

## Estilo de interacción
Usuario usa Termux + SSH + tmux desde Android. Respuestas concisas.
No asumir, verificar siempre.
No implementar, delegar al buffer.
