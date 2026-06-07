# Multiplicidad y anidación de decoradores

## Filosofía: mínimo esfuerzo, máxima potencia

Cada decorador debe funcionar **con la menor cantidad de parámetros posible**.
El default debe ser el caso de uso más común. Todo lo demás es configurable,
pero no obligatorio.

```python
@app.proxy                      # Sin parámetros = proxy local, mismo puerto
class Proxy: ...

@app.system                     # Sin parámetros = monitoreo de procesos
class Process: ...

@app.log                         # Sin parámetros = auditoría básica
class Log: ...

@app.model                       # Sin parámetros = CRUD completo
class Task: ...
```

El desarrollador principiante hace cosas útiles sin leer documentación.
El desarrollador avanzado afina cada parámetro cuando lo necesita.

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

## Namespaces de ruta

Cada decorador asigna a sus modelos un **namespace** (prefijo de ruta) por defecto.
Esto define si una ruta empieza con `/api/`, `/proxy/`, etc.

| Decorador | Namespace default | Ejemplo de ruta |
|---|---|---|
| `@app.model` | `/api/` | `GET /api/user` |
| `@app.system` | `/api/` | `GET /api/process` |
| `@app.log` | `/api/` | `GET /api/audit` |
| `@app.proxy` | `/proxy/` | `POST /proxy/openai/v1/chat` |
| `@app.proxy` (con `port=`) | (su propio puerto) | `POST http://localhost:9098/v1/chat` |

El namespace se puede configurar explícitamente:

```python
@app.model(namespace="/data/")
class User: ...

@app.proxy("openai", namespace="/llm/", upstream="...")
class OpenAIProxy: ...
```

### ¿Por qué `/api/` vs `/proxy/`?

- `/api/` es para **datos** (CRUD). El cliente pide y recibe JSON.
- `/proxy/` es para **tráfico externo**. Recibe peticiones, las reenvía al upstream, devuelve la respuesta.

Separarlos evita confusión: `POST /api/command/run/1` es CRUD. `POST /proxy/openai/v1/chat` es proxy.

### Namespace con puerto separado

Con `port=`, el namespace es irrelevante porque el proxy corre en otro puerto:

```python
@app.proxy("openai", upstream="https://api.openai.com", port=9098)
# → http://localhost:9098/v1/chat/completions
```

Sin puerto, el namespace enruta dentro de la misma app:

```python
@app.proxy("openai", upstream="https://api.openai.com")
# → http://localhost:8080/proxy/openai/v1/chat/completions
```

### Namespace como concepto unificador

Todo sigue el mismo patrón:

```
/{namespace}/{nombre}[/{id}][/{accion}]
```

Sin namespaces no sabrías si `process` vive en `/api/process` o `/system/process`. Con namespaces, es explícito desde el decorador.

---

## 1. Decoradores con nombre

Cada decorador puede recibir un nombre como primer argumento. Ese nombre se usa en rutas y URLs:

```python
@app.proxy("openai", upstream="https://api.openai.com", port=9098)
class OpenAIProxy: ...

@app.proxy("anthropic", upstream="https://api.anthropic.com", port=9099)
class AnthropicProxy: ...
```

Rutas generadas:
- `GET /proxy/openai` (lista agentes del proxy OpenAI)
- `GET /proxy/anthropic` (lista agentes del proxy Anthropic)

### Proxy sin puerto (misma app)

```python
@app.proxy("local", upstream="https://api.openai.com")
class LocalProxy: ...
```

Sin `port`, el proxy corre en la misma app en el namespace `/proxy/`:

```
http://localhost:8080/proxy/local/v1/chat  ← tráfico proxy
http://localhost:8080/api/                  ← CRUD normal
```

### Casos de uso del proxy

