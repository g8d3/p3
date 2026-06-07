# Multiplicidad y anidación de decoradores

## Filosofía: mínimo esfuerzo, máxima potencia

Cada decorador debe funcionar **con la menor cantidad de parámetros posible**.
El default debe ser el caso de uso más común. Todo lo demás es configurable,
pero no obligatorio.

### Dos líneas y ya funciona

Si la clase está vacía, el decorador provee sus campos por defecto:

```python
@app.system
class Process: ...
# → pid, name, cpu_percent, memory_percent, status

@app.log
class Log: ...
# → source, level, content, time

@app.model
class Task: ...
# → name, description (o los que tenga sentido)

@app.proxy
class Proxy: ...
# → agent_id, status, pid, cpu, mem_pct, window, last_active
```

Si el usuario necesita campos extra, los agrega sin repetir los defaults:

```python
@app.system
class Process:
    username: str      # se agrega a los campos por defecto
    cmdline: str
```

Sin leer documentación, dos líneas y tenés tabla CRUD con monitoreo de procesos.

---

## Namespace con decorador separado

`@app.namespace` define el prefijo de ruta de una clase y todas sus hijas.

```python
@app.namespace("perro")       # La clase se llama Api pero la ruta es /perro/
class Api: ...
# → /perro/...

@app.namespace                # Sin nombre = usa el nombre de la clase en minúscula
class Api: ...
# → /api/...
```

### Herencia a hijos

El namespace se hereda a todas las clases definidas dentro:

```python
@app.namespace("perro")
class Api:

    @app.model
    class User: ...
    # → /perro/user

    @app.model
    class Post: ...
    # → /perro/post
```

Si un hijo tiene su propio `@app.namespace`, lo overridea:

```python
@app.namespace("perro")
class Api:

    @app.namespace("gato")
    @app.model
    class User: ...
    # → /gato/user (no /perro/user)
```

### Namespace default por decorador

Cada decorador tiene un namespace default que se usa si no hay `@app.namespace`:

| Decorador | Namespace default |
|---|---|
| `@app.model` | nombre de la clase |
| `@app.system` | nombre de la clase |
| `@app.log` | nombre de la clase |
| `@app.proxy` | nombre de la clase |
| `@app.namespace` (sin args) | nombre de la clase en minúscula |

### Ejemplos

```python
# Default del decorador: /api/
@app.model
class Task: ...
# → /api/task

# Namespace explícito overridea el default
@app.namespace("data")
@app.model
class Task: ...
# → /data/task

# Proxy sin namespace explícito: usa default /proxy/
@app.proxy("openai", upstream="...")
class OpenAIProxy: ...
# → /proxy/openai/v1/chat

# Proxy con namespace explícito
@app.namespace("llm")
@app.proxy("openai", upstream="...")
class OpenAIProxy: ...
# → /llm/openai/v1/chat

# Proxy con puerto separado (namespace irrelevante)
@app.proxy("openai", upstream="...", port=9098)
class OpenAIProxy: ...
# → http://localhost:9098/v1/chat
```

### Namespace como concepto unificador

```
/{namespace}/{nombre}[/{id}][/{accion}]
```

Sin namespaces no sabrías dónde vive cada cosa. Con `@app.namespace`, es explícito y heredable.

---

## Problema actual

Hoy los decoradores son planos y singulares:

```python
@app.model        # Un solo modelo
@app.system       # Un solo sistema
@app.log          # Un solo log
```

No puedes definir:
- **Dos proxies** (OpenAI + Anthropic cada uno con sus propios modelos anidados)
- **Dos fuentes de sistema** (procesos + monturas de disco)
- **CRUD batch** (múltiples operaciones en una petición)

---

## 1. Decoradores con nombre

Cada decorador puede recibir un nombre como primer argumento para crear múltiples instancias:

