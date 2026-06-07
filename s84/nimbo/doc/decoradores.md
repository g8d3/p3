# Filosofía de decoradores — nimbo

## Principio

Cada decorador sobre una clase expresa **la naturaleza del modelo** — qué es, de dónde vienen sus datos, qué se puede hacer con él.

No hay lógica procedural en la app. Solo declaración de intenciones.

## Mínimo esfuerzo

Si la clase está vacía, el decorador provee campos por defecto:

```python
@app.system
class Process: ...   # → pid, name, cpu_percent, memory_percent, status
```

El desarrollador escribe 2 líneas y ya tiene algo funcional. Si necesita más, agrega campos sin repetir los defaults.

---

## Decoradores actuales

### `@app.model`

Registra el modelo como tabla en base de datos con CRUD completo.

```python
@app.model
class Task: ...
```

Genera: `GET/POST /api/task`, `GET/PUT/DELETE /api/task/<id>`, schema endpoint, y tabla CRUD en el navegador.

Campos por defecto si la clase está vacía: `name: str`, `description: str`.

---

### `@app.run("campo", ...)`

Marca un campo como ejecutable (comando shell). Genera `POST /api/{modelo}/run/<id>`.

Requiere `@app.model` (no tiene sentido solo).

| Parámetro | Default | Descripción |
|---|---|---|
| `"campo"` | (requerido) | Nombre del campo que contiene el comando shell |
| `timeout` | `"timeout"` | Nombre del campo del timeout |

```python
@app.model
@app.run("shell", timeout="timeout")
class Command:
    shell: str = ""
    timeout: int = 30
```

---

### `@app.system`

Modelo virtual sin base de datos. Recibe un **vocabulario limitado** de fuentes de datos del sistema, no comandos arbitrarios.

```python
@app.system                  # procesos (default)
class Process: ...

@app.system("mounts")        # monturas de disco
class Mount: ...

@app.system("network")       # conexiones de red
class Connection: ...
```

| Parámetro | Default | Descripción |
|---|---|---|
| (primer arg) | `"process"` | Fuente de datos del sistema. Valores: `"process"`, `"mounts"`, `"network"`, `"services"`, `"users"` |
| `refresh` | `5` | Intervalo de auto-refresh en segundos |
| `kill` | `True` | Si tiene botón ✕ (solo para `"process"`) |

```python
@app.system
class Process:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str
```

El framework sabe cómo obtener cada fuente de datos internamente (psutil).
El usuario no escribe comandos ni endpoints.

Campos por defecto si la clase está vacía (según la fuente):

| Fuente | Campos por defecto |
|---|---|
| `"process"` | `pid`, `name`, `cpu_percent`, `memory_percent`, `status` |
| `"mounts"` | `device`, `mount`, `fstype`, `usage` |
| `"network"` | `fd`, `family`, `type`, `laddr`, `raddr`, `status` |

Si se omite el nombre de la fuente, el decorador infiere la fuente del nombre de la clase:
- `class Process:` → fuente `"process"`
- `class Mount:` → fuente `"mounts"`
- `class Connection:` → fuente `"network"`

---

### `@app.log`

Modelo de auditoría. Tabla en DB de solo lectura, auto-poblada por el framework.

Sin parámetros.

```python
@app.log
class Log:
    source: str
    level: str
    content: str
    time: str
```

Campos por defecto si la clase está vacía: `source`, `level`, `content`, `time`.

El framework auto-escribe en cada CRUD y cada ejecución (`@app.run`). Máximo 200 registros.

---

### `@app.proxy`

Proxy reverso para LLMs. Corre en la misma app o en puerto separado.

| Parámetro | Default | Descripción |
|---|---|---|
| `upstream` | (infiere del nombre) | URL del proveedor LLM |
| `port` | `None` | Puerto separado (misma app si `None`) |
| `timeout` | `45` | Segundos sin actividad para marcar agente idle |
| `discovery` | `"process"` | Cómo detectar agentes: `"process"` (psutil) o `"header"` (X-Agent-ID) |

```python
@app.proxy("openai")
class OpenAIProxy: ...
```

Sin `port`, corre en la misma app en `/proxy/`. El framework conoce los proveedores populares (OpenAI, Anthropic, etc.) y completa `upstream` automáticamente.

Campos por defecto si la clase está vacía: `agent_id`, `status`, `pid`, `cpu`, `mem_pct`, `window`, `last_active`.

---

### `@app.namespace`

Define el prefijo de ruta de una clase y sus hijas. No es un modelo — es un organizador de rutas.

| Parámetro | Default | Descripción |
|---|---|---|
| (primer arg) | nombre de clase en minúscula | Prefijo de ruta |

```python
@app.namespace("perro")          # ruta /perro/
class Api: ...

@app.namespace                   # ruta /api/
class Api: ...
```

Los hijos heredan el namespace del padre. Pueden overridearlo con su propio `@app.namespace`.

---

## Tabla resumen

| Decorador | Parámetro principal | Defaults | UI generada |
|---|---|---|---|
| `@app.model` | — | `name`, `description` | CRUD completo |
| `@app.run` | campo | — | Botón ▶ |
| `@app.system` | fuente (`"process"`, etc.) | según fuente | Tabla auto-refresh, ✕ opcional |
| `@app.log` | — | `source`, `level`, `content`, `time` | Tabla solo lectura |
| `@app.proxy` | nombre del proxy | `agent_id`, `status`, etc. | Proxy + modelos anidados |
| `@app.namespace` | nombre de ruta | nombre de clase | — |

## Infraestructura adicional

### Registry de proveedores conocidos

El framework mantiene una tabla interna que mapea nombres de clase a configuraciones:

| Nombre de clase | `upstream` detectado | `api_key_env` |
|---|---|---|
| `OpenAI` | `https://api.openai.com` | `OPENAI_API_KEY` |
| `Anthropic` | `https://api.anthropic.com` | `ANTHROPIC_API_KEY` |
| `OpenCode` | `https://opencode.ai/go/v1` | `OPENCODE_API_KEY` |

Se puede overridear: `@app.proxy(upstream="https://..."")`.

### Templates (marketplace)

Repositorio de plantillas de modelos que se aplican con:

```bash
nimbo apply blog           # agrega User, Post, Comment
nimbo apply monitor        # agrega Process, Mount, Connection
```

Cada template es código Python explícito que se copia al proyecto.

---

## Preguntas abiertas

- Los campos por defecto de `@app.model` son genéricos. ¿Tiene sentido que varíen según el nombre de la clase? (ej: `class Contact:` → `name`, `email`, `phone`)
- ¿`@app.system("mounts")` debería autodetectar el campo `id` o el usuario debe definirlo?
- ¿El registry de proveedores debería ser extensible por el usuario?
