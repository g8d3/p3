# Filosofía de decoradores — nimbo

## Principio

Cada decorador sobre una clase expresa **la naturaleza del modelo** — qué es, de dónde vienen sus datos, qué se puede hacer con él.

No hay lógica procedural en la app. Solo declaración de intenciones.

## Decoradores actuales

| Decorador | Significado | Datos | CRUD | UI generada |
|---|---|---|---|---|
| `@app.model` | Tabla en DB | SQLite (persistente) | crear, leer, actualizar, borrar | Tabla estándar con ±✎✕ |
| `@app.run("campo")` | Tiene campo ejecutable | mismo que el modelo padre | + ejecutar | Botón ▶ |
| `@app.system` | Recurso vivo del sistema | API externa (psutil, etc.) | solo lectura, auto-refresh | Tabla sin crear/editar/borrar |
| `@app.log` | Registro de auditoría | DB (auto-poblado) | solo lectura, auto-refresh | Tabla sin crear/editar/borrar |

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

Modelo virtual ─── @app.system ─── datos vivos del SO, solo lectura
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
