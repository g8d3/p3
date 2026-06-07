# Multiplicidad y anidación de decoradores

## Problema

Hoy los decoradores son planos y singulares:

```python
@app.model        # Un solo modelo
@app.system       # Un solo sistema
@app.log          # Un solo log
@app.proxy        # Un solo proxy (propuesto)
```

No puedes definir:
- **Dos proxies** (OpenAI + Anthropic cada uno con sus propios modelos)
- **Dos modelos anidados** (Proxy → Request, Proxy → TokenUsage)
- **Dos fuentes de sistema** (procesos + monturas de disco)
- **CRUD batch** (crear 5 registros de 3 modelos distintos en una sola petición)

---

## 1. Decoradores con nombre

Cada decorador puede recibir un nombre como primer argumento. Ese nombre se usa en rutas, URLs y referencias.

```python
@app.proxy("openai", upstream="https://api.openai.com", port=9098)
class OpenAIProxy:
    agent_id: str
    status: str
    ...

@app.proxy("anthropic", upstream="https://api.anthropic.com", port=9099)
class AnthropicProxy:
    agent_id: str
    status: str
    ...
```

### ¿Por qué dos proxies?

**Escenario real:** un sistema multi-agente donde algunos agentes usan OpenAI y otros Anthropic. Cada proxy:

- Corre en su propio puerto (9098, 9099) para no interferir
- Tiene su propia configuración de upstream, timeout, y rate limit
- Tiene sus propios modelos anidados (Request, TokenUsage) para auditoría separada
- Se monitorea independientemente en el dashboard

### Casos de uso del proxy

| Configuración | Ejemplo |
|---|---|
| Proxy simple, un upstream | `@app.proxy("llm", upstream="https://api.openai.com")` |
| Proxy con autenticación | `@app.proxy("llm", upstream="...", api_key="sk-...")` |
| Proxy con rate limiting | `@app.proxy("llm", upstream="...", rpm=60)` |
| Proxy con cache | `@app.proxy("llm", upstream="...", cache_ttl=300)` |
| Proxy local (sin upstream) | `@app.proxy("local", port=9097, upstream=None)` — solo registra peticiones |

---

## 2. Multiplicidad en todos los decoradores

### `@app.system` múltiple

```python
@app.system("processes", api="/api/process", id="pid")
class Process:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str

@app.system("mounts", api="/api/mounts", kill=False)
class Mount:
    device: str
    mount: str
    fstype: str
    usage: float

@app.system("connections", api="/api/net-connections", refresh=2)
class Connection:
    fd: int
    family: str
    type: str
    laddr: str
    raddr: str
    status: str
```

Cada uno:
- Tiene su propio endpoint de datos (`/api/process`, `/api/mounts`, etc.)
- Tiene su propia configuración de refresh, kill, etc.
- Aparece como un modelo independiente en la navegación

### `@app.log` múltiple

```python
@app.log("audit")
class AuditLog:
    source: str
    action: str
    detail: str
    time: str

@app.log("proxy-events")
class ProxyEvent:
    agent_id: str
    method: str
    route: str
    status_code: int
    duration_ms: float
    time: str

@app.log("errors")
class ErrorLog:
    source: str
    message: str
    traceback: str
    time: str
```

Cada uno:
- Es una tabla independiente en DB
- Tiene su propio auto-refresh y config
- Se auto-puebla desde diferentes partes del sistema

### `@app.model` múltiple

```python
@app.model
class User:
    name: str
    email: str

@app.model
class Post:
    title: str
    body: str
    user_id: int

@app.model
class Category:
    name: str
    description: str
```

(Los modelos múltiples ya funcionan hoy. La novedad es poder anidarlos.)

---

## 3. Modelos anidados

Un decorador con nombre actúa como **contenedor** de modelos hijos. Los hijos heredan el contexto del padre.

### Ejemplo completo: proxy con modelos anidados

```python
@app.proxy("openai", upstream="https://api.openai.com", port=9098)
class OpenAIProxy:
    agent_id: str
    status: str
    pid: int
    cpu: float
    window: str
    last_active: float

    @app.model
    class Request:
        prompt: str
        response: str
        model: str
        tokens: int
        duration_ms: float
        agent_id: str       # FK implícita al padre

    @app.model
    class TokenUsage:
        model: str
        date: str
        prompt_tokens: int
        completion_tokens: int
        total_tokens: int
        cost: float
```

Rutas generadas:

| Ruta | Qué hace |
|---|---|
| `GET /api/openai-proxy` | Lista agentes del proxy |
| `GET /api/openai-proxy/request` | Lista requests |
| `POST /api/openai-proxy/request` | Crea request (lo envía al upstream) |
| `GET /api/openai-proxy/token-usage` | Lista uso de tokens |
| `POST /api/openai-proxy/token-usage` | Registra uso manual |

### Otro ejemplo: sistema de archivos

