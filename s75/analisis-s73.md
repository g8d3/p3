# Análisis de Sesión: `input-s73.txt`

## 1. Decisiones de Arquitectura

| Decisión | Detalle |
|---|---|
| **Stack tecnológico** | Go sobre Python — `go` disponible, `python3` no. Servidor auto-contenido en un binario. |
| **Estructura del proyecto** | `main.go` (servidor + loop AI), `static/index.html` (frontend), `go.mod`. Sin framework web. |
| **Comunicación frontend-backend** | SSE (Server-Sent Events) para streaming de respuestas del AI. Endpoints: `POST /chat`, `GET/POST /api/config`. |
| **Gestión de sesiones** | En memoria (`map[string]*Session`), no persistente. Cada sesión guarda historial de mensajes. |
| **Loop AI → comando → resultado** | Mensaje → API → parsear `<cmd>` → `sh -c` → resultado → feedback como `system` (no `user`) → repetir hasta `<done>`. |
| **Corte forzado de loop** | Si el AI no decide terminar: detección de comandos duplicados (exact match) + límite de iteraciones (configurable, default 3) → `forcedSummary` con última salida. |
| **Configuración en UI** | Todas las variables (`api_key`, `base_url`, `model`, `system_prompt`, `max_iter`) configurables desde el panel de ajustes web, no solo env vars. |
| **Logging persistente** | Salida redirigida a `s73.log` para diagnóstico post-mortem. Errores viajan al cliente por SSE (`event: error`) y al log. |
| **Despliegue en display real** | Chrome sobre `DISPLAY=:0` (Xorg) en vez de headless + swiftshader para evitar ~250% CPU. |

---

## 2. Problemas Técnicos

| # | Problema | Causa raíz | Resolución |
|---|---|---|---|
| 1 | `env` no imprime nada | Script `~/.local/bin/env` sombreando a `/usr/bin/env` | Eliminar el script (~346 bytes, de un instalador de herramientas) |
| 2 | `OPENCODE_GO` no existe | Variable nunca definida en el entorno | Diagnosticar con `echo $OPENCODE_GO` en vez de `env \| grep` |
| 3 | `curl`/`wget` no disponibles | Sandbox `mvdan/sh` en el bash tool — intérprete minimalista Go | Usar `node -e` con `fetch()` o el tool `webfetch` |
| 4 | AI en loop infinito (`ls` sin parar) | El modelo nunca outputea `<done>`. El resultado se mandaba como `role: user` (AI creía que era nuevo pedido) | Feedback como `role: system` + detección de comandos duplicados + `max_iter` |
| 5 | API 500 intermitente | Error upstream en `opencode.ai/zen/go/v1/` — no sistemático (3/3 requests directas ok) | Logging + el error se muestra al cliente por SSE. Es intermitente del proveedor. |
| 6 | `kill` no funciona en bash tool | `mvdan/sh` no implementa `kill` como builtin | Usar `/bin/kill` con path completo o `fuser -k` |
| 7 | Chrome a 250% CPU | `--headless` + `--use-angle=swiftshader-webgl` emula GPU por software | Usar `DISPLAY=:0` real (Xorg en tty2) → baja a ~4% CPU |
| 8 | `address already in use` zombie | Proceso muerto pero socket no liberado; `kill -9` insuficiente | `fuser -k 8080/tcp` libera el port |
| 9 | `forcedSummary` también falla | Llamaba a la API y podía recibir el mismo 500 | Cambiar a resumen sin llamar API — mostrar último output directamente |
| 10 | Refs cambian entre instancias Chrome | La jerarquía DOM difiere entre Chrome headless y display real | Sacar snapshot fresco en cada sesión para obtener refs correctos |
| 11 | Mensajes duplicados en UI | Lógica de render en frontend | Ajustar `renderMessages()` para no duplicar |

---

## 3. Patrones de Trabajo

### Ciclo de desarrollo
```
Escribir → compilar → test (API) → test (browser) → diagnosticar → editar → repetir
```
Frecuencia de edición: ~1 cambio cada 2 minutos en fase intensiva. Compilación Go ~siempre exitosa.

### Flujo de diagnóstico de errores
1. **Sospecha de código → aislamiento**: Cuando el `500` aparecía en s73, se llamó al upstream directamente para confirmar que no era error propio.
2. **Problema de entorno → rastreo de PATH**: `env` roto → `which env` → `~/.local/bin/env` → script de instalación de herramientas → eliminación.
3. **Problema de performance → instrumentación**: CPU alta → `ps` + medición → hipótesis (swiftshader) → validación (Xvfb vs real display) → solución.
4. **Loop AI → múltiples estrategias**: Cambio de role (`user`→`system`) → dedup exacto → dedup aproximado → max iteraciones → forcedSummary sin AI → límite a 2 comandos.

### Roles en la interacción
- **Usuario como experto de dominio**: Aporta correcciones clave que el AI no detecta solo: *"revisa la consola del navegador"*, *"busca el display real en vez de crear uno virtual"*, *"hay log file?"*, *"prueba con la página no solo con la API"*.
- **AI como implementador rápido**: Ejecuta, itera, prueba. Tiende a sesgos de diagnóstico (asume error propio cuando es upstream, asume headless es la única opción).
- **Puja por calidad UI/UX**: Usuario insiste en que todo error se vea en cliente, toda config se cambie desde UI, sin editar archivos externamente.

### Disciplina operativa
- Matar procesos después de pruebas (Chrome, servers, agent-browser)
- Dejar logging persistente para diagnóstico sin supervisión
- Probar en múltiples niveles (API directa, servidor local, browser real)
- No asumir estabilidad de servicios externos — tratar 500 como hecho de vida

### Progresión del proyecto
```
Fase 1: Chat básico (3 archivos, loop AI→cmd→result)
Fase 2: Sesiones múltiples + prompt configurable
Fase 3: Config UI + manejo de errores visible
Fase 4: Logging + performance tuning (CPU Chrome)
Fase 5: Estabilización (dedup, límites, timeouts)
```

### Anti-patrones observados
- **AI alucina archivos del sistema** cuando no ejecuta comandos reales — corregido reforzando en system prompt que use comandos para datos reales.
- **AI no sabe detenerse** —requiere supervisión externa (dedup server-side, max iter). El modelo tiende a seguir ejecutando aunque ya tenga la respuesta.
- **Pruebas solo en API no alcanzan** — el frontend SSR/SSE tiene sus propios bugs (refs, render, parseo de eventos) que solo aparecen en browser real.