```python
@app.proxy("openai", upstream="https://api.openai.com", port=9098)
class OpenAIProxy: ...

@app.proxy("anthropic", upstream="https://api.anthropic.com", port=9099)
class AnthropicProxy: ...
```

Rutas:
- `GET /proxy/openai` (agentes del proxy OpenAI)
- `GET /proxy/anthropic` (agentes del proxy Anthropic)

### Proxy sin puerto (misma app)

```python
@app.namespace("/llm/")
@app.proxy("openai", upstream="https://api.openai.com")
class OpenAIProxy: ...
```

Sin `port`, el proxy corre en la misma app:

```
http://localhost:8080/llm/openai/v1/chat  ← tráfico proxy
http://localhost:8080/api/                 ← CRUD normal
```

### Casos de uso del proxy

| Configuración | Ejemplo |
|---|---|
| Proxy simple, mismo puerto | `@app.proxy("llm", upstream="...")` |
| Proxy con puerto separado | `@app.proxy("llm", upstream="...", port=9098)` |
| Proxy con auth | `@app.proxy("llm", upstream="...", api_key="sk-...")` |
| Proxy con rate limit | `@app.proxy("llm", upstream="...", rpm=60)` |
| Proxy con cache | `@app.proxy("llm", upstream="...", cache_ttl=300)` |
| Proxy local (sin upstream) | `@app.proxy("local", upstream=None)` |

### Mismo puerto vs separado

| Situación | Recomendación |
|---|---|
| Desarrollo local | Misma app |
| Producción, varios agentes | Puerto separado |
| Proxy interno | Misma app |
| Proxy público | Puerto separado + auth |

---

## 2. Multiplicidad en todos los decoradores

### `@app.system` múltiple

```python
@app.system("processes")
class Process:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str

@app.system("mounts", kill=False)
class Mount:
    device: str
    mount: str
    fstype: str
    usage: float
```

### `@app.log` múltiple

```python
@app.log("audit")
class AuditLog: ...

@app.log("proxy-events")
class ProxyEvent:
    agent_id: str
    method: str
    route: str
    status_code: int
    duration_ms: float
```

---

## 3. Modelos anidados

Un decorador con nombre actúa como contenedor de modelos hijos.

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

Rutas:

| Ruta | Qué hace |
|---|---|
| `GET /proxy/openai` | Lista agentes |
| `GET /proxy/openai/request` | Lista requests |
| `POST /proxy/openai/request` | Crea request (lo envía al upstream) |
| `GET /proxy/openai/token-usage` | Lista uso de tokens |

### Reglas de anidación

1. **Un padre puede tener múltiples hijos.**
2. **Los hijos heredan el prefijo de ruta del padre.**
3. **Los hijos heredan la base de datos del padre.**
4. **Un hijo puede tener sus propios decoradores** (`@app.run`, etc.).
5. **Ruta completa:** `/{namespace}/{padre}/{hijo}`.

---

## 4. CRUD batch

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
    {"action": "delete", "model": "category", "status": 204, "id": 5}
  ]
}
```

Atomicidad opcional con `"atomic": true`.

---

## 5. Mapeo `fields`

```python
@app.system("processes",
    fields={"id": "pid", "cpu": "cpu_percent", "memory": "mem_pct"})
class Process:
    pid: int
    cpu_percent: float
    mem_pct: float
```

Si `fields` se omite, el decorador busca por convención de nombre:
- `id` → `id`, `pid`, `uuid`
- `status` → `status`, `state`
- `cpu` → `cpu`, `cpu_percent`, `usage`
- `time` → `time`, `timestamp`, `created_at`, `date`

---

## Preguntas abiertas

1. **¿`@app.namespace` puede aplicarse a modelos anidados o solo al nivel raíz?**
2. **¿Hasta qué profundidad de anidación es útil?**
3. **FK automática entre padre e hijo?**
4. **¿`atomic` en batch desde el inicio?**
5. **¿Límite de operaciones por batch?**