```python
@app.system("filesystem", api="/api/filesystem")
class FileSystem:
    device: str
    mount: str
    size: int
    used: int
    avail: int
    usage: float

    @app.model
    class MountOption:
        mount: str
        option: str
        value: str

    @app.model
    class IOStat:
        device: str
        reads: int
        writes: int
        read_bytes: int
        write_bytes: int
        time: str
```

### Reglas de anidación

1. **Un padre puede tener múltiples hijos.** No hay límite.
2. **Los hijos heredan el prefijo de ruta del padre.** Ej: `/api/openai-proxy/request`.
3. **Los hijos heredan la base de datos del padre** (misma DB, mismas migraciones).
4. **Un hijo puede tener sus propios decoradores.** Ej: `@app.model` puede tener `@app.run`.
5. **Los hijos pueden tener hijos** (anidación recursiva).
6. **La ruta completa se construye concatenando nombres:** `/{abuelo}/{padre}/{hijo}`.

---

## 4. CRUD batch: múltiples operaciones en una petición

Además de multiplicidad en modelos, se necesita multiplicidad en operaciones:
crear, actualizar y borrar varios registros de varios modelos en **una sola petición HTTP**.

### API batch

```http
POST /api/batch
Content-Type: application/json

{
  "operations": [
    {"action": "create", "model": "user", "data": {"name": "Alice", "email": "alice@x.com"}},
    {"action": "create", "model": "user", "data": {"name": "Bob", "email": "bob@x.com"}},
    {"action": "create", "model": "post", "data": {"title": "Hello", "body": "World", "user_id": 1}},
    {"action": "update", "model": "category", "id": 3, "data": {"name": "Updated"}},
    {"action": "delete", "model": "category", "id": 5},
  ]
}
```

### Respuesta

```json
{
  "results": [
    {"action": "create", "model": "user", "status": 201, "id": 1},
    {"action": "create", "model": "user", "status": 201, "id": 2},
    {"action": "create", "model": "post", "status": 201, "id": 10},
    {"action": "update", "model": "category", "status": 200, "id": 3},
    {"action": "delete", "model": "category", "status": 204, "id": 5}
  ]
}
```

### ¿Para qué sirve?

| Escenario | Sin batch | Con batch |
|---|---|---|
| Crear usuario + post + categoría en onboarding | 3 peticiones | 1 petición |
| Borrar 50 logs viejos | 50 peticiones | 1 petición |
| Sincronizar datos entre agentes | N peticiones | 1 petición |

### Atomicidad

Por defecto, batch ejecuta en orden y no es atómico (si falla la operación 3,
las 1 y 2 ya se ejecutaron).

Se puede agregar `"atomic": true` para envolver todo en una transacción:

```json
{
  "atomic": true,
  "operations": [...]
}
```

---

## 5. Mapeo `fields`

Todos los decoradores deben soportar `fields` para mapear conceptos del decorador
a columnas del modelo. Esto es especialmente importante para decoradores como
`@app.proxy` y `@app.system` donde el decorador necesita saber qué campo usar
para cada concepto.

```python
@app.system("processes",
    fields={
        "id": "pid",            # campo identificador único
        "status": "status",      # campo de estado
        "cpu": "cpu_percent",    # campo de uso de CPU
        "memory": "mem_pct",     # campo de uso de memoria
    })
class Process:
    pid: int
    name: str
    cpu_percent: float
    mem_pct: float
    status: str
```

### Convención

- Si `fields` no se especifica, el decorador usa defaults por convención de nombre:
  - `id` → busca `id`, `pid`, `uuid`
  - `status` → busca `status`, `state`
  - `cpu` → busca `cpu`, `cpu_percent`, `usage`
  - `time` → busca `time`, `timestamp`, `created_at`, `date`
- Si se especifica `fields`, los defaults se sobreescriben.

---

## 6. UI: navegación con namespace

La navegación del frontend muestra nombres compuestos con indentación:

```
openai-proxy
  request
  token-usage
anthropic-proxy
  request
  token-usage
process
mounts
connections
audit
proxy-events
errors
user
post
category
```

Los modelos anidados se muestran como hijos indentados. `__NIMBO_CONFIGS__` incluye
un campo `parent` para que el frontend sepa cómo agruparlos.

---

## Preguntas abiertas

1. **Profundidad máxima:** ¿2 niveles (padre → hijo) o más? ¿3?
2. **FK automática:** ¿El hijo debe tener automáticamente una foreign key al padre? ¿O se declara explícitamente con `fields`?
3. **Transacciones en batch:** ¿`"atomic": true` se implementa desde el inicio o se deja para después?
4. **Namespace puro:** ¿Tiene sentido `@app.namespace("nombre")` como contenedor sin comportamiento, para agrupar modelos no relacionados?
5. **Rendimiento batch:** ¿Hay un límite de operaciones por petición batch?
