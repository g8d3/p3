# Multiplicidad y anidación de decoradores

## Problema

Hoy los decoradores son planos y singulares:

```python
@app.model        # Un solo modelo
@app.system       # Un solo sistema
@app.log          # Un solo log
@app.proxy        # Un solo proxy
```

No puedes definir **dos proxies** (OpenAI + Anthropic), ni **dos modelos anidados** (Proxy → Request, Proxy → TokenUsage), ni **dos fuentes de sistema** (procesos + monturas de disco).

## Solución: decoradores con nombre y anidación

### Decoradores con nombre

Cada decorador puede recibir un nombre como primer argumento. Ese nombre se usa en rutas y URLs:

```python
@app.proxy("openai", upstream="https://api.openai.com", port=9098)
class OpenAIProxy:
    ...

@app.proxy("anthropic", upstream="https://api.anthropic.com", port=9099)
class AnthropicProxy:
    ...
```

Esto genera rutas como:
- `GET /api/openai-proxy` (lista agentes del proxy OpenAI)
- `GET /api/anthropic-proxy` (lista agentes del proxy Anthropic)

### Modelos anidados

Un modelo puede contener otros modelos. El hijo hereda el contexto del padre:

```python
@app.proxy("openai", upstream="https://api.openai.com", port=9098)
class OpenAIProxy:
    agent_id: str
    status: str

    @app.model
    class Request:
        prompt: str
        response: str
        tokens: int
        duration_ms: float

    @app.model
    class TokenUsage:
        model: str
        prompt_tokens: int
        completion_tokens: int
```

Esto genera rutas anidadas:
- `GET /api/openai-proxy` — agentes del proxy
- `GET /api/openai-proxy/request` — requests de ese proxy
- `GET /api/openai-proxy/token-usage` — uso de tokens de ese proxy
- `POST /api/openai-proxy/request` — crear request (se envía al upstream automáticamente)

La ruta se construye como: `/{nombre-padre}/{nombre-hijo}`.

### Multiplicidad en otros decoradores

```python
@app.system("processes", api="/api/process", id="pid")
class Process:
    pid: int
    name: str

@app.system("mounts", api="/api/mounts", kill=False)
class Mount:
    device: str
    mount: str
    usage: float

@app.log("audit")
class AuditLog:
    ...

@app.log("proxy-events")
class ProxyEvent:
    ...
```

## Reglas de anidación

1. **Un padre puede tener múltiples hijos.** No hay límite de profundidad.
2. **Los hijos heredan el prefijo de ruta del padre.** Ej: `openai-proxy/request`.
3. **Los hijos heredan la base de datos del padre** (si el padre tiene DB, los hijos usan la misma).
4. **Un hijo puede tener sus propios decoradores.** Ej: `@app.model` dentro de `@app.proxy` puede tener `@app.run`.
5. **Los decoradores sin nombre usan el nombre de la clase en minúscula** (como ahora).

## Implementación

### Registro de modelos

En lugar de una lista plana `_model_schema`, se usa un árbol:

```python
_model_tree = {
    "openai-proxy": {
        "cls": OpenAIProxy,
        "children": {
            "request": {"cls": Request, "fields": [...]},
            "token-usage": {"cls": TokenUsage, "fields": [...]},
        }
    },
    "process": {
        "cls": Process,
        "children": {}
    },
    "audit": {
        "cls": AuditLog,
        "children": {}
    }
}
```

### Generación de rutas

Al registrar un modelo anidado, la ruta se construye recursivamente:

```python
def register_model(self, cls, parent_name=None, name=None):
    model_name = name or cls.__name__.lower()
    full_name = f"{parent_name}/{model_name}" if parent_name else model_name
    # Registrar schema en /api/{full_name}/schema
    # Registrar CRUD en /api/{full_name}
    # Si tiene hijos, registrarlos recursivamente
```

### Namespaces en la UI

La navegación del frontend se adapta para mostrar nombres compuestos:

```
openai-proxy
  └── request
  └── token-usage
anthropic-proxy
  └── request
  └── token-usage
process
audit
proxy-events
```

## Preguntas abiertas

1. **¿Hasta qué profundidad de anidación es útil?** 2 niveles (padre → hijo) parece suficiente. ¿3?
2. **¿Cómo se manejan las relaciones entre modelos anidados?** ¿El hijo tiene automáticamente una FK al padre?
3. **¿Los decoradores sin nombre (`@app.model`) pueden ser hijos?** ¿O solo los decoradores con nombre pueden ser padres?
4. **¿Cómo se refleja la anidación en `__NIMBO_CONFIGS__`?** ¿Los hijos heredan configs del padre?
5. **¿Debe existir `@app.namespace("nombre")` como decorador contenedor sin comportamiento propio?**

## Relación con `fields`

Cada decorador acepta `fields` para mapear conceptos a columnas del modelo:

```python
@app.system("processes", fields={"id": "pid", "status": "status", "cpu": "cpu_percent"})
class Process:
    pid: int
    name: str
    cpu_percent: float
    ...
```

`fields` es un parámetro estándar que TODO decorador debe soportar.
