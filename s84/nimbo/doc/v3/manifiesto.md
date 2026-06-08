# nimbo v3 — Manifiesto de diseño

> Documento único. Fuente única de verdad para v3.
> v3 extiende y completa el proxy como plataforma de gestión de agentes.

---

## Índice

1. [Filosofía](#1-filosofía)
2. [Proxy v3 — Visión general](#2-proxy-v3--visión-general)
   - [API key — no es obligatoria](#23-api-key--no-es-obligatoria)
3. [Agente como recurso CRUD](#3-agente-como-recurso-crud)
4. [Ciclo de vida del agente](#4-ciclo-de-vida-del-agente)
5. [Asignación de tareas](#5-asignación-de-tareas)
6. [Métricas de eficiencia y eficacia](#6-métricas-de-eficiencia-y-eficacia)
7. [Control de agentes](#7-control-de-agentes)
8. [Directions](#8-directions)
9. [Dashboard de monitoreo](#9-dashboard-de-monitoreo)
10. [Contratos de API v3](#10-contratos-de-api-v3)
11. [Registro de decisiones v3](#11-registro-de-decisiones-v3)

---

## 1. Filosofía

El proxy en v2 era un **reverse pasivo**: interceptaba peticiones, las reenviaba a un upstream LLM, y exponía una lista plana de agentes descubiertos.

v3 convierte el proxy en un **sistema activo de gestión de agentes**. Cada agente es un recurso CRUD completo: se puede inspeccionar, controlar, medir, y asignar. El proxy ya no solo reenvía tráfico — **gestiona el ciclo de vida completo del agente**.

Principios rectores:

- **El agente es el centro.** Todo gira en torno a qué está haciendo, cómo lo está haciendo, y si se le puede pedir algo más.
- **CRUD universal.** Las mismas operaciones que aplican a un `Contact` aplican a un `Agent`. Listar, leer, crear, actualizar, eliminar — más acciones específicas (iniciar, pausar, matar).
- **Medible por diseño.** Cada agente expone métricas de eficiencia y eficacia sin configuración extra.
- **Control explícito.** No hay magia: iniciar, pausar, reasignar y matar son endpoints explícitos.

---

## 2. Proxy v3 — Visión general

```python
from nimbo import App
app = App(__name__)

@app.proxy
class OpenAI: ...

app.serve()
```

**Qué genera v3 (vs v2):**

| Aspecto | v2 | v3 |
|---|---|---|---|
| Agentes | Lista plana, solo lectura | CRUD completo + acciones |
| Estado | `active` / `idle` | `discovered` / `active` / `standby` / `error` |
| Tarea | No disponible | Asignación explícita por agente |
| Métricas | Solo CPU/mem | Eficiencia, eficacia, tasa de éxito, tiempo promedio |
| Dirección | No disponible | Asignable y reasignable por agente |
| Control | Matar proceso (✕) | Iniciar, pausar, reasignar, cancelar direction, matar |
| Monitoreo | Tabla con auto-refresh | Dashboard con métricas en vivo |

### 2.1 Modelo mental

```
 ┌─────────────────────────────────────┐
 │            Proxy v3                  │
 │                                      │
 │  ┌──────────┐   ┌──────────┐        │
 │  │ Agent A  │   │ Agent B  │        │
 │  │ status   │   │ status   │        │
 │  │ task_id  │   │ task_id  │        │
 │  │ eff%     │   │ eff%     │        │
 │  │ dir      │   │ dir      │        │
 │  │ ...      │   │ ...      │        │
 │  └────┬─────┘   └────┬─────┘        │
 │       │              │              │
 │  ┌────▼──────────────▼──────────┐   │
 │  │   PUT /agent/{id} · DELETE   │   │
 │  │   GET /agent/{id} · CRUD     │   │
 │  └──────────────────────────────┘   │
 │       │              │              │
 │  ┌────▼──────────────▼──────────┐   │
 │  │    Upstream LLM (OpenAI)     │   │
 │  └──────────────────────────────┘   │
 └─────────────────────────────────────┘
```

### 2.2 Configuración del decorador

```python
@app.proxy(
    port=None,          # Puerto separado (None = misma app)
    upstream=None,      # URL del proveedor (infiere del nombre)
    api_key=None,       # API key literal
    api_key_env=None,   # Variable de entorno con API key
    discovery=None,     # Función de descubrimiento
)
class OpenAI: ...
```

| Parámetro | Default | Descripción |
|---|---|---|
| `port` | `None` | Puerto separado para el proxy |
| `upstream` | inferido del nombre | URL base del proveedor LLM |
| `api_key` | `None` | API key literal (ver sección 2.3) |
| `api_key_env` | `None` | Variable de entorno con API key (ver sección 2.3) |
| `discovery` | función por defecto | Descubrimiento de agentes |

### 2.3 API key — no es obligatoria

La API key **nunca es obligatoria**. El proxy siempre intenta resolverla, y si no la encuentra, reenvía la petición sin `Authorization` — el upstream devolverá un error y ese error se propaga de vuelta al cliente.

**Cadena de resolución:**

```
1. api_key="sk-..."       → se usa directamente
2. api_key_env="VAR"      → se lee os.environ["VAR"]
3. (inferido del nombre)  → {NOMBRE_CLASE}_API_KEY (ej: OpenAI → OPENAI_API_KEY)
4. nada encontrado        → se envía la petición sin Authorization
```

| Escenario | Qué hace el proxy | Resultado |
|---|---|---|
| `api_key="sk-..."` | Inyecta `Authorization: Bearer sk-...` | Autenticación garantizada |
| `api_key_env="OPENAI_API_KEY"` y la variable existe | Inyecta `Authorization: Bearer {valor}` | Autenticación garantizada |
| Sin parámetros y `OPENAI_API_KEY` existe en el entorno | Inyecta `Authorization: Bearer {valor}` | Autenticación garantizada |
| Sin parámetros y ninguna variable de entorno existe | Reenvía sin `Authorization` | El upstream rechaza con 401/403 y el proxy devuelve ese error al cliente |

**Ejemplo: sin API key ni variable de entorno**

```python
@app.proxy
class OpenAI: ...
```

El proxy reenvía a `https://api.openai.com` sin `Authorization`. OpenAI responde `401 Unauthorized`. El proxy devuelve ese 401 al cliente tal cual.

**Ejemplo: con API key explícita**

```python
@app.proxy(api_key_env="OPENAI_API_KEY")
class OpenAI: ...
```

```python
@app.proxy(api_key="sk-real-key")
class OpenAI: ...
```

En ambos casos el proxy inyecta el header antes de reenviar al upstream.

---

## 3. Agente como recurso CRUD

Cada agente es un recurso completo con operaciones CRUD. El proxy expone los agentes en `/{provider}/agent`.

### 3.1 Schema del agente

```python
@app.proxy
class OpenAI:
    agent_id: str       # identificador único (ej: "python3-12345")
    status: str         # discovered | active | standby | error
    pid: int            # PID del proceso
    cpu: float          # uso de CPU (%)
    mem_pct: float      # uso de memoria (%)
    window: str         # nombre de ventana (tmux, terminal)
    last_active: float  # timestamp Unix de última actividad

    # v3 — nuevos campos
    task_id: str        # tarea actual ("" si ninguna)
    task_name: str      # nombre legible de la tarea
    efficiency: float   # eficiencia 0–100 (%)
    effectiveness: float # eficacia 0–100 (%)
    direction: str        # directriz o instrucción activa
    started_at: float   # timestamp de inicio de tarea actual
    requests_served: int # total de requests atendidos
    avg_response_time: float  # tiempo promedio de respuesta (ms)
    success_rate: float  # tasa de éxito 0–100 (%)
```

### 3.2 Campos por defecto (clase vacía)

Si la clase está vacía, v3 provee todos los campos anteriores. El usuario puede agregar campos extra:

```python
@app.proxy
class OpenAI:
    model: str          # modelo LLM que usa este agente
    provider_version: str  # versión del provider
```

### 3.3 Endpoints — CRUD estándar

El agente sigue el mismo patrón CRUD que cualquier modelo Nimbo. No hay endpoints especiales para tareas, directions o estado — todo se hace actualizando los campos del agente con `PUT`.

| Método | Ruta | Cuerpo | Descripción |
|---|---|---|---|
| `GET` | `/{provider}/agent` | — | Listar todos los agentes |
| `GET` | `/{provider}/agent/{id}` | — | Leer un agente completo (incluye tarea, métricas, direction) |
| `PUT` | `/{provider}/agent/{id}` | `{...}` | Actualizar cualquier campo del agente |
| `DELETE` | `/{provider}/agent/{id}` | — | Matar proceso del agente |

**Un solo endpoint de escritura: `PUT`.** Todo se expresa como campos:

| Para hacer esto... | ...haces este PUT |
|---|---|
| Asignar tarea | `PUT /agent/X` `{"task_id":"t-01","task_name":"..."}` |
| Cancelar tarea | `PUT /agent/X` `{"task_id":"","task_name":""}` |
| Poner en espera | `PUT /agent/X` `{"status":"standby"}` |
| Reanudar | `PUT /agent/X` `{"status":"active"}` |
| Cambiar direction | `PUT /agent/X` `{"direction":"priorizar usuario vip-42"}` |
| Cancelar direction | `PUT /agent/X` `{"direction":""}` |
| Actualizar métricas | `PUT /agent/X` `{"efficiency":95,"effectiveness":98}` |

### 3.4 Ejemplo: listar agentes

```http
GET /openai/agent
```

```json
[
  {
    "agent_id": "opencode-12345",
    "status": "active",
    "pid": 12345,
    "cpu": 12.5,
    "mem_pct": 8.3,
    "window": "tmux: dev-session",
    "task_id": "t-001",
    "task_name": "Generar respuesta usuario #42",
    "efficiency": 94.2,
    "effectiveness": 98.7,
    "direction": "priorizar respuestas del usuario vip-42",
    "started_at": 1717891234.0,
    "requests_served": 156,
    "avg_response_time": 2340,
    "success_rate": 97.4,
    "last_active": 1717891834.0
  }
]
```

### 3.5 Ejemplo: leer un agente

```http
GET /openai/agent/opencode-12345
```

---

## 4. Ciclo de vida del agente

### 4.1 Diagrama de estados

```
                     ┌──────────┐
                     │discovered│ ← psutil descubre proceso
                     └────┬─────┘
                          │ primera actividad o asignación de tarea
                     ┌────▼─────┐
            ┌────────│  active  │────────┐
            │        └────┬─────┘        │
       reasignar          │         poner en
       tarea              │          espera
            │        ┌────▼──────┐       │
            └────────│  standby  │───────┘
                     └────┬──────┘
                          │ reanudar
                          └─────────► active


                     ┌────▼──────┐
                     │   error   │ ← proceso muerto / no responde
                     └───────────┘
                          │ re-descubrimiento
                          └─────────► discovered
```

| Estado | Significado | Transiciones |
|---|---|---|
| `discovered` | Proceso encontrado por psutil, aún sin actividad | → active (primera petición o asignación de tarea) |
| `active` | Procesando peticiones activamente | → standby (manual), → error (proceso muere) |
| `standby` | Puesto en espera manualmente | → active (reanudar) |
| `error` | Falló, no responde, proceso muerto | → discovered (re-descubrimiento automático) |

**No hay transiciones automáticas a standby.** La única forma de entrar en standby es por decisión explícita del administrador. Mientras el proceso esté vivo, el agente permanece en active.

### 4.2 Ejemplo: ciclo completo

```python
# Agente descubierto → "discovered"
# Al recibir primera petición → "active"
# Administrador lo pone en standby → "standby"
# Administrador lo reanuda → "active"
# Proceso muere → "error"
# Redescubierto por psutil → "discovered"
# Administrador mata el proceso → eliminado del registro
```

---

## 5. Asignación de tareas

### 5.1 Concepto

Cada agente puede tener una **tarea activa**. La tarea es lo que el agente está haciendo en este momento. No es el comando shell — es la **razón de su existencia actual**: "generar traducción", "procesar lote #42", "monitorear endpoint X".

La tarea se asigna simplemente actualizando los campos `task_id` y `task_name` del agente vía `PUT`. No hay un endpoint separado para tareas.

### 5.2 Asignar tarea

```http
PUT /openai/agent/opencode-12345
Content-Type: application/json

{
  "task_id": "t-001",
  "task_name": "Generar respuesta usuario #42"
}
```

| Campo | Descripción |
|---|---|
| `task_id` | Identificador único de la tarea |
| `task_name` | Nombre legible |

**Respuesta:** el agente completo con los campos actualizados:

```json
{
  "agent_id": "opencode-12345",
  "status": "active",
  "task_id": "t-001",
  "task_name": "Generar respuesta usuario #42",
  "started_at": 1717891234.0,
  ...
}
```

### 5.3 Consultar tarea actual

```http
GET /openai/agent/opencode-12345
```

El agente completo incluye `task_id`, `task_name`, `started_at` y `progress_pct`. No hay endpoint separado.

### 5.4 Cancelar tarea

```http
PUT /openai/agent/opencode-12345
Content-Type: application/json

{
  "task_id": "",
  "task_name": ""
}
```

### 5.5 Listar tareas activas

```http
GET /openai/agent
```

```http
GET /openai/agent?where=task_id%3D*&select=agent_id,task_name,status
```

---

## 6. Métricas de eficiencia y eficacia

### 6.1 Eficiencia

Mide **cómo usa el agente sus recursos** para completar tareas:

```
efficiency = (tiempo_ideal / tiempo_real) × 100
```

Donde `tiempo_ideal` es el tiempo estimado para la tarea (promedio histórico o baseline del sistema).

| Rango | Interpretación |
|---|---|
| 90–100 | Óptimo |
| 70–89 | Aceptable |
| 50–69 | Regular |
| < 50 | Crítico — requiere revisión |

### 6.2 Eficacia

Mide **calidad del resultado** del agente:

```
effectiveness = (tareas_exitosas / tareas_totales) × 100
```

Donde `tareas_exitosas` son las que completaron sin error y cumplieron criterios de calidad.

| Rango | Interpretación |
|---|---|
| 95–100 | Excelente |
| 80–94 | Bueno |
| 60–79 | Regular |
| < 60 | Requiere intervención |

### 6.3 Métricas automáticas por agente

| Métrica | Cálculo | Actualización |
|---|---|---|
| `efficiency` | Tiempo ideal / tiempo real | Por tarea completada |
| `effectiveness` | Éxitos / totales | Por tarea completada |
| `requests_served` | Contador | Por cada request proxy |
| `avg_response_time` | Media móvil | Por cada request proxy |
| `success_rate` | 200s / total requests | Por cada request proxy |

### 6.4 Ejemplo: dashboard de métricas

```http
GET /openai/metrics
```

```json
{
  "provider": "openai",
  "total_agents": 4,
  "active_agents": 2,
  "standby_agents": 1,
  "error_agents": 1,
  "global_efficiency": 87.3,
  "global_effectiveness": 94.1,
  "total_requests": 4582,
  "avg_response_time_ms": 2150,
  "global_success_rate": 96.8,
  "agents": [
    {
      "agent_id": "opencode-12345",
      "efficiency": 94.2,
      "effectiveness": 98.7,
      "requests_served": 156,
      "avg_response_time_ms": 2340,
      "success_rate": 97.4
    }
  ]
}
```

### 6.5 Histórico de métricas

```http
GET /openai/metrics/history?period=24h
```

Devuelve series temporales de eficiencia, eficacia y tasa de éxito agregadas por hora.

---

## 7. Control de agentes

### 7.1 Control vía CRUD estándar

Todo el control del agente se hace con los mismos dos endpoints. No hay acciones especiales:

| Operación | Cómo se hace | Efecto |
|---|---|---|
| Poner en espera | `PUT /agent/X` `{"status":"standby"}` | El agente deja de recibir peticiones |
| Reanudar | `PUT /agent/X` `{"status":"active"}` | Vuelve a recibir peticiones |
| Asignar direction | `PUT /agent/X` `{"direction":"..."}` | Asigna una directriz al agente |
| Cancelar direction | `PUT /agent/X` `{"direction":""}` | Limpia la directriz activa |
| Asignar tarea | `PUT /agent/X` `{"task_id":"t-01"}` | Asigna tarea activa |
| Cancelar tarea | `PUT /agent/X` `{"task_id":""}` | Limpia la tarea |
| Matar proceso | `DELETE /agent/X` | Elimina el agente |

### 7.2 Matar proceso

```http
DELETE /openai/agent/opencode-12345
```

```json
{
  "ok": true,
  "agent_id": "opencode-12345",
  "pid": 12345,
  "terminated": true
}
```

El proxy intenta `SIGTERM`. Si el proceso no muere en 5s, envía `SIGKILL`.

### 7.3 Poner en espera (standby)

```http
PUT /openai/agent/opencode-12345
Content-Type: application/json

{
  "status": "standby"
}
```

```json
{
  "agent_id": "opencode-12345",
  "status": "standby",
  "task_id": "t-001",
  "efficiency": 94.2,
  ...
}
```

El agente deja de recibir nuevas peticiones proxy. Para reanudarlo:

```http
PUT /openai/agent/opencode-12345
Content-Type: application/json

{
  "status": "active"
}
```

### 7.4 Acciones personalizadas via `@app.action`

El usuario puede agregar acciones propias que escriben campos del agente:

```python
@app.proxy
class OpenAI:
    @app.action("restart")
    def restart_agent(self, item):
        import os, signal
        pid = item["pid"]
        os.kill(pid, signal.SIGTERM)
        item["status"] = "standby"
        return item

    @app.action("backup")
    def backup_logs(self, item):
        item["last_backup"] = __import__("time").time()
        return item
```

| Parámetro | Default | Descripción |
|---|---|---|
| `name` | nombre del método | Identificador de la acción (ruta y etiqueta) |

**Genera:** botón en la UI y endpoint `POST /{provider}/agent/{action}/{agent_id}`. La acción recibe el agente, lo modifica, y el framework persiste los cambios.

---

## 8. Directions

### 8.1 Concepto

Una **direction** es una instrucción o directriz que se le da al agente sobre cómo operar: un objetivo específico, un comportamiento a seguir, o un parámetro de configuración temporal. A diferencia del par `task_id`/`task_name` (qué hacer), `direction` indica el cómo o hacia dónde orientar el esfuerzo. Es simplemente un campo más del agente. Se lee con `GET` y se escribe con `PUT`.

### 8.2 Asignar direction

```http
PUT /openai/agent/opencode-12345
Content-Type: application/json

{
  "direction": "priorizar respuestas del usuario vip-42"
}
```

### 8.3 Leer direction actual

```http
GET /openai/agent/opencode-12345
```

El campo `direction` viene incluido en el agente junto con el resto de campos.

### 8.4 Cancelar direction

```http
PUT /openai/agent/opencode-12345
Content-Type: application/json

{
  "direction": ""
}
```

### 8.5 Múltiples directions

Si un agente necesita varias instrucciones simultáneas, se usa `directions` (lista de strings):

```http
PUT /openai/agent/opencode-12345
Content-Type: application/json

{
  "directions": ["priorizar usuario vip-42", "usar modelo gpt-4", "responder en español"]
}
```

---

## 9. Tabla de agentes

### 9.1 Vista de tabla

v3 muestra los agentes en la misma tabla CRUD que cualquier otro modelo Nimbo. No hay tarjetas ni página de detalle — la tabla es la interfaz universal.

La diferencia con v2 es que el usuario puede **elegir qué columnas ver**, tal como SQL permite seleccionar campos:

```http
GET /openai/agent?select=agent_id,status,task_name,efficiency,direction,cpu,mem_pct
```

| Parámetro | Ejemplo | Descripción |
|---|---|---|
| `?select=` | `?select=agent_id,status,efficiency` | Columnas a devolver (SQL `SELECT`). Por defecto se devuelven todas |

### 9.2 Configuración de columnas

El schema del modelo proxy define qué columnas están disponibles. El frontend las muestra como columnas de la tabla:

```json
{
  "openai": {
    "api": "/openai/agent",
    "id": "agent_id",
    "refresh": 5000,
    "noCreate": true,
    "kill": true,
    "fields": [
      {"name": "agent_id", "type": "string"},
      {"name": "status", "type": "string"},
      {"name": "task_name", "type": "string", "label": "Tarea"},
      {"name": "efficiency", "type": "float", "label": "Eff%" },
      {"name": "effectiveness", "type": "float", "label": "Efic%" },
      {"name": "direction", "type": "string"},
      {"name": "cpu", "type": "float", "label": "CPU%"},
      {"name": "mem_pct", "type": "float", "label": "MEM%"}
    ]
  }
}
```

### 9.3 Acciones por fila

Cada fila del agente tiene botones de acción. Los botones se definen por campo (como SQL permite seleccionar columnas, el framework permite elegir qué acciones son relevantes):

| Botón | Acción | Endpoint |
|---|---|---|
| ✕ | Matar proceso | `DELETE /{provider}/agent/{id}` |
| ✎ | Editar campos | `PUT /{provider}/agent/{id}` |
| Acciones custom | Según `@app.action` | `POST /{provider}/agent/{action}/{id}` |

No hay botones específicos para "iniciar", "pausar" o "reanudar" — esas son operaciones de escritura que se hacen vía `PUT` modificando el campo `status`.

---

## 10. Contratos de API v3

### 10.1 Nuevos endpoints

| Método | Ruta | v3 Descripción |
|---|---|---|
| `GET` | `/{provider}/agent` | Listar agentes |
| `GET` | `/{provider}/agent/{id}` | Leer un agente (incluye tarea, direction, métricas) |
| `PUT` | `/{provider}/agent/{id}` | Actualizar cualquier campo del agente |
| `DELETE` | `/{provider}/agent/{id}` | Matar proceso |
| `GET` | `/{provider}/metrics` | Métricas globales del provider |
| `GET` | `/{provider}/metrics/history` | Histórico de métricas |

### 10.2 Parámetros de consulta — convención SQL

Todos los endpoints `GET /{provider}/agent` aceptan parámetros que imitan cláusulas SQL:

| Parámetro | SQL equivalente | Ejemplo |
|---|---|---|
| `?select=col1,col2` | `SELECT col1, col2` | `?select=agent_id,status,efficiency` |
| `?where=col=val` | `WHERE col = val` | `?where=status=active` |
| `?order_by=col` | `ORDER BY col` | `?order_by=efficiency desc` |
| `?limit=N` | `LIMIT N` | `?limit=50` |
| `?offset=N` | `OFFSET N` | `?offset=100` |

```http
GET /openai/agent?select=agent_id,status,task_name,efficiency&where=status=active&order_by=efficiency desc&limit=10
```

Se puede combinar `?select` con múltiples condiciones en `?where`:

```http
GET /openai/agent?where=status=active,task_id=%2A&order_by=cpu desc
```

### 10.3 Extensiones al esquema de configuración

```json
{
  "openai": {
    "api": "/openai/agent",
    "id": "agent_id",
    "refresh": 5000,
    "noCreate": true,
    "kill": true,
    "fields": [
      {"name": "agent_id", "type": "string"},
      {"name": "status", "type": "string"},
      {"name": "task_name", "type": "string", "label": "Tarea"},
      {"name": "efficiency", "type": "float", "label": "Eff%" },
      {"name": "effectiveness", "type": "float", "label": "Efic%" },
      {"name": "direction", "type": "string"},
      {"name": "cpu", "type": "float", "label": "CPU%"},
      {"name": "mem_pct", "type": "float", "label": "MEM%"}
    ]
  }
}
```

| Campo nuevo | Obligatorio | Default | Descripción |
|---|---|---|---|
| `metrics_api` | no | `"/{provider}/metrics"` | Endpoint de métricas globales |

### 10.3 Formato de agente (schema extendido)

```json
{
  "name": "agent_id",
  "type": "string"
}
```

Nuevos tipos de campo para v3:

| Tipo | Control HTML | Uso |
|---|---|---|
| `progress` | Barra de progreso visual | `progress_pct` de tarea |
| `metric` | Indicador numérico con color según rango | `efficiency`, `effectiveness` |
| `status` | Badge de color según estado | `status` del agente |
| `direction` | Enlace clickeable | `direction` del agente |

---

## 11. Registro de decisiones v3

Decisiones explícitas de v3 que resuelven limitaciones de v2:

| # | Decisión | Resuelve |
|---|---|---|
| 1 | El agente es un recurso CRUD completo con GET/POST/PUT/DELETE | v2 solo exponía lista plana de solo lectura |
| 2 | `status` tiene 4 estados: discovered, active, standby, error. No hay idle automático | v2 solo tenía active/idle, sin standby ni error |
| 3 | Toda acción de control tiene endpoint explícito: start, standby, resume, kill | v2 solo tenía DELETE para matar, sin ciclo de vida |
| 4 | La direction del agente se modela como campo de texto actualizable vía PUT | v2 no contemplaba directions o instrucciones |
| 5 | Las métricas de eficiencia y eficacia se calculan automáticamente por tarea | v2 solo exponía CPU/mem, sin métricas de rendimiento |
| 6 | `task_id` y `task_name` son campos nativos del agente | v2 no tenía concepto de tarea activa |
| 7 | El dashboard tiene vista `grid` (tarjetas) además de `table` | v2 solo tenía tabla, sin diferenciación visual por estado |
| 8 | No existe transición automática a standby. Solo standby manual explícito | v2 tenía timeout fijo de 120s para marcar idle |
| 9 | `@app.action` dentro de proxy permite acciones custom por agente | v2 solo tenía acciones globales del modelo |

---

## Apéndice A: Mapa de ruta v2 → v3

| v2 | v3 |
|---|---|
| `@app.proxy` con lista plana de agentes | `@app.proxy` con CRUD + métricas + control |
| `GET /{provider}` lista agentes | `GET /{provider}/agent` lista agentes |
| Agente: agent_id, status, pid, cpu, mem_pct, window, last_active | Agente extendido: +task_id, task_name, efficiency, effectiveness, direction, started_at, requests_served, avg_response_time, success_rate |
| Status: active, idle | Status: discovered, active, standby, error |
| DELETE /{provider}/{id} mata proceso | DELETE /{provider}/agent/{id} mata proceso |
| — | PUT /{provider}/agent/{id} actualiza cualquier campo (status, direction, task) |
| — | GET /{provider}/metrics métricas globales |
| Auto-logging de requests | + Métricas de eficiencia/eficacia por tarea |

---

## Apéndice B: Ejemplo completo — Proxy v3

```python
from nimbo import App

app = App(__name__)

@app.proxy
class OpenAI:
    pass

@app.proxy(port=9099)
class Anthropic:
    pass

@app.log
class AuditLog: ...

app.serve()
```

**Genera v3:**
- `GET /openai/agent` — lista agentes OpenAI con métricas
- `POST /openai/agent/{id}/task` — asigna tarea a agente
- `PUT /openai/agent/{id}` — actualiza cualquier campo del agente
- `DELETE /openai/agent/{id}` — mata proceso del agente
- `POST /openai/agent/{id}/standby` — pone en espera
- `POST /openai/agent/{id}/resume` — reanuda
- `GET /openai/metrics` — métricas globales del proxy
- `GET /openai/task` — tareas activas de todos los agentes
- Todo lo anterior también en puerto 9099 para Anthropic
- Log de auditoría de todas las acciones
