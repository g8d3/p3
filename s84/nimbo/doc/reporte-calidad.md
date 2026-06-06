# Reporte de Calidad — nimbo

> Generado el 2026-06-06 · Revisión estática (sin ejecución)

---

## Resumen

| Aspecto | Valoración |
|---|---|
| Calidad del código | 7/10 |
| Rendimiento estimado | 8/10 |
| UX (usuario final) | 5/10 |
| DX (desarrollador) | 4/10 |
| Cobertura de documentación | 1/10 |

---

## 1. Calidad del código por módulo

### 1.1 `nimbo/server.py` (502 líneas) — ⚠️ Aceptable con deuda técnica

**Fortalezas:**
- Arquitectura limpia: `App`, `Request`, `Response` con responsabilidades bien definidas
- Hot-reload funcional con proceso padre/hijo y livereload vía WebSocket
- CRUD automático a partir de modelos con type hints
- Manejo de errores con try/except en los puntos clave

**Debilidades:**
- SQL injection potencial: `_auto_crud()` inserta el nombre del modelo directamente en el path. Si el nombre del modelo contiene caracteres especiales, se genera una ruta inválida o insegura
- El reemplazo de `<id>` en rutas es frágil: solo contempla `<id>` y `<path>`, no es extensible
- `_serve_static()` construye `file_path` concatenando strings (path traversal potencial si bien se mitiga con `os.path.exists`)
- La función `_match_route()` importa `re` dentro del cuerpo en cada llamada (ineficiente)
- `_watch_while_running()` usa `time.sleep(1)` con polling activo — consume CPU innecesariamente
- `_handle_http()` lee el header línea por línea hasta `\r\n\r\n` pero no tiene límite de tamaño de header → DoS potencial
- `_handle_ws_upgrade()` solo conecta el primer `ws_handler` registrado (no puede haber múltiples topics WS)
- La lógica de `_serve_static()` para inyectar scripts en `index.html` funciona pero usa `b"</head>"` como marcador — si el HTML no tiene `</head>`, falla silenciosamente

### 1.2 `nimbo/db.py` (159 líneas) — ✅ Buena calidad

**Fortalezas:**
- Patrón Strategy (Engine) bien aplicado
- `_SQLite` implementación limpia y completa
- `DBPool` con acceso por nombre, migración multi-DB
- `register_engine()` permite extender a PostgreSQL, MySQL, etc.

**Debilidades:**
- `migrate()` construye SQL concatenando nombres de tabla y campo sin sanitizar (SQL injection si los nombres vienen de entrada del usuario)
- `DEFAULT` para booleanos: lógica redundante con `if f.get("default") is True` y `is False` — se puede simplificar
- `create()` no valida que `data` no esté vacío — si se envía `{}`, genera `INSERT INTO t () VALUES ()` que falla
- No hay soporte para `async` — toda la DB es síncrona, puede bloquear el event loop

### 1.3 `nimbo/ws.py` (137 líneas) — ⚠️ Frágil

**Fortalezas:**
- Implementación RFC 6455 completa desde cero (0 dependencias)
- Manejo de frames enmascarados y no enmascarados
- Soporte para ping/pong

**Debilidades:**
- `recv()` usa `timeout=0.1` en el read → polling cada 100ms aunque no haya datos
- `decode_frame()` devuelve tuplas con strings mágicas (`__close__`, `__ping__`, `__pong__`) en vez de constantes o un enum
- Si el cliente envía un frame con opcode desconocido (0x3-0x7, 0xB-0xF), el servidor intenta decodificarlo como UTF-8 y falla silenciosamente
- No hay límite de tamaño de frame → un frame gigante puede saturar memoria (DoS)
- No hay soporte para fragmented messages (FIN=0)

### 1.4 `nimbo/system.py` (129 líneas) — ✅ Bueno

- Endpoints de sistema bien definidos
- `psutil` usado correctamente
- Log con cleanup automático (mantiene últimos 200)
- `kill_process` con manejo de errores por código HTTP apropiado

### 1.5 `nimbo/ws_base.py` (53 líneas) — ✅ Bueno

- Interfaz abstracta limpia
- `WSManager` pub/sub simple y funcional

### 1.6 `nimbo/ws_websockets.py` (105 líneas) — ✅ Bueno

- Adaptador limpio entre `websockets` library y la interfaz `WSConnection`
- `recv()` con timeout evita bloqueo infinito

### 1.7 `apps/agentui/server.py` (37 líneas) — ✅ Excelente

- Código mínimo y expresivo. Define 3 modelos en ~20 líneas efectivas
- Ejemplo claro del valor del framework

### 1.8 `static/` — ⚠️ Regular

