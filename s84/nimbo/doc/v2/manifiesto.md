# nimbo v2 — Manifiesto de diseño

> Documento único. Fuente única de verdad.
> Las contradicciones no existen — si dos interpretaciones chocan, el manifiesto gana.

---

## Índice

1. [Filosofía](#1-filosofía)
2. [Inicio rápido](#2-inicio-rápido)
3. [Decoradores](#3-decoradores)
4. [Namespaces y rutas](#4-namespaces-y-rutas)
5. [Multiplicidad y anidación](#5-multiplicidad-y-anidación)
6. [Contratos de API](#6-contratos-de-api)
7. [WebSocket](#7-websocket)
8. [Registro de decisiones](#8-registro-de-decisiones)

---

## 1. Filosofía

El objetivo central es **minimizar la carga cognitiva del desarrollador**.
Cada decisión se evalúa contra esta pregunta: *"¿esto hace que el framework sea más fácil de recordar y usar, o lo complica?"*

Consecuencias:

- **Un solo patrón para todo**: la API sigue siempre `/api/{model}[/{id}][/{acción}]`. No hay rutas especiales.
- **Menos imports, menos archivos**: una app cabe en un solo archivo con 30 líneas.
- **Los decoradores son auto-documentantes**: `@app.system` se lee como "esto es del sistema".
- **Contratos mínimos**: lo que el frontend necesita del backend cabe en dos variables (`__NIMBO_RESOURCES__`, `__NIMBO_CONFIGS__`).
- **2 líneas y funciona**: si la clase está vacía, el decorador provee campos por defecto.

---

## 2. Inicio rápido

### CRUD básico

```python
from nimbo import App
app = App(__name__)

@app.model
class Contact:
    name: str
    email: str
    phone: str

app.serve()
```

**Genera:** tabla CRUD en `/contact`, UI mobile. 2 líneas de framework + 3 campos.

### Monitor de procesos

```python
from nimbo import App
app = App(__name__)

@app.system
class Process: ...

app.serve()
```

**Genera:** tabla en `/process` con `pid`, `name`, `cpu_percent`, `memory_percent`, `status`.
Auto-refresh, botón ✕ para matar. El framework detecta "Process" y sabe qué datos mostrar.

### Proxy para LLM

```python
from nimbo import App
app = App(__name__)

@app.proxy
class OpenAI: ...

app.serve()
```

**Genera:** proxy en `/openai` que reenvía a OpenAI.
El framework detecta "OpenAI" en el registry y completa `upstream`, `api_key`, etc.

### App completa: proxy + sistema + logs

```python
from nimbo import App
app = App(__name__)

@app.proxy
class OpenAI: ...
@app.system
class Process: ...
@app.log
class Log: ...

app.serve()
```

**Genera:** proxy OpenAI, monitoreo de procesos, auditoría de todo. 6 líneas efectivas.

---

## 3. Decoradores

Cada decorador expresa **la naturaleza del modelo** — qué es, de dónde vienen sus datos, qué se puede hacer con él.

### 3.1 `@app.model`

Registra el modelo como tabla en base de datos con CRUD completo.

```python
@app.model
class Task:
    name: str
    description: str
```

| Parámetro | Default | Descripción |
|---|---|---|
| `table` | nombre de clase en minúscula | Nombre de la tabla en DB y ruta API |
| `db` | `"default"` | Conexión de base de datos |
| `run` | `None` | Campo ejecutable (atajo para `@app.run`) |

**Único campo automático:** `id` (autoincremental). Siempre presente, no se declara en la clase.

Los modelos con clase vacía solo tienen `id`:

```python
@app.model
class Tag: ...
# → tabla con id y nada más (útil como placeholder o para relaciones)
```

El usuario declara todos los campos visibles explícitamente:

### 3.2 `@app.system`

Modelo virtual sin base de datos. Obtiene datos del sistema vía psutil.

```python
@app.system                    # procesos (default)
class Process: ...

@app.system("mount")           # monturas de disco
class Mount: ...

@app.system("network")         # conexiones de red
class Connection: ...

@app.system("service")         # servicios del sistema
class Service: ...

@app.system("user")            # usuarios del sistema
class User: ...
```

| Parámetro | Default | Descripción |
|---|---|---|
| (primer arg) | infiere del nombre de clase | Fuente de datos: `"process"`, `"mount"`, `"network"`, `"service"`, `"user"` |
| `refresh` | `5` | Intervalo de auto-refresh en segundos |
| `id` | `"pid"` | Campo identificador |
| `kill` | `True` | Botón ✕ (solo aplica a `"process"`) |

**Inferencia del nombre de clase:**
- `class Process:` → fuente `"process"`
- `class Mount:` → fuente `"mount"`
- `class Connection:` → fuente `"network"`
- `class Service:` → fuente `"service"`
- `class User:` → fuente `"user"`

La regla es simple: el nombre de clase en minúscula es la fuente. No hay tabla oculta de mapeo.

**Campos por defecto por fuente:**

| Fuente | Campos por defecto |
|---|---|
| `"process"` | `pid: int`, `name: str`, `cpu_percent: float`, `memory_percent: float`, `status: str` |
| `"mount"` | `device: str`, `mount: str`, `fstype: str`, `usage: float` |
| `"network"` | `fd: int`, `family: str`, `type: str`, `laddr: str`, `raddr: str`, `status: str` |
| `"service"` | `name: str`, `status: str`, `pid: int`, `started: str` |
| `"user"` | `name: str`, `terminal: str`, `host: str`, `started: str`, `pid: int` |

El usuario puede agregar campos extra sin repetir los defaults:

```python
@app.system
class Process:
    username: str      # se agrega a los campos por defecto
    cmdline: str
```

### 3.3 `@app.log`

Modelo de auditoría. Tabla en DB de solo lectura, auto-poblada por el framework.

```python
@app.log
class Log:
    source: str
    level: str
    content: str
    time: str
```

Sin parámetros. Si la clase está vacía, provee `source`, `level`, `content`, `time`.

El framework auto-escribe en cada CRUD y cada ejecución (`@app.run`). Máximo 200 registros en DB.

### 3.4 `@app.proxy`

Proxy reverso para LLMs. Corre en la misma app o en puerto separado.

```python
@app.proxy
class OpenAI: ...
# upstream inferido de "OpenAI" → https://api.openai.com
# api_key_env inferido de "OpenAI" → OPENAI_API_KEY
# corre en la misma app, ruta /openai

@app.proxy(port=9098)
class Anthropic: ...
# upstream inferido de "Anthropic" → https://api.anthropic.com
# corre en puerto separado 9098

@app.proxy(upstream="https://custom.api.com", api_key="sk-...")
class CustomProxy: ...
# upstream explícito, api_key directa (literal)

@app.proxy(upstream="https://custom.api.com", api_key_env="MY_CUSTOM_KEY")
class CustomProxy: ...
# upstream explícito, api_key desde variable de entorno
```

| Parámetro | Default | Descripción |
|---|---|---|
| `port` | `None` (misma app) | Puerto separado para el proxy |
| `upstream` | inferido del nombre de clase | URL base del proveedor LLM |
| `api_key` | `None` | API key directa (literal en código) |
| `api_key_env` | `None` | Variable de entorno con la API key |
| `discovery` | función por defecto | Función que descubre agentes. Sin parámetro = psutil + whitelist |

**Resolución de api_key (primero que se encuentre):**
1. `api_key` si se pasó como literal
2. `api_key_env` si se pasó (lee la variable de entorno con ese nombre)
3. Inferido del nombre de clase: variable `{NOMBRE}_API_KEY` (ej: `OpenAI` → `OPENAI_API_KEY`)

**Registry de proveedores conocidos:**

| Nombre | `upstream` | Variable de entorno |
|---|---|---|
| `OpenAI` | `https://api.openai.com` | `OPENAI_API_KEY` |
| `Anthropic` | `https://api.anthropic.com` | `ANTHROPIC_API_KEY` |
| `OpenCode` | `https://opencode.ai/go/v1` | `OPENCODE_API_KEY` |

**Discovery y naming de agentes:**

El parámetro `discovery` acepta una función o se omite para usar la default:

```python
@app.proxy                           # discovery por defecto
class OpenAI: ...

@app.proxy(discovery=mi_funcion)      # personalizado
class OpenAI: ...
```

La función por defecto:
1. Ejecuta `psutil.process_iter()` y filtra por una whitelist interna: `["tmux", "opencode", "python3", "crush"]`
2. Para cada proceso encontrado, extrae: nombre (del proceso o ventana tmux), PID, CPU, memoria
3. Devuelve `[{agent_id, pid, cpu, mem_pct, window}, ...]`
4. `agent_id` se genera como `"{nombre-proceso}-{pid}"`

Si el usuario necesita extender la default, la importa:

```python
from nimbo.discovery import default_discovery

def mi_funcion():
    agentes = default_discovery()
    return [a for a in agentes if a["cpu"] > 0]
```

**Campos por defecto (clase vacía):** `agent_id: str`, `status: str`, `pid: int`, `cpu: float`, `mem_pct: float`, `window: str`, `last_active: float`.

**Comportamiento:**
1. Intercepta peticiones HTTP y reenvía al upstream
2. Descubre agentes periódicamente vía la función `discovery`
3. Marca agente como **activo** mientras su petición está en curso; **idle** en cuanto se envía la respuesta
4. Registra cada llamada en el modelo `Log`
5. Expone agentes vía CRUD: `GET /{ruta}` lista agentes

### 3.5 `@app.namespace`

Define el prefijo de ruta de una clase contenedora.

```python
@app.namespace                 # sin args → nombre de clase en minúscula
class Api: ...                 # ruta /api/...

@app.namespace("perro")        # con parámetro → nombre personalizado
class Api: ...                 # ruta /perro/...
```

| Parámetro | Default | Descripción |
|---|---|---|
| (primer arg) | nombre de clase en minúscula | Prefijo de ruta (un solo segmento, sin `/`) |

Un namespace **no es un modelo**. Es solo un organizador de rutas. No genera API propia, no tiene campos, no se registra como recurso.

Las clases hijas heredan el prefijo de ruta del namespace padre:

```python
@app.namespace
class Api:
    @app.model
    class User: ...    # ruta: /api/user

    @app.model
    class Post: ...    # ruta: /api/post
```

Si un hijo tiene su propio `@app.namespace`, se concatenan los segmentos:

```python
@app.namespace
class Api:
    @app.namespace
    class V1:
        @app.model
        class User: ...    # ruta: /api/v1/user
```

**Restricciones:**
- Un namespace es **un solo segmento** de ruta (sin `/`)
- Para rutas multi-nivel, se anidan namespaces
- Una clase no puede ser namespace y modelo a la vez

### 3.6 `@app.run`

Marca un campo como ejecutable (comando shell). Genera `POST /api/{modelo}/run/{id}`.

Requiere `@app.model` — no tiene sentido solo.

```python
@app.model
@app.run("shell", timeout="timeout")
class Command:
    shell: str = ""
    timeout: int = 30
```

| Parámetro | Default | Descripción |
|---|---|---|
| (primer arg) | (requerido) | Nombre del campo que contiene el comando shell |
| `timeout` | `"timeout"` | Nombre del campo del timeout |

También puede pasarse como parámetro directo de `@app.model`:

```python
@app.model(run="shell")
class Command:
    shell: str = ""
```

### 3.7 `@app.action`

Marca un método de clase como acción personalizada. Genera un botón en la UI.

```python
@app.model
class Command:
    shell: str = ""

    @app.action                    # sin args → usa el nombre del método
    def reboot(self, item):
        import subprocess
        subprocess.run(["reboot"])
        return {"ok": True}

    @app.action("restart")         # con nombre explícito
    def restart_server(self, item):
        ...
```

| Parámetro | Default | Descripción |
|---|---|---|
| `name` | nombre del método | Identificador de la acción (ruta y etiqueta) |

**Genera:** botón en la tabla y endpoint `POST /api/{model}/{action_name}/{id}`.

### 3.8 Tabla resumen

| Decorador | ¿Requiere DB? | Defaults | UI generada |
|---|---|---|---|
| `@app.model` | Sí | `id` (autoincremental) | CRUD completo |
| `@app.system` | No | según fuente | Tabla auto-refresh, ✕ opcional |
| `@app.log` | Sí | `source`, `level`, `content`, `time` | Tabla solo lectura |
| `@app.proxy` | No | `agent_id`, `status`, etc. | Proxy + monitoreo de agentes |
| `@app.namespace` | No | — | No genera UI |
| `@app.run` | No (requiere `@app.model`) | — | Botón ▶ |
| `@app.action` | No (requiere `@app.model`) | — | Botón personalizado |

---

## 4. Namespaces y rutas

### 4.1 Patrón de ruta universal

```
/{namespace}/{model}[/{id}][/{acción}]
```

Donde:
- `{namespace}` es opcional (pueden ser múltiples segmentos anidados)
- `{model}` es el nombre del modelo (inferido de la clase o explícito vía `table`)
- `{id}` es opcional (solo para GET/PUT/DELETE de un registro)
- `{acción}` es opcional (solo para `run` y acciones personalizadas)

### 4.2 Resolución de namespace

1. Si la clase está dentro de una o más clases con `@app.namespace`, los prefijos se concatenan en orden
2. Si la clase tiene su propio `@app.namespace`, ese segmento se agrega después del del padre
3. Si no hay `@app.namespace`, la ruta es directamente `/{model}`

Ejemplos:

```python
# Sin namespace
@app.model
class Task: ...                # → /task

# Namespace simple (sin args → nombre de clase)
@app.namespace
class Api:
    @app.model
    class Task: ...            # → /api/task

# Namespace anidado (sin args ambos → nombres de clase)
@app.namespace
class Api:
    @app.namespace
    class V1:
        @app.model
        class Task: ...        # → /api/v1/task

# Con parámetro: solo cuando el nombre de ruta difiere del nombre de clase
@app.namespace("perro")
class Gato:
    @app.model
    class Task: ...            # → /perro/task
```

### 4.3 Namespace y herencia de contenido

Se usa **herencia de clases Python** para que un namespace herede modelos de otro:

```python
@app.namespace
class Api:
    @app.model
    class User:
        name: str
        email: str

# V1 hereda los modelos de Api, pero con su propio prefijo de ruta
@app.namespace
class V1(Api):
    pass
# Rutas: /api/user, /v1/user

# V2 hereda de V1 y extiende User
@app.namespace
class V2(V1):
    @app.model
    class User(Api.User):
        phone: str
# Rutas: /v2/user (con phone), /v1/user (sin phone)
```

No hay herencia automática "mágica". La herencia de contenido siempre es explícita vía herencia de clases Python. Esto evita ambigüedades de dependencia cíclica y orden de definición.

### 4.4 Namespace vacío sin `@app.namespace`

Si una clase anidada dentro de un namespace no tiene `@app.namespace`, **hereda el namespace del padre** pero no agrega un segmento propio:

```python
@app.namespace
class Api:
    class V1:              # sin @app.namespace
        @app.model
        class User: ...    # → /api/user (hereda namespace de Api)
```

Para crear un subsegmento, la clase hija debe tener `@app.namespace`:

```python
@app.namespace
class Api:
    @app.namespace         # sin args → nombre "v1"
    class V1:
        @app.model
        class User: ...    # → /api/v1/user
```

### 4.5 Proxy con puerto separado

Cuando `@app.proxy` usa `port`, **todo el grupo** (proxy + modelos hijos) corre en ese puerto. El grupo es autónomo.

```python
@app.proxy(port=9098)
class OpenAI:
    @app.model
    class Request:
        prompt: str
        response: str
```

- `GET /openai` → lista agentes (puerto 9098)
- `POST /openai/v1/chat/completions` → proxy (puerto 9098)
- `GET /openai/request` → CRUD de requests (puerto 9098)
- `GET /` → CRUD de modelos raíz (puerto principal, 8080)

Sin `port`, todo vive en el mismo puerto. Con `port`, el grupo se aísla en su propio puerto.

---

## 5. Multiplicidad y anidación

### 5.1 Múltiples instancias del mismo decorador

Cada decorador puede usarse múltiples veces con diferentes clases:

```python
@app.proxy
class OpenAI: ...

@app.proxy
class Anthropic: ...
# Rutas: /openai, /anthropic

@app.system
class Process: ...

@app.system("mount")
class Mount: ...
# Rutas: /process, /mount
```

El nombre de clase distingue cada instancia.

### 5.2 Múltiples logs

```python
@app.log
class AuditLog: ...

@app.log
class ProxyEvent:
    agent_id: str
    method: str
    route: str
    status_code: int
    duration_ms: float
```

Cada log es una tabla independiente en DB. El framework escribe automáticamente en todas.

### 5.3 Modelos anidados bajo proxy

```python
@app.proxy(port=9098)
class OpenAI:
    @app.model
    class Request:
        prompt: str
        response: str
        model: str
        tokens: int
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

**Reglas:**
1. Los hijos heredan el prefijo de ruta del padre: `/openai/request`, `/openai/token-usage`
2. Los hijos heredan la base de datos del padre
3. Un hijo puede tener sus propios decoradores (`@app.run`, `@app.action`)
4. Los hijos heredan el `port` del proxy. Si el padre tiene puerto separado, todo el grupo vive en ese puerto.

### 5.4 CRUD batch

> Endpoint opcional en v2. Implementación planificada para v2.1.

```http
POST /batch
Content-Type: application/json

{
  "operations": [
    {"action": "create", "model": "user", "data": {"name": "Alice"}},
    {"action": "delete", "model": "category", "id": 5}
  ]
}
```

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `operations` | array | (requerido) | Lista de operaciones |
| `atomic` | bool | `false` | Si `true`, falla todo si una operación falla |

Cada operación:

| Campo | Descripción |
|---|---|
| `action` | `create`, `read`, `update`, `delete` |
| `model` | Nombre del modelo |
| `id` | ID del registro (para read/update/delete) |
| `data` | Datos (para create/update) |

---

## 6. Contratos de API

### 6.1 Server → Cliente (inyectado en HTML)

#### `window.__NIMBO_RESOURCES__`

```json
["contact", "process", "log"]
```

Lista de nombres de modelos en orden de registro. El cliente construye la navegación a partir de esta lista.

#### `window.__NIMBO_CONFIGS__`

```json
{
  "process": {
    "api": "/api/process",
    "id": "pid",
    "refresh": 5000,
    "noCreate": true,
    "noEdit": true,
    "kill": true,
    "fields": [
      {"name": "pid", "type": "int"},
      {"name": "name", "type": "string"},
      {"name": "cpu_percent", "type": "float", "label": "CPU%"},
      {"name": "memory_percent", "type": "float", "label": "MEM%"},
      {"name": "status", "type": "string"}
    ]
  }
}
```

| Campo | Obligatorio | Default | Descripción |
|---|---|---|---|
| `fields` | sí | — | Schema de la tabla para el CRUD |
| `api` | no | `"/api/{model}"` | Endpoint para listar datos |
| `id` | no | `"id"` | Campo identificador |
| `refresh` | no | — | Intervalo de auto-refresh (ms) |
| `noCreate` | no | `false` | Oculta botón "+ New" |
| `noEdit` | no | `false` | Oculta botón "✎" |
| `noDelete` | no | `false` | Oculta botón "🗑" |
| `kill` | no | — | Muestra botón "✕" (DELETE /api/{model}/{id}) |
| `actions` | no | — | Array de acciones personalizadas |

#### Formato de acciones

```json
{
  "actions": [
    {"label": "▶", "class": "btn-primary", "handlerTemplate": "run"}
  ]
}
```

`handlerTemplate` es una referencia a una función JavaScript predefinida. Actualmente: `"run"` (ejecuta `POST /api/{model}/run/{id}`).

### 6.2 Cliente → Servidor (API REST)

#### CRUD universal

| Método | Ruta | Cuerpo | Respuesta | Uso |
|---|---|---|---|---|
| `GET` | `/api/{model}` | — | `[{...}, ...]` | Listar |
| `GET` | `/api/{model}/schema` | — | `{"name":"{model}","fields":[...]}` | Schema |
| `GET` | `/api/{model}/{id}` | — | `{...}` | Leer uno |
| `POST` | `/api/{model}` | `{...}` | `{...}` | Crear |
| `PUT` | `/api/{model}/{id}` | `{...}` | `{...}` | Actualizar |
| `DELETE` | `/api/{model}/{id}` | — | `{...}` | Borrar |
| `POST` | `/api/{model}/run/{id}` | — | `{"stdout":"...","stderr":"...","returncode":0}` | Ejecutar |
| `POST` | `/api/{model}/{action}/{id}` | — | `{...}` | Acción personalizada |

#### Query parameters

| Parámetro | Ejemplo | Descripción |
|---|---|---|
| `?limit=N` | `?limit=50` | Máximo de registros |
| `?offset=N` | `?offset=100` | Desplazamiento |
| `?sort=campo` | `?sort=-created_at` | Ordenar (prefijo `-` para descendente) |
| `?{campo}={valor}` | `?status=running` | Filtrar por valor exacto |

#### Modelos virtuales (system, proxy)

Siguen el mismo patrón CRUD. Las operaciones que no aplican devuelven 405:

| Operación | Código |
|---|---|
| `POST /api/{model}` si `noCreate` | `405` |
| `PUT /api/{model}/{id}` si `noEdit` | `405` |

### 6.3 Formato de schema de campos

```json
{
  "name": "nombre_del_campo",
  "type": "string|int|float|bool",
  "label": "Etiqueta visible",
  "default": "valor por defecto"
}
```

| Tipo | Control HTML |
|---|---|
| `string` | `<input type="text">` (o `<textarea>` si > 80 caracteres) |
| `int` | `<input type="number">` |
| `float` | `<input type="number" step="any">` |
| `bool` | `<input type="checkbox">` |

---

## 7. WebSocket

### 7.1 Conexión

```
ws://{host}:{port}/ws
```

### 7.2 Formato universal

```json
{"type": "{tipo}", "data": {...}}
```

### 7.3 Tipos de mensajes

| `type` | Dirección | Descripción |
|---|---|---|
| `log` | ambas | Evento de log |
| `crud` | servidor → cliente | Notificación de cambio CRUD |
| `model:{model}` | servidor → cliente | Actualización de datos vivos |
| `system` | servidor → cliente | Stats del sistema (CPU, memoria, disco) |
| `reload` | servidor → cliente | El servidor se reinició |

### 7.4 Client-side API

```javascript
// Escuchar tipo específico
nimbo.ws.on('log', msg => { ... });
nimbo.ws.on('model:process', msg => { ... });
// O escuchar todo
nimbo.ws.on('message', msg => { ... });
```

### 7.5 Hot-reload

Cuando `NIMBO_RELOAD_CHILD` está activo, el servidor inyecta un script de livereload en `index.html` que abre un WebSocket a `/__nimbo/livereload` y recarga la página cuando la versión del servidor cambia.

---

## 8. Decisiones pendientes

| # | Tema | Discusión |
|---|---|---|
| 1 | `created_at` / `updated_at` automáticos | Rails los tiene como opt-in (migrations). En nimbo — ¿siempre presentes en `@app.model` como `id`? ¿Opcional? ¿Solo `created_at`? Impacto: ordenar por defecto, auditoría, DX vs simplicidad. |
| 2 | Límite de operaciones en batch CRUD | Definir tope máximo de operaciones por `POST /batch` cuando se implemente. |

---

## 9. Registro de decisiones

Decisiones explícitas tomadas en v2 que resuelven contradicciones de v1:

| # | Decisión | Resuelve |
|---|---|---|
| 1 | `upstream` se infiere del nombre de clase **por defecto**. No es requerido | `proxy-decorator.md` decía requerido; `decoradores.md` y ejemplos decían inferido |
| 2 | `port` default es `None` (misma app). Puerto separado es opt-in | `proxy-decorator.md` decía 9098; `decoradores.md` decía None |
| 3 | Los nombres de fuente de sistema son **singulares**: `"process"`, `"mount"`, `"network"`, `"service"`, `"user"` | `multiplicidad.md` usaba `"processes"`; `decoradores.md` mezclaba `"mounts"`, `"users"` |
| 4 | `kill` solo aplica a `"process"`. Para otras fuentes se ignora silenciosamente | `multiplicidad.md` usaba `kill=False` con `"mounts"` |
| 5 | `@app.model` con clase vacía solo provee `id` (autoincremental). Sin `name` ni `description` automáticos | `decoradores.md` v1 prometía `name`, `description`; decisión v2: los campos visibles los declara el usuario |
| 6 | Los nombres de namespace son **un solo segmento** (sin `/`). Para rutas multi-nivel se anidan namespaces | `versionado.md` usaba `"api/v2"` con slash |
| 7 | Solo existe **un mecanismo** de herencia de contenido: herencia de clases Python. No hay herencia automática "mágica" | `versionado.md` proponía dos mecanismos ambiguos |
| 8 | `@app.action` se documenta oficialmente como decorador de métodos de clase, distinto de `@app.run` | Existía en código pero no en docs |
| 9 | CRUD batch se aplaza a v2.1. Mencionado en el manifiesto pero no en contratos oficiales | `multiplicidad.md` lo diseñaba pero no estaba en contratos |
| 10 | `port` en proxy aplica a todo el grupo (proxy + modelos hijos). El grupo es autónomo en su propio puerto | `multiplicidad.md` v1 no aclaraba; decisión v2: el `port` abarca todo el grupo por legibilidad |