| Configuración | Ejemplo |
|---|---|
| Proxy simple, mismo puerto | `@app.proxy("llm", upstream="...")` |
| Proxy con puerto separado | `@app.proxy("llm", upstream="...", port=9098)` |
| Proxy con autenticación | `@app.proxy("llm", upstream="...", api_key="sk-...")` |
| Proxy con rate limiting | `@app.proxy("llm", upstream="...", rpm=60)` |
| Proxy con cache | `@app.proxy("llm", upstream="...", cache_ttl=300)` |
| Proxy local (sin upstream) | `@app.proxy("local", upstream=None)` — solo registra |

### Mismo puerto vs puerto separado

| Situación | Recomendación |
|---|---|
| Desarrollo local, un agente | Misma app (sin puerto) |
| Producción, varios agentes | Puerto separado |
| Proxy interno (solo para la app) | Misma app |
| Proxy público (accesible desde internet) | Puerto separado + auth |

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

---

## 3. Modelos anidados

Un decorador con nombre actúa como **contenedor** de modelos hijos.

### Proxy con modelos anidados

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
        agent_id: str

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
| `GET /proxy/openai` | Lista agentes del proxy |
| `GET /proxy/openai/request` | Lista requests |
| `POST /proxy/openai/request` | Crea request (lo envía al upstream) |
| `GET /proxy/openai/token-usage` | Lista uso de tokens |

### Sistema de archivos anidado

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
2. **Los hijos heredan el prefijo de ruta del padre.** Ej: `/proxy/openai/request`.
3. **Los hijos heredan la base de datos del padre** (misma DB).
4. **Un hijo puede tener sus propios decoradores.** Ej: `@app.run`.
5. **Los hijos pueden tener hijos** (anidación recursiva).
6. **La ruta completa:** `/{namespace}/{nombre-padre}/{nombre-hijo}`.

---

## 4. CRUD batch

Múltiples operaciones en una sola petición:

```http
POST /api/batch
Content-Type: application/json

{
  "operations": [
    {"action": "create", "model": "user", "data": {"name": "Alice"}},
    {"action": "create", "model": "post", "data": {"title": "Hello"}},
    {"action": "delete", "model": "category", "id": 5}
  ]
}
```

Respuesta:

```json
{
  "results": [
    {"action": "create", "model": "user", "status": 201, "id": 1},
    {"action": "create", "model": "post", "status": 201, "id": 10},
    {"action": "delete", "model": "category", "status": 204, "id": 5}
  ]
}
```

### Atomicidad

```json
{"atomic": true, "operations": [...]}
```

Con `atomic: true`, todo se envuelve en una transacción. Si falla una operación, se revierte todo.

---

## 5. Mapeo `fields`

Todos los decoradores soportan `fields` para mapear conceptos a columnas:

```python
@app.system("processes",
    fields={
        "id": "pid",
        "status": "status",
        "cpu": "cpu_percent",
        "memory": "mem_pct",
    })
class Process:
    pid: int
    name: str
    cpu_percent: float
    mem_pct: float
    status: str
```

### Convención por nombre

Si `fields` se omite, el decorador busca por nombre de campo:
- `id` → busca `id`, `pid`, `uuid`
- `status` → busca `status`, `state`
- `cpu` → busca `cpu`, `cpu_percent`, `usage`
- `time` → busca `time`, `timestamp`, `created_at`, `date`

Si se especifica `fields`, los defaults se sobreescriben.

---

## 6. UI: navegación con namespace

```
/openai
  request
  token-usage
/anthropic
  request
  token-usage
/process
/mounts
/connections
/audit
/proxy-events
/errors
/user
/post
/category
```

Los hijos se muestran indentados. `__NIMBO_CONFIGS__` incluye `parent` y `namespace`
para que el frontend agrupe correctamente.

---

## Preguntas abiertas

1. **Profundidad máxima:** ¿2 niveles (padre → hijo) o más?
2. **FK automática:** ¿El hijo tiene FK al padre automáticamente?
3. **Transacciones en batch:** ¿`atomic` desde el inicio o después?
4. **Namespace puro:** ¿`@app.namespace("nombre")` como contenedor sin comportamiento?
5. **Límite batch:** ¿Cuántas operaciones por petición?
