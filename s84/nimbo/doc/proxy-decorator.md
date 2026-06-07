# Diseño: decorador `@app.proxy`

## Visión general

Convierte una clase en un proxy reverso que intercepta llamadas a un upstream,
trackea agentes AI, registra actividad, y expone todo vía CRUD automático.

```python
@app.proxy(
    upstream="https://api.openai.com",
    port=9098,
    prefix="/v1/",
    timeout=45,
)
class LLMProxy:
    agent_id: str      # identificador del agente (de window name o PID)
    status: str        # activo / idle / timeout
    pid: int           # PID del proceso
    cpu: float         # uso de CPU
    mem_pct: float     # uso de memoria
    window: str        # nombre de la ventana tmux
    last_active: float # timestamp última actividad
```

## Configuración del decorador

| Parámetro | Default | Descripción |
|---|---|---|
| `upstream` | (requerido) | URL base del proveedor LLM (ej: `https://api.openai.com`) |
| `port` | `9098` | Puerto donde escucha el proxy |
| `prefix` | `"/v1/"` | Prefijo de ruta a interceptar |
| `timeout` | `45` | Segundos sin actividad para marcar agente como idle |
| `discovery` | `"process"` | Método de descubrimiento de agentes: `"process"` (desde psutil filtrando por `tmux`/`opencode`) o `"header"` (desde `X-Agent-ID`) |
| `discovery_filter` | `"tmux"` | String para filtrar procesos (solo cuando `discovery="process"`) |
| `fields` | `{...}` | Mapeo explícito de campos del decorador a columnas del modelo (ver sección abajo) |

## Mapeo explícito de campos

Cada decorador debería poder definir qué campos del modelo corresponden a qué concepto.
Este es el patrón que falta en los decoradores actuales:

```python
@app.proxy(
    fields={
        "id": "agent_id",       # campo identificador
        "status": "status",      # campo de estado
        "pid": "pid",            # campo de proceso
        "cpu": "cpu",            # campo de CPU
        "memory": "mem_pct",     # campo de memoria
        "window": "window",      # campo de ventana tmux
        "last_active": "last_active",  # campo de última actividad
        "upstream_url": "_upstream",   # campo interno (con _)
    }
)
class LLMProxy:
    agent_id: str = ""
    status: str = "activo"
    pid: int = 0
    cpu: float = 0.0
    mem_pct: float = 0.0
    window: str = ""
    last_active: float = 0.0
    _upstream: str = ""  # campo interno, no se muestra en UI
```

## Comportamiento

### 1. Proxy reverso

El decorador inicia un servidor HTTP en `port` que:

1. Recibe petición del cliente (ej: `POST /v1/chat/completions`)
2. Reenvía al `upstream` (ej: `https://api.openai.com/v1/chat/completions`)
3. Devuelve la respuesta al cliente
4. Registra la llamada en el modelo `Log` automáticamente

### 2. Descubrimiento de agentes

Si `discovery="process"` (default):

1. Cada N segundos (configurable internamente), ejecuta `psutil.process_iter()`
2. Filtra procesos cuyo nombre contenga `discovery_filter` (ej: `"tmux"`, `"opencode"`)
3. Actualiza el modelo con los procesos encontrados:
   - Crea entradas nuevas para procesos no vistos antes
   - Actualiza CPU/memoria de los existentes
   - Marca como "idle" los que desaparecieron

Si `discovery="header"`:

1. Cada petición al proxy lleva un header `X-Agent-ID`
2. Si el header es nuevo, crea una entrada en el modelo
3. Actualiza `last_active` en cada petición

### 3. Detección de idle

- Cada N segundos, revisa todos los agentes
- Si `now - last_active > timeout`, marca `status = "idle"`
- Esto corre como tarea asyncio periódica

### 4. Auto-logging

- Cada petición proxy genera una entrada en el modelo `Log`
- Contiene: agente, método, ruta, status code, duración

## Integración con otros decoradores

```python
@app.proxy(upstream="https://api.openai.com")
@app.system  # o @app.model si se persisten agentes en DB
class Agent:
    ...
```

Si se combina con `@app.system`, los datos vienen del sistema (psutil).
Si se combina con `@app.model`, los datos se persisten en DB.

## Preguntas abiertas

1. ¿`discovery_filter` debería ser una lista o permitir regex?
2. ¿Cómo se maneja el rate limiting del upstream?
3. ¿El proxy debería soportar streaming (SSE desde el upstream)?
4. ¿Cómo se autentican los agentes contra el proxy?
5. ¿`fields` debería ser un parámetro estándar de TODOS los decoradores?
