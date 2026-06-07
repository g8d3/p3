# Changelog

## 0.1.0 — 2026-06-06

Primera versión estable. Framework funcional con app base agentui.

### Framework core
- CRUD automático desde type hints de clase Python
- Decoradores: `@app.model`, `@app.run("campo")`, `@app.system`, `@app.log`
- Auto-logging de operaciones CRUD en modelo de auditoría
- WebSocket con backend intercambiable (nativo 0-deps / librería websockets)
- Hot reload con livereload vía WebSocket
- API REST unificada: `GET/POST /api/{model}`, `GET/PUT/DELETE /api/{model}/{id}`, `POST /api/{model}/run/{id}`
- Parámetros de consulta: `?limit=`, `?sort=`, `?campo=valor`
- Servidor asyncio sin dependencias externas
- Multi-DB: conexiones nombradas con `app.db("nombre", "url")`

### App agentui
- Modelos: Agent, DataSource, Command (ejecutable con ▶), Process (sistema con ✕), Log (auditoría)
- Tabla CRUD con ordenamiento por columna y filtros en cada campo
- Monitoreo del sistema: CPU, RAM, Disk, Net
- Live Logs con timestamps del servidor
- Navegación por hash que preserva pestaña activa
- Auto-refresh de datos vivos (procesos, logs)
- Confirmación antes de matar procesos

### Documentación
- `doc/contratos.md` — contratos entre capas (API, WebSocket, frontend)
- `doc/decoradores.md` — filosofía y referencia de decoradores
- `doc/aprendizajes.md` — lecciones del proyecto
- `doc/pendientes.md` — bugs y mejoras conocidas
- `doc/reporte-calidad.md` — auditoría de calidad externa

### Bugs conocidos
- WS nativo no funciona correctamente en navegador (usar `ws_backend="websockets"`)
- Sin paginación visual en tabla CRUD (API soporta `?limit=` pero UI no la expone)
- Sin tests automatizados
- Sin autenticación