**Fortalezas:**
- `crud.js`: CRUD frontend completo y configurable con acciones personalizadas
- `ws.js`: Cliente WebSocket con reconexión automática, eventos pub/sub
- `mobile.css`: Diseño responsive, dark mode, animaciones, utilidades

**Debilidades:**
- `index.html`: la navegación recarga el contenido completo (`innerHTML`) → pérdida de scroll y estado
- `crud.js`: `renderForm()` excluye campos `id` y `pid` de forma hardcodeada — debería ser configurable
- `ws.js`: no hay manejo de autenticación en la conexión WS
- No hay `favicon.ico` — el navegador registrará error 404 en cada carga
- `index.html` carga `/mobile.css` como única hoja de estilo — no hay soporte para desktop

---

## 2. Rendimiento estimado (sin ejecutar)

### 2.1 Cuellos de botella identificados

| Módulo | Problema | Impacto |
|---|---|---|
| `server.py:202` | `import re` dentro de `_match_route()` en cada request | Bajo — <1ms por request, pero evitable |
| `server.py:236` | Lectura de header sin límite de tamaño | Medio — DoS potencial con headers grandes |
| `server.py:412` | `time.sleep(1)` con polling de archivos en hot-reload | Medio — 1% CPU permanentemente |
| `ws.py:99` | Polling cada 100ms en `recv()` nativo | Bajo — 0.1s de latencia adicional |
| `db.py:38-43` | `INSERT` con `" ".join()` sin prepared statement estable | Bajo — SQLite es single-writer, no hay contención |

### 2.2 Estimación de throughput

- **Servidor HTTP**: ~500-1000 req/s estimados (asyncio puro, sin workers)
- **WebSocket nativo**: ~1000 msg/s (limitado por polling de lectura)
- **WebSocket con librería**: ~5000+ msg/s (event-driven real)
- **SQLite**: ~100-200 writes/s (WAL mode, single-writer)
- **Latencia media**: <10ms para requests simples, ~50ms para CRUD con DB

### 2.3 Recomendaciones de rendimiento

- Mover `import re` al tope del archivo (no dentro de la función)
- Agregar límite de tamaño del header HTTP (ej. 8192 bytes)
- Cuando el backend nativo WS no tenga datos, usar `asyncio.wait_for` con un timeout razonable en vez de polling
- Considerar `watchdog` (librería) en vez de polling manual para hot-reload

---

## 3. Experiencia de Usuario (UX)

### 3.1 Problemas detectados

| Problema | Severidad | Propuesta |
|---|---|---|
| Recarga completa de tabla en cada CRUD | Alta | Actualización parcial con diff de items |
| Sin feedback de "cargando" en llamadas API | Media | Spinner/placeholder en cada operación |
| Sin confirmación visual de "guardado" consistente | Baja | El toast existe pero no en todos los casos |
| Scroll perdido al cambiar de pestaña | Alta | Preservar posición de scroll por modelo |
| Sin soporte para teclado (Enter para guardar, Escape para cerrar modal) | Media | Hotkeys básicos en modal |
| Sin paginación en tablas con muchos registros | Baja | Agregar offset/limit en API y UI |
| Sin estado vacío visual atractivo | Baja | Ilustración o ícono cuando no hay items |

### 3.2 Mejoras propuestas

1. **Preservar scroll**: Guardar `scrollTop` por modelo en `sessionStorage` y restaurarlo al navegar
2. **Carga diferida (lazy)**: No cargar datos de todos los modelos al inicio, solo al hacer clic
3. **Feedback háptico**: Mostrar toast con checkmark animado tras crear/editar/eliminar
4. **Indicador de conexión WS**: El círculo verde/rojo existe pero es pequeño — agrandar o agregar texto

---

## 4. Experiencia del Desarrollador (DX)

### 4.1 Problemas detectados

| Problema | Severidad | Propuesta |
|---|---|---|
| No hay README.md | **Crítica** | Sin onboarding, nadie sabe cómo empezar |
| No hay AGENTS.md | **Crítica** | Sin guía para agentes AI, las contribuciones son inconsistentes |
| No hay tests | **Crítica** | Imposible hacer refactoring con confianza |
| No hay type hints completos en `server.py` | Media | Varias funciones sin tipos de retorno |
| No hay linter configurado (ruff, flake8, etc.) | Media | Sin formato consistente |
| `pyproject.toml` sin dependencias listadas | Media | `psutil` y `websockets` no están declaradas |
| No hay script de desarrollo (`dev` / `reload`) | Media | Hay que leer el código para saber que existe `reload=True` |
| No hay `.env` ni configuración por entorno | Baja | Las URLs de DB están hardcodeadas |

### 4.2 Archivos faltantes (recomendaciones)

