# Pendientes y mejoras

> Documento de ideas, bugs y mejoras. Checklist para un framework web completo.

---

## Checklist de features para un framework web

| Feature | Estado | Prioridad |
|---|---|---|
| CRUD automático | ✅ Implementado | — |
| WebSocket | ✅ Implementado (2 backends) | — |
| Hot reload | ✅ Implementado | — |
| Auto-logging de operaciones | ✅ Implementado | — |
| Monitoreo de sistema | ✅ Implementado | — |
| Proxy para LLM | 📐 Diseñado | Alta |
| Namespaces y rutas jerárquicas | 📐 Diseñado | Alta |
| Multiplicidad de modelos | 📐 Diseñado | Alta |
| Inferencia (DB → código) | ❌ Pendiente | Media |
| Marketplace de templates | ❌ Pendiente | Media |
| Migraciones de DB | ❌ Pendiente | Alta |
| Background jobs | ❌ Pendiente | Media |
| Autenticación (login, tokens) | ❌ Pendiente | Alta |
| Autorización (roles, permisos) | ❌ Pendiente | Media |
| Row Level Security | ❌ Pendiente | Baja |
| Observabilidad (métricas, tracing) | ❌ Pendiente | Media |
| Tests automatizados | ❌ Pendiente | Alta |
| CLI (`nimbo create`, `nimbo apply`) | ❌ Pendiente | Media |
| README y onboarding | ❌ Pendiente | Alta |
| Linter y formato | ❌ Pendiente | Media |

---

## 1. Inferencia (DB → código Python)

Comando que lee una base de datos existente y genera `server.py` con los modelos.

```bash
nimbo infer sqlite:///data.db       # genera server.py
nimbo infer postgresql://...        # genera server.py
```

Generaría:

```python
from nimbo import App
app = App(__name__, db_url="sqlite:///data.db")

@app.model
class User:
    name: str
    email: str
    created_at: str

@app.model
class Post:
    title: str
    body: str
    user_id: int
    ...

app.serve()
```

**Abierto:** ¿el archivo generado es la fuente de verdad o la DB? Hoy el código Python es la fuente. La inferencia solo acelera la escritura inicial.

---

## 2. Marketplace de templates

Repositorio de plantillas de modelos que se aplican con un comando:

```bash
nimbo apply blog           # agrega User, Post, Comment
nimbo apply monitor        # agrega Process, Mount, Connection, Log
nimbo apply openai-proxy   # agrega OpenAI proxy con Request, TokenUsage
```

Cada template es código Python explícito que se copia al proyecto.
El usuario puede modificar el código después de aplicarlo.

**Abierto:** ¿repositorio centralizado (GitHub) o local? ¿Quién mantiene los templates?

---

## 3. Migraciones de base de datos

Hoy el framework crea tablas con `CREATE TABLE IF NOT EXISTS`. No hay migraciones.

Necesario para:

- Agregar columnas a tablas existentes
- Cambiar tipos de datos
- Renombrar tablas/campos
- Eliminar columnas

**Idea inicial:** migraciones automáticas detectando diferencias entre el schema del modelo y la tabla real. Rails-style `db/migrate/`.

**Abierto:** ¿migraciones implícitas (detectar diff y aplicar) o explícitas (generar archivos de migración)?

---

## 4. Background jobs

Tareas asíncronas que corren en segundo plano dentro del mismo proceso.

```python
@app.job(every="5m")
def check_health():
    ...

@app.job(cron="0 * * * *")
def hourly_report():
    ...
```

Sin Redis ni workers externos — usan `asyncio` dentro del event loop del servidor.

**Abierto:** ¿persistencia de jobs? ¿Reintentos? ¿Cola de mensajes?

---

## 5. Autenticación

Mecanismo básico de login:

```python
@app.auth
class User:
    username: str
    password: str    # hasheada automáticamente
```

Genera: `POST /login`, `POST /logout`, `GET /me`. Protege rutas con decorador `@app.require_auth`.

---

## 6. Browser APIs bridge

`@app.browser_api("dictation")` definido en servidor pero no expuesto al JS.

Falta:
- Que genere automáticamente `nimbo.api.dictation(text)`
- Soporte para: dictado, geolocalización, cámara, micrófono, notificaciones

---

## 7. Depurar backend WebSocket nativo

El backend nativo (0 deps) no funciona en navegador. El de la librería `websockets` sí.

**Pendiente:** encontrar el bug del nativo o descartarlo como opción.

---

## 8. Propagación de errores del cliente al servidor

Interceptar `window.onerror` y `window.onunhandledrejection` y enviarlos
al servidor por WebSocket.

---

## 9. Multi-DB con diferentes motores

`app.db("nombre", "url")` soporta SQLite. PostgreSQL planeado via `asyncpg`.

---

## 10. Comando `nimbo create`

```bash
nimbo create mi-app        # crea estructura de proyecto
nimbo create mi-app --db postgresql    # con PostgreSQL
```

---

## Bugs conocidos

- WS nativo no funciona en navegador (usar `ws_backend="websockets"`)
- Sin paginación visual en tabla CRUD (API soporta `?limit=` pero UI no lo expone)
- Sin tests
