# Filosofía de decoradores — nimbo

## Principio

Cada decorador sobre una clase expresa **la naturaleza del modelo** — qué es, de dónde vienen sus datos, qué se puede hacer con él.

No hay lógica procedural en la app. Solo declaración de intenciones.

## Decoradores actuales

### `@app.model`

Registra el modelo como tabla en base de datos con CRUD completo.

```python
@app.model
class Producto:
    nombre: str
    precio: float = 0
```

Genera: `GET/POST /api/producto`, `GET/PUT/DELETE /api/producto/<id>`, schema endpoint, y tabla CRUD en el navegador.

Sin parámetros adicionales. Todo se deduce de las anotaciones de tipo de la clase.

---

### `@app.run("campo", ...)`

**Requiere**: `@app.model` (no tiene sentido solo).

Marca un campo como ejecutable (comando shell). Genera `POST /api/{modelo}/run/<id>`.

| Parámetro | Default | Descripción |
|---|---|---|
| `"campo"` | (requerido) | Nombre del campo que contiene el comando shell |
| `timeout` | `"timeout"` | Nombre del campo que contiene el timeout en segundos |

```python
@app.model
@app.run("shell", timeout="timeout")
class Command:
    shell: str = ""
    timeout: int = 30
```

El framework ejecuta `item["shell"]` vía `asyncio.create_subprocess_shell()` con el timeout de `item["timeout"]`.

---

### `@app.system`

Modelo virtual sin base de datos. Los datos vienen del sistema operativo vía API.

| Parámetro | Default | Descripción |
|---|---|---|
| `api` | `"/api/system/processes"` | Endpoint que provee los datos |
| `id` | `"pid"` | Campo usado como identificador único |
| `refresh` | `5` | Intervalo de auto-refresh en segundos |
| `kill` | `True` | Si tiene botón ✕ para matar el recurso |

```python
@app.system
class Process:
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    status: str

@app.system(kill=False)
class Mount:
    device: str
    mount: str
    fstype: str
    usage: float
```

El framework genera: schema endpoint, configuración de cliente con `noCreate`, `noEdit`, `auto-refresh`, y botón ✕ si `kill=True`. No crea tabla en DB.

---

### `@app.log`

Modelo de auditoría. Es una tabla en DB pero de solo lectura y auto-poblada por el framework.

Sin parámetros.

```python
@app.log
class Log:
    source: str
    level: str
    content: str
    time: str
```

El framework:
- Crea la tabla en DB
- Auto-escribe una entrada en cada CRUD (crear, actualizar, borrar) de cualquier otro modelo
- Auto-escribe en cada ejecución (`@app.run`)
- Genera configuración de cliente: solo lectura, auto-refresh 3s
- Mantiene un máximo de 200 registros (los más recientes)

---

## Tabla resumen

| Decorador | Parámetros | Datos | CRUD | UI generada |
|---|---|---|---|---|
| `@app.model` | — | DB | crear, leer, actualizar, borrar | Tabla estándar con ±✎✕ |
| `@app.run` | `campo`, `timeout` | DB (del modelo padre) | + ejecutar | Botón ▶ |
| `@app.system` | `api`, `id`, `refresh`, `kill` | API externa | solo lectura, auto-refresh | Tabla con ✕ (opcional) |
| `@app.log` | — | DB (auto-poblado) | solo lectura, auto-refresh | Tabla sin crear/editar/borrar |

## Reglas de diseño

1. **Un decorador = un aspecto ortogonal** del modelo. No mezclar conceptos.
   - `@app.model` dice "esto es persistente"
   - `@app.run` dice "esto se puede ejecutar"
   - Son independientes: un modelo puede ser `@app.model` sin `@app.run`, y viceversa (aunque `@app.run` sin modelo no tiene sentido práctico).

2. **Los decoradores se leen como lenguaje natural**:
   ```
   @app.model          → "Esto es un modelo de datos"
   @app.run("shell")   → "Esto tiene un shell ejecutable"
   @app.system         → "Esto es un recurso del sistema"
   @app.log            → "Esto es un registro de auditoría"
   ```

3. **No hay herencia de decoradores**. `@app.log` no es un subtipo de `@app.model` aunque compartan implementación. La semántica es diferente aunque el mecanismo interno sea similar.

4. **Configuración explícita > magia**. Los parámetros van en el decorador (`@app.run("shell", timeout="timeout")`), no en atributos mágicos de la clase.

## Decoradores futuros (candidatos)

| Decorador | Para qué | Ejemplo |
|---|---|---|
| `@app.export` | Campo descargable (archivo, reporte) | `@app.export("pdf")` |
| `@app.upload` | Campo que acepta subida de archivos | `@app.upload("avatar")` |
| `@app.secret` | Campo encriptado en DB | `@app.secret("password")` |
| `@app.graph` | Modelo que se renderiza como gráfico | `@app.graph("line")` |
| `@app.map` | Modelo con datos geoespaciales | `@app.map("lat", "lng")` |

No todos serán implementados. La lista es exploratoria.

## Relación entre conceptos

```
Modelo en DB  ─── @app.model ─── CRUD completo
                  │
                  ├── @app.run ─── + ejecutar comando
                  │
                  └── @app.log ─── solo lectura, auto-poblado

Modelo virtual ─── @app.system ─── datos vivos del SO
```

`@app.run` puede combinarse con cualquier decorador que defina un modelo:
- `@app.model` + `@app.run` → comando guardado en DB, ejecutable
- `@app.system` + `@app.run` → proceso del sistema ejecutable (futuro)
- `@app.log` + `@app.run` → no tendría sentido

## Preguntas abiertas

- ¿`@app.log` debería ser `@app.model` + `@app.audit` (combinación de dos decoradores)?
- ¿`@app.system` necesita su propio schema endpoint o puede reusar el de `@app.model`?
- ¿Debería existir `@app.model(log=True)` en vez de `@app.log` separado?
- ¿Los decoradores de comportamiento (`@app.run`) deberían aceptar múltiples campos?
- ¿Cómo se documentan los decoradores para que el desarrollador los descubra sin leer el código fuente del framework?
