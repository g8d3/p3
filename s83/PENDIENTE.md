# PENDIENTE.md — s82

## Contexto desde s81

Sistema `j` completo en construcción. s81 desarrolló componentes, daemons, status window.

### Bugs al salir de s81
1. Status muestra ○ idle para todos aunque trabajen (detección rota)
2. jd alerta monitorea a*/in en vez de dev/in buf/in tst/in bld/in
3. j flow next no notifica al agente asignado
4. Daemons no se auto-reparan
5. j go no hace switch real
6. Actividad no se correlaciona con flows DB

### Próximos pasos
1. Arreglar detección de estado (usar flow DB, no pane patterns)
2. Arreglar jd alerta inbox paths
3. Notificación al asignar flow steps
4. Auto-reparación en jd ronda
