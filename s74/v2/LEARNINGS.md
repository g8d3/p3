# v1 → v2: Lecciones aprendidas

## Lo que funcionó

- **Arquitectura de versiones**: copias completas del código (base/ → v{N}/) con symlink `live` para activar. Simple, robusto, sin necesidad de git.
- **Hot reload del orquestador**: watch cada 2s sobre server.py. Fundamental para no tener que reiniciar a mano.
- **WebSocket push**: el servidor empuja estado a los clientes. Mejor que polling.
- **Tags con relaciones many-to-many**: tabla tags + version_tags + tag_rels. Flexible, el AI puede auto-generarlos del diff.
- **Agente find/replace**: más confiable que pedirle al LLM que genere el archivo completo.

## Lo que no funcionó

- **Mezclar UI de gestión y app versionada en el mismo HTML**: confuso para el usuario, difícil de mantener.
- **El orquestador y las versiones compitiendo**: ruteo confuso (/ vs /app/ vs /v{N}/).
- **Minificar el HTML en server.py**: imposible de leer y editar. El HTML debe vivir en archivos separados.
- **Benchmarks y leaderboard en la UI de base**: no deberían estar visibles por defecto — son herramientas de desarrollo.
- **Falta de indicación visual del agente**: el usuario crea una tarea y no ve nada hasta que termina.

## Decisiones para v2

1. **Orquestador mínimo**: solo sirve API y rutea archivos. No contiene UI.
2. **Cada versión contiene su UI completa**: gestión + app, todo en una página.
3. **Rutas compartibles**: `/v003/task/abc` muestra la versión 3 viendo la tarea abc.
4. **Agente visible**: indicador "agente trabajando" con barra de progreso.
5. **HTML no minificado**: archivos separados, legibles, comentados.
6. **Config desde UI**: benchmarks, modelos, intervalo, todo configurable.
7. **Tags como feature de primera clase**: auto-tagueo, filtros, búsqueda.
8. **Fusión de versiones**: seleccionar UI de v001 + funcionalidad de v002 = v003.
9. **Sin `sleep` en pruebas**: eventos, WebSocket, polling corto.

## Arquitectura v2

```
s74/v2/
├── orchestrator.py   ← Mínimo: API + file server + hot reload
├── versions/
│   ├── base/         ← Template inicial completo
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   ├── v001/         ← Copia de base + cambios del agente
│   └── live → base/  ← Symlink
├── agent.py          ← Agente IA (encargado de modificar versiones)
└── start.sh
```

## API endpoints (v2)

| Ruta | Método | Función |
|---|---|---|
| `/api/state` | GET | Estado completo |
| `/api/tasks` | POST | Crear tarea (→ agente trabaja) |
| `/api/tasks/{id}/approve` | POST | Aprobar → activa versión |
| `/api/tasks/{id}/reject` | POST | Rechazar → borra versión |
| `/api/versions/activate` | POST | Cambiar versión activa |
| `/api/tags` | GET | Listar tags |
| `/api/versions/{v}/tags` | POST | Asignar tags a versión |
| `/api/config` | GET/POST | Config (benchmarks, etc.) |
| `/diff/{task_id}` | GET | Diff entre versiones |
| `/{v}/{path}` | GET | Servir archivos de la versión |