```
nimbo/
├── README.md          ← ONBOARDING: qué es, cómo instalarlo, cómo usarlo
├── AGENTS.md          ← GUÍA: contexto, decisiones, convenciones para agentes AI
├── CONTRIBUTING.md    ← OPCIONAL: estándares de contribución
├── .env.example       ← OPCIONAL: variables de entorno documentadas
├── Makefile o scripts/  ← OPCIONAL: comandos comunes (run, test, lint)
└── tests/             ← OPCIONAL: tests unitarios y de integración
```

### 4.3 `README.md` sugerido (contenido mínimo)

```markdown
# nimbo

Framework web mínimo para agentes AI. CRUD automático desde type hints, WebSocket
nativo, hot-reload, y dashboard auto-generado.

## Quickstart

```bash
cd apps/agentui
python server.py          # Arranca en http://localhost:8080 con hot-reload
```

## Modelos

Define un modelo con 4 líneas:

```python
@app.model
class Task:
    title: str
    done: bool = False
```

Esto genera automáticamente: `GET/POST /api/task`, `GET/PUT/DELETE /api/task/<id>`,
y una tabla CRUD en el dashboard.

## Backend WebSocket

- **Nativo** (0 deps): `app.serve(ws_backend="native")`
- **websockets** (recomendado): `app.serve(ws_backend="websockets")`

## Comandos

```bash
python server.py              # Producción
python server.py --reload     # Desarrollo con hot-reload
```

## Dependencias

- `psutil` — monitoreo de sistema
- `websockets` — backend WS alternativo (opcional)
```

### 4.4 `AGENTS.md` sugerido (contenido mínimo)

```markdown
# Guía para Agentes AI — nimbo

## Stack
- Python 3.10+, asyncio, sin framework externo
- Frontend: vanilla JS, sin bundler
- Base de datos: SQLite (WAL mode), interfaz extensible a otros motores

## Arquitectura
- `nimbo/` — framework core
- `apps/` — aplicaciones construidas con nimbo
- `static/` — frontend compartido (JS/CSS)

## Convenciones
- No agregar dependencias sin justificación
- Preferir código mínimo que funciones sobre abstracciones complejas
- El CRUD automático es la interfaz universal — no crear dashboards custom salvo que sea necesario
- Si un bug aparece, hacer el backend intercambiable (como WS nativo vs librería) para comparar

## Tests
- No hay tests aún. Ejecutar manualmente con `python apps/agentui/server.py`

## Antes de contribuir
1. Leer `doc/aprendizajes.md` — contiene las lecciones del proyecto
2. Revisar `doc/pendientes.md` — bugs y mejoras conocidas
```

---

## 5. Seguridad

| Riesgo | Severidad | Descripción |
|---|---|---|
| Path traversal en static | Media | `_serve_static()` podría servir archivos fuera de `static/` si se construye path con `..` |
| SQL injection en `migrate()` | Media | Los nombres de tabla y columna se concatenan sin sanitizar |
| Sin autenticación | Alta | Cualquiera con acceso al puerto puede ver/kills procesos del sistema |
| Sin límite de header HTTP | Media | Un cliente malicioso puede enviar headers gigantes y saturar memoria |
| Sin rate limiting | Baja | Endpoints sin protección contra abuso |
| CORS abierto (`Access-Control-Allow-Origin: *`) | Baja | Aceptable para herramienta de desarrollo |

---

## 6. Scoreboard final

| Categoría | Puntaje | Justificación |
|---|---|---|
| **Código** | 7/10 | Bien estructurado, pero con varios code smells menores |
| **Rendimiento** | 8/10 | Asyncio bien usado; polling es la única debilidad |
| **UX** | 5/10 | Funcional pero sin refinamiento (scroll, feedback, carga) |
| **DX** | 4/10 | Sin README, sin tests, sin linter, dependencias no declaradas |
| **Seguridad** | 5/10 | Sin autenticación, path traversal posible, sin límites |
| **Documentación** | 1/10 | Solo hay `doc/aprendizajes.md` y `doc/pendientes.md` — no hay README |
| **Mantenibilidad** | 6/10 | Código pequeño y legible, pero sin tests que validen cambios |

**Promedio general: 5.1/10**

---

## 7. Hoja de ruta sugerida (prioridades)

