# Aprendizajes y prácticas — nimbo

## Principios de construcción

### 1. Estimar antes de ejecutar

Cada tarea y cada comando debe tener una estimación explícita de duración.
Si un comando excede el tiempo estimado, el agente debe:

1. Detenerse y reportar: "excedió el tiempo estimado"
2. Diagnosticar: ¿está colgado? ¿falló silenciosamente? ¿necesita más tiempo?
3. Decidir: reintentar con más tiempo, abortar y notificar, o tomar una ruta alternativa

Esto aplica tanto a comandos de shell como a ciclos completos de implementación.

### 2. Iterar sobre planificar

No construir todo de una vez. Ciclo corto:

```
construir → probar → identificar carencia → volver al framework → repetir
```

Cada ciclo se enfoca en UNA mejora concreta y medible.

### 3. Preferir lo mínimo que funciona

Cada línea de framework se multiplica por cada app que use el framework.
Antes de agregar algo, preguntar: "¿esto ahorra más líneas de las que agrega?"

La métrica clave: **líneas necesarias para definir un CRUD**.
Actualmente: 4 líneas (`@app.model` + clase + atributos con tipo).

### 4. No reinventar lo que ya existe

| Situación | Lección |
|---|---|
| WebSocket nativo vs librería | La implementación nativa (0 deps) introdujo un bug sutil que no apareció hasta probar en el navegador. La librería `websockets` (15.0.1) funcionó de inmediato. |
| DB multi-engine | No reimplementar PostgreSQL — solo definir una interfaz y usar `asyncpg`/`psycopg`. |
| Browser APIs | No wrappear cada API del navegador — solo dar un mecanismo para exponerlas fácilmente. |

**Decisión correcta**: hacer el backend WebSocket intercambiable (`NIMBO_WS_BACKEND` / `ws_backend=`). Esto permite:
- Zero-deps por defecto (nativo)
- Poder cambiar a la librería si el nativo falla
- Comparar comportamiento y encontrar bugs

### 5. Propagación de errores (pendiente)

Actualmente:
- Errores del servidor → se ven en logs y se devuelven como JSON 500
- Errores del cliente (navegador) → no se ven en el servidor

**Patrón necesario**: que el framework capture errores del lado del cliente
(JS exceptions, WS disconnects, API errors) y los envíe al servidor
automáticamente, ya sea por WebSocket o por endpoint dedicado.

Esto permite al agente (o al desarrollador) diagnosticar problemas
del lado del navegador sin estar mirando la consola.

### 6. Nomenclatura de la interfaz

| Componente | Nombre actual | Alternativas |
|---|---|---|
| Barra superior | header | encabezado (es el `<header>` HTML5) |
| Barra de pestañas | nav / app-nav | navegación, tabs |
| Área de contenido | main / app-content | contenido, principal (es el `<main>` HTML5) |

### 7. Actualizaciones parciales vs totales

Problema detectado: `renderDashboard()` y `renderProcesses()` reemplazan
`innerHTML` completo, lo que causa:
- El scroll vuelve al inicio de la página
- Se pierde el estado de los inputs
- No se puede interactuar con elementos durante la actualización

**Práctica correcta**: actualizar solo los valores que cambian
(CPU%, RAM%, lista de procesos) en lugar de reemplazar todo el contenedor.
Usar patrones como:
- `element.textContent = nuevoValor` para valores individuales
- `element.replaceChild()` para filas de tablas
- O un mecanismo de binding simple en el framework

### 8. Hot-reload y ciclo de desarrollo

El hot-reload (proceso padre que observa archivos y reinicia al hijo) junto
con el auto-refresh del navegador (WebSocket livereload) permiten un ciclo
de desarrollo ágil:

```
editar archivo → guardar → (1s) → servidor reinicia → navegador recarga solo
```

Esto es fundamental porque el desarrollador (humano o AI) puede ver resultados
inmediatos sin intervención manual.