1. **Agregar README.md y AGENTS.md** — urgencia máxima, sin esto el proyecto no es usable
2. **Agregar tests** — al menos un test de integración que arranque el server y haga un CRUD
3. **Declarar dependencias en pyproject.toml** — `psutil`, opcionalmente `websockets`
4. **Agregar límite de tamaño de header HTTP** — seguridad básica
5. **Configurar linter** — ruff con `pyproject.toml`
6. **Reemplazar polling por eventos** — ver sección 8 (empezar por #6 y #4)
7. **Eliminar sobre-envío de datos** — ver sección 9 (empezar por #B y #F)
8. **Actualización parcial del frontend** — diff DOM en lugar de `innerHTML` completo
9. **Agregar paginación en API CRUD** — `LIMIT/OFFSET` en listados
10. **Mover `import re` al tope del módulo**
11. **Sistema de autenticación básico** — token en header
12. **Event-driven pusher** — migrar `setInterval` cliente a broadcast WS del servidor

---

---

## 8. Inventario completo de polling en el código

A continuación, **todas las ocurrencias de espera activa (busy-wait / polling)** en el código, tanto servidor como cliente, con explicación y solución event-driven.

### 8.1 Servidor — Hot-reload (3 ocurrencias)

#### #1 — `server.py:412` — `time.sleep(1)` en watcher de archivos

```python
while process.poll() is None:
    time.sleep(1)                               # ← POLLING
    for f in watched:
        mt = os.path.getmtime(f)
        if mt != mtimes[f]:
            changed = f
```

**Por qué está ahí:** No hay una librería de sistema de archivos basada en eventos, entonces se compara `mtime` cada 1s. Es la implementación más simple de un file watcher.  
**Dificultad de solución:** Media.  
**Solución event-driven:** Reemplazar con [`watchdog`](https://pypi.org/project/watchdog/) que usa `inotify` en Linux:

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ReloadHandler(FileSystemEventHandler):
    def __init__(self, on_change):
        self.on_change = on_change
    def on_modified(self, event):
        if event.src_path.endswith(('.py', '.js', '.css', '.html')):
            self.on_change(event.src_path)

observer = Observer()
observer.schedule(ReloadHandler(lambda p: print(f"change: {p}")), path, recursive=True)
observer.start()
```

Esto elimina por completo `_watch_while_running()` y el `time.sleep(1)`.

#### #2 — `server.py:423` — `time.sleep(2)` debounce manual

```python
if changed:
    time.sleep(2)                               # ← POLLING
    mt2 = os.path.getmtime(changed)
```

**Por qué está ahí:** Espera a que el archivo terminé de escribirse antes de reiniciar. Sin esto, un editor que escribe en múltiples pasos (vim, VS Code) dispararía reinicios múltiples.  
**Dificultad de solución:** Baja (se elimina automáticamente si se implementa la #1 con `watchdog`).  
**Solución event-driven:** `watchdog` maneja el debounce internamente o se combina con `asyncio.Event`:

```python
async def debounced_reload(path, delay=2):
    await asyncio.sleep(delay)
    if os.path.getmtime(path) == last_mtime:
        return  # se revirtió
    trigger_reload(path)
```

#### #3 — `server.py:458` — `time.sleep(0.5)` entre reinicios

```python
p.kill()
p.wait()
time.sleep(0.5)                                  # ← POLLING
```

**Por qué está ahí:** Pequeña pausa para que el puerto se libere antes de que el nuevo proceso hijo lo bindee.  
**Dificultad de solución:** Baja.  
**Solución event-driven:** Usar `asyncio.create_subprocess_exec` + `await proc.wait()` (ya es event-driven), y para la espera de puerto, un pequeño loop con `asyncio.open_connection` en lugar de sleep fijo:

```python
await proc.wait()
# Esperar a que el puerto esté libre
for _ in range(10):
    try:
        r, w = await asyncio.open_connection(host, port)
        w.close()
        break
    except ConnectionRefusedError:
        await asyncio.sleep(0.1)
```

### 8.2 Servidor — WebSocket nativo (1 ocurrencia)

#### #4 — `ws.py:94-108` — loop con `timeout=0.1` para leer frames

```python
async def recv(self):
    while True:
        if self._buf:
            result, self._buf = decode_frame(self._buf)
        else:
            try:
                chunk = await asyncio.wait_for(
                    self.reader.read(4096), timeout=0.1  # ← POLLING
                )
            except asyncio.TimeoutError:
                return None                               # ← retorna None cada 100ms
```

**Por qué está ahí:** `recv()` es un método diseñado para ser *no bloqueante* — quien lo llama (ej. `ws_logs` en `system.py:108`) lo invoca en un `while not ws.closed` y espera recibir datos o `None`. Como no hay forma de esperar "hasta que llegue un frame O hasta que se cierre la conexión" sin un `wait_for`, se usa un timeout arbitrario de 100ms para retornar `None` periódicamente.  
**Dificultad de solución:** Media-alta (toca rediseñar la interfaz de `recv()`).  
**Solución event-driven:** Cambiar `recv()` para que sea **bloqueante** (espere hasta que llegue un frame real) y que el cierre se maneje con una excepción o señal:

```python
# Opción A: recv() bloqueante que espera el tiempo que sea necesario
async def recv(self):
    chunk = await self.reader.read(4096)  # sin timeout
    if not chunk:
        self.closed = True
        return None
    result, self._buf = decode_frame(chunk)
    return result[1] if result else None

# Opción B: usar asyncio.Event para señalizar cierre y asyncio.wait()
# para esperar simultáneamente datos y cierre:
async def recv(self):
    while not self.closed:
        read_task = asyncio.create_task(self.reader.read(4096))
        close_task = asyncio.create_task(self._close_event.wait())
        done, _ = await asyncio.wait(
            [read_task, close_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        if close_task in done:
            return None
        chunk = read_task.result()
        ...
```

**Impacto colateral:** Todos los llamadores de `recv()` que dependen del retorno periódico de `None` para hacer otras cosas (enviar heartbeats, etc.) tendrían que cambiar su lógica.

### 8.3 Servidor — WebSocket con librería `websockets` (1 ocurrencia, mismo patrón)

#### #5 — `ws_websockets.py:41` — `timeout=0.1` en `recv()`

```python
async def recv(self):
    try:
        msg = await asyncio.wait_for(
            self._ws.recv(), timeout=0.1          # ← POLLING
        )
        return msg
    except asyncio.TimeoutError:
        return None
```

**Por qué está ahí:** Idéntico al #4 — mantener compatibilidad con la interfaz `WSConnection.recv()` que retorna `None` periódicamente.  
**Dificultad de solución:** Media (misma que #4).  
**Solución event-driven:** Igual que #4. La ventaja aquí es que `websockets` library ya maneja ping/pong internamente, así que `recv()` sin timeout funciona perfectamente. Solo hay que actualizar los llamadores.

### 8.4 Servidor — Livereload WS (1 ocurrencia)

#### #6 — `server.py:223-224` — `asyncio.sleep(1)` en livereload

```python
if path == "/__nimbo/livereload":
    self._ws_manager.add(ws, "__nimbo_livereload")
    await ws.send(json.dumps({"type":"version","v":self._restart_count}))
    while not ws.closed:
        await asyncio.sleep(1)            # ← POLLING
    return
```

**Por qué está ahí:** Esta conexión WS solo existe para que el navegador reciba el mensaje "version" y detecte un reinicio. No tiene más mensajes entrantes. El `while not ws.closed` con `sleep(1)` mantiene viva la corutina para detectar cuándo el cliente se desconecta.  
**Dificultad de solución:** Baja.  
**Solución event-driven:** Usar un `Event` que se dispare cuando la conexión se cierre:

```python
disconnected = asyncio.Event()
ws._on_close = lambda: disconnected.set()  # o un callback en WSConnection
await disconnected.wait()  # bloquea hasta que el cliente se desconecte
```

O más simple: esperar a que `ws.recv()` retorne `None` (si se cambia a bloqueante como en #4), sin necesidad de sleep.

### 8.5 Servidor — psutil CPU (no es polling nuestro, pero值得一提)

#### #7 — `system.py:45` — `psutil.cpu_percent(interval=0.5)`

```python
"cpu": psutil.cpu_percent(interval=0.5),   # ← BLOQUEA 500ms
```

**Por qué está ahí:** `psutil.cpu_percent()` necesita un intervalo para medir la carga de CPU. Con `interval=0.5` se bloquea 500ms midiendo. No es polling en el sentido de loop, pero cada request a `/api/system/resources` tarda 500ms.  
**Dificultad de solución:** Baja (no es polling, es medición).  
**Solución:** Cachear el resultado con TTL ~2s para que no todos los requests paguen los 500ms:

```python
_cpu_cache = {"value": 0, "time": 0}
def get_cpu():
    now = time.time()
    if now - _cpu_cache["time"] > 2:
        _cpu_cache["value"] = psutil.cpu_percent(interval=0.5)
        _cpu_cache["time"] = now
    return _cpu_cache["value"]
```

### 8.6 Cliente — Stats del sistema (2 ocurrencias)

#### #8 — `index.html:171` — `setInterval(updateStats, 5000)`

```javascript
setInterval(updateStats, 5000);        // ← POLLING
```

**Por qué está ahí:** La navbar muestra CPU%, RAM%, Disk% en vivo. Como no hay push del servidor para estos valores, se polling cada 5s.  
**Dificultad de solución:** Baja.  
**Solución event-driven:** Enviar las stats por WebSocket. El servidor calcularía las stats cada ~2s y las broadcastearía a todos los clients conectados:

```python
# Servidor: tarea periódica que broadcast stats
async def broadcast_stats():
    while True:
        stats = get_resources_cached()
        await app._ws_manager.broadcast(
            json.dumps({"type": "stats", "data": stats})
        )
        await asyncio.sleep(2)

# Cliente: escuchar stats por WS
nimbo.ws.on('stats', (d) => updateStatsBar(d.data));
```

Esto elimina el `setInterval` y el fetch periódico.

#### #9 — `crud.js:261` — `setInterval(load, cfg.refresh)` (refresco periódico de tabla)

```javascript
timer = setInterval(() => {
    load();                              // ← POLLING
}, cfg.refresh);   // 5000ms para "process"
```

**Por qué está ahí:** Modelos como `process` tienen datos vivos del sistema que cambian constantemente. El `config.refresh=5000` hace polling cada 5s.  
**Dificultad de solución:** Baja.  
**Solución event-driven:** Mecanismo push similar al #8: cuando un modelo tiene `refresh`, el servidor puede enviar actualizaciones periódicas por WS. O mejor: que el servidor notifique cambios reales vía WS solo cuando los datos cambian significativamente:

```python
# Servidor: broadcast periódico de procesos
async def broadcast_processes():
    while True:
        procs = get_processes()
        await app._ws_manager.broadcast(
            json.dumps({"type": "crud_update", "model": "process", "data": procs}),
            topic=f"model:process"
        )
        await asyncio.sleep(2)
```

### 8.7 Cliente — Reconexión WS (NO es polling, pero se menciona)

#### #10 — `ws.js:26` — `setTimeout(reconnect, 2000)`

```javascript
ws.onclose = () => {
    reconnectTimer = setTimeout(() => connect(path), 2000);
};
```

**Por qué está ahí:** Reintentar conexión WS tras 2s si se cierra. No es polling (es un timer único que se reinicia en cada cierre).  
**Clasificación:** No es polling — es un **retraso de reconexión**, comportamiento estándar.

#### #11 — `index.html (línea ~357)` — `setTimeout(lr, 2000)` en livereload

```javascript
w.onclose = function() { setTimeout(lr, 2000); };
```

**Por qué está ahí:** Misma razón que #10: reconexión del livereload WS.  
**Clasificación:** No es polling.

### 8.8 Cliente — Toast auto-dismiss (NO es polling)

#### #12 — `crud.js:68` — `setTimeout(toast.remove, 2500)`

```javascript
const t = document.createElement('div');
t.className = `toast ${type}`;
document.body.appendChild(t);
setTimeout(() => t.remove(), 2500);
```

**Por qué está ahí:** El toast se muestra 2.5s y luego se elimina.  
**Clasificación:** No es polling. Es un timeout de UI, comportamiento estándar y correcto.

### 8.9 Resumen de ocurrencias

| # | Archivo | Línea | Tipo | ¿Es polling? | Dificultad |
|---|---|---|---|---|---|
| 1 | `server.py` | 412 | `time.sleep(1)` file watch | ✅ Sí | Media |
| 2 | `server.py` | 423 | `time.sleep(2)` debounce | ✅ Sí | Baja |
| 3 | `server.py` | 458 | `time.sleep(0.5)` restart | ✅ Sí | Baja |
| 4 | `ws.py` | 99 | `timeout=0.1` WS recv | ✅ Sí | Media-alta |
| 5 | `ws_websockets.py` | 41 | `timeout=0.1` WS recv | ✅ Sí | Media |
| 6 | `server.py` | 224 | `asyncio.sleep(1)` livereload | ✅ Sí | Baja |
| 7 | `system.py` | 45 | `interval=0.5` CPU meas. | ⚠️ Medición | Baja (cache) |
| 8 | `index.html` | 171 | `setInterval(5000)` stats | ✅ Sí | Baja |
| 9 | `crud.js` | 261 | `setInterval(refresh)` data | ✅ Sí | Baja |
| 10 | `ws.js` | 26 | `setTimeout(2000)` reconnect | ❌ No | — |
| 11 | `index.html` | ~357 | `setTimeout(2000)` LR recon. | ❌ No | — |
| 12 | `crud.js` | 68 | `setTimeout(2500)` toast | ❌ No | — |

### 8.10 Orden sugerido de eliminación

1. **#6 + #4** — Livereload + WS nativo `recv()`: son la base. Hacer `recv()` bloqueante elimina el polling del WS nativo y del livereload.
2. **#5** — WS websockets `recv()`: adaptar para que coincida con el nuevo `recv()` bloqueante.
3. **#8 + #9** — Stats y refresco de tabla: migrar de `setInterval` a push por WS (broadcast periódico del servidor).
4. **#1 + #2** — Hot-reload: migrar a `watchdog` (inotify).
5. **#3 + #7** — Optimizaciones menores (cache CPU, espera de puerto con `asyncio.open_connection`).

---

---

## 9. Sobre-envío de datos (over-fetching y re-renderizados completos)

Lugares donde se envía/recarga **más información de la necesaria**, causando tráfico innecesario, trabajo extra en base de datos, y parpadeo/pérdida de estado en UI.

### 9.1 API — `SELECT *` sin límite en listados

#### #A — `server.py:144` — `_db().list(name)` sin paginación

```python
@app.route(f"{base}", methods=["GET"])
async def list_all(req):
    return _db().list(name)     # ← Devuelve TODAS las filas
```

```python
# db.py:68
cur = self._conn.execute(f"SELECT * FROM {table}")  # ← Sin LIMIT
```

**Problema:** Si la tabla tiene 100k registros, esta petición carga todo a memoria y lo envía entero al cliente.  
**Solución:** Agregar paginación con `?limit=50&offset=0`:

```python
async def list_all(req):
    limit = int(req.query.get("limit", [50])[0])
    offset = int(req.query.get("offset", [0])[0])
    return _db().list(name, _limit=limit, _offset=offset)
```

#### #B — `system.py:100` — `all_logs = app._db.list("log")` + `[-50:]`

```python
@app.route("/api/log/recent", methods=["GET"])
async def recent_logs(req):
    all_logs = app._db.list("log")   # ← Carga TODOS los logs a memoria
    return all_logs[-50:]            # ← Descarta todo menos 50
```

**Problema:** Si hay 50k logs, se cargan todos desde SQLite, se parsean a diccionarios Python, y solo se devuelven 50. El 99.9% del trabajo es desperdiciado.  
**Solución:** Query con `ORDER BY id DESC LIMIT 50` directamente en SQL:

```python
async def recent_logs(req):
    cur = app._db.engine._conn.execute(
        "SELECT * FROM log ORDER BY id DESC LIMIT 50"
    )
    return [dict(r) for r in cur.fetchall()]
```

#### #C — `crud.js:load()` + `cfg.refresh=5000` — recarga completa cada 5s

```javascript
// crud.js:102-108
async function load() {
    items = await api('GET', apiBase);  // ← GET /api/process devuelve todo cada 5s
    render();                            // ← Recrea el tbody completo
}

// index.html:38
refresh: 5000,  // ← Incluso si nada cambió
```

**Problema:** Para procesos del sistema, donde CPU%/MEM% fluctúan, se envía el array completo de 50 procesos (~10KB) cada 5s aunque solo 1 o 2 valores numéricos hayan cambiado. El cliente además destruye y recrea todo el DOM de la tabla (cientos de nodos) cada vez.  
**Solución:** Enviar solo las diferencias (deltas) o usar push del servidor con las filas que cambiaron:

```javascript
// Cliente: en lugar de recargar todo, actualizar celdas individuales
function updateRow(item) {
    const row = document.getElementById(`row-${item.pid}`);
    if (row) {
        row.querySelector('.cpu-cell').textContent = item.cpu_percent;
        row.querySelector('.mem-cell').textContent = item.memory_percent;
    } else {
        addRow(item); // solo si es nuevo
    }
}
```

### 9.2 Frontend — Re-renderizado completo de DOM

#### #D — `crud.js:180` — `tbody.innerHTML = ''` en cada refresco

```javascript
if (tbody) {
    tbody.innerHTML = '';               // ← Destruye todo
    items.forEach(item => {             // ← Reconstruye todo
        const row = document.createElement('tr');
        // ... crea y añade cada celda ...
    });
}
```

**Problema:** Cada 5 segundos se eliminan y recrean todas las filas del tbody. Esto:
- Destruye el estado interno de los elementos del DOM
- Causa parpadeo si hay estilos con transiciones
- Aumenta GC pressure
- Pierde foco de teclado y selecciones
- Es trabajo innecesario si 49/50 filas no cambiaron

**Solución:** Identificar filas por `idField`, hacer diff, y solo agregar/remover/actualizar las que cambiaron:

```javascript
function render() {
    const newIds = new Set(items.map(i => i[idField]));
    // Eliminar filas que ya no existen
    tbody.querySelectorAll('tr').forEach(row => {
        if (!newIds.has(row.dataset.id)) row.remove();
    });
    // Actualizar o insertar filas
    items.forEach(item => {
        let row = tbody.querySelector(`tr[data-id="${item[idField]}"]`);
        if (row) updateRow(row, item);
        else tbody.appendChild(createRow(item));
    });
}
```

#### #E — `index.html:84` — `el.innerHTML = ''` en switchModel

```javascript
function switchModel(name) {
    // ...
    el.innerHTML = '';      // ← Destruye TODO el contenido previo
    cleanup = nimbo.crud.mount(el, name, schema.fields);
}
```

**Problema:** Cada vez que se cambia de pestaña, se destruye el contenido del `<main>` y se vuelve a crear desde cero. Si se vuelve a una pestaña visitada antes, hay que re-fetchear schema y datos de nuevo.  
**Solución:** Cachear instancias de modelos ya montados:

```javascript
const modelInstances = {};
function switchModel(name) {
    if (modelInstances[name]) {
        modelInstances[name].show();  // solo mostrar
    } else {
        modelInstances[name] = createModelView(name);
    }
}
```

#### #F — `index.html:123` — `sys-stats.innerHTML = ...` recarga completa

```javascript
document.getElementById('sys-stats').innerHTML =   // ← Recarga completo cada 5s
    `<span>CPU <span class="val">${d.cpu}%</span>...`;
```

**Problema:** El navbar de stats se reconstruye completamente cada 5s, aunque solo cambien 3 números.  
**Solución:** Asignar `id` a cada valor y usar `textContent`:

```html
<!-- HTML estático en el navbar -->
CPU <span id="stat-cpu">0%</span>
RAM <span id="stat-ram">0%</span>
Disk <span id="stat-disk">0%</span>
```

```javascript
function updateStats(d) {
    document.getElementById('stat-cpu').textContent = d.cpu + '%';
    document.getElementById('stat-ram').textContent = Math.round(d.memory.percent) + '%';
    document.getElementById('stat-disk').textContent = Math.round(d.disk.percent) + '%';
}
```

### 9.3 API — Respuestas completas cuando sobra la mitad de los campos

#### #G — `system.py:44-49` — `/api/system/resources` devuelve objetos enormes del SO

```python
async def get_resources(req):
    return {
        "cpu": ...,
        "memory": psutil.virtual_memory()._asdict(),  # ← 6-8 campos (total, avail, pct, used, free, active, inactive, buffers, cached, shared, slab)
        "disk": psutil.disk_usage("/")._asdict(),      # ← 5 campos
        "net": psutil.net_io_counters()._asdict(),     # ← 8 campos (bytes_sent, bytes_recv, packets_sent, packets_recv, errin, errout, dropin, dropout)
        "uptime": ...,
    }
```

**Problema:** `_asdict()` convierte todo el namedtuple, incluyendo campos que el frontend no usa. Por ejemplo, `svmem` tiene ~15 campos pero la UI solo usa `percent`. Se envían ~50 campos cuando se necesitan 3.  
**Solución:** Seleccionar solo los campos necesarios:

```python
mem = psutil.virtual_memory()
return {
    "cpu": ..., 
    "memory": {"percent": mem.percent, "total": mem.total, "available": mem.available},
    "disk": {"percent": psutil.disk_usage("/").percent},
    "net": {"bytes_sent": net.bytes_sent, "bytes_recv": net.bytes_recv},
}
```

### 9.4 Redundancia en cada navegación

#### #H — `index.html:79-82` — schema fetch + resources fetch en cada switchModel

```javascript
const schemaPromise = fetch(`/api/${name}/schema`).then(r => r.json());
const statsPromise = name === 'process' ? fetch('/api/system/resources').then(r => r.json()) : null;
```

**Problema:** El schema de un modelo no cambia nunca (es estático, definido en código). Sin embargo, se fetchea cada vez que se navega a esa pestaña. Igual para `/api/system/resources` en la pestaña "process".  
**Solución:** Cachear schema en el cliente, y cachear resources con TTL:

```javascript
const schemaCache = {};
function getSchema(name) {
    if (!schemaCache[name]) {
        schemaCache[name] = fetch(`/api/${name}/schema`).then(r => r.json());
    }
    return schemaCache[name];
}
```

### 9.5 Resumen de sobre-envíos

| # | Archivo | Línea | ¿Qué se sobre-envía? | Tamaño estimado extra | Solución |
|---|---|---|---|---|---|
| A | `server.py` | 144 | Todas las filas sin paginación | Ilimitado | `LIMIT/OFFSET` |
| B | `system.py` | 100 | Todos los logs para tomar 50 | 99.9% desperdicio | `ORDER BY DESC LIMIT 50` |
| C | `crud.js` | 102-108+261 | Array completo de datos cada 5s | ~10KB cada vez | Deltas por WS |
| D | `crud.js` | 180 | DOM completo destruido/recreado | N/A (perf. visual) | Diff de filas |
| E | `index.html` | 84 | Contenido de pestaña destruido al navegar | N/A (perf. visual) | Cache de instancias |
| F | `index.html` | 123 | HTML del navbar reconstruido cada 5s | ~200B×N | `textContent` directo |
| G | `system.py` | 44-49 | 50 campos del SO cuando se usan 3 | ~1.5KB×request | Filtrar respuesta |
| H | `index.html` | 80-81 | Schema fetch repetido en cada navegación | ~500B×navegación | Cache local |

---

*Reporte generado por revisión estática del código fuente en `nimbo/`.*
