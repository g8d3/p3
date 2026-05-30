# Testing + Framework — Integración Multi-Agente

**Contexto:** Este documento conecta la infraestructura de testing automatizado con los principios de framework extraídos de s71 (VoiceButtonApp) y aplicados en s72 (AI Video Studio). Es la pieza que permite que múltiples agentes (humanos + IA) trabajen en paralelo.

---

## 1. El Problema

Cuando un humano desarrolla con IA, el cuello de botella no es escribir código — es **ver lo que pasó**. Sin visibilidad estructurada:

- La IA no ve pantallas (sin visión)
- Los logs se pierden entre ventanas de terminal
- Los errores del browser no llegan al servidor
- No hay trazabilidad entre cambios y resultados

Cada iteración requiere que el humano describa manualmente lo que ve → la IA adivina → ciclo lento.

---

## 2. Principios de Framework

Extraídos de la experiencia en s71 + s72:

### A. Visibilidad Total

Toda capa del sistema debe exponer su estado de forma que una IA pueda leerlo sin intervención humana.

```
Servidor → API REST con estado (cola, acciones, estilo, errores)
Browser  → Console logs accesibles vía CDP + modo dev con errores al servidor
Testing  → agent-browser vía CDP para snapshot del árbol de accesibilidad
Sistema  → tmux capture-pane para ver ventanas del desarrollador
```

**Implementado en s72:**
- `GET /api/actions` — historial completo de eventos del servidor
- `GET /api/status` — estado de cola, archivos, caches
- `GET /api/dev/errors` — errores del browser subidos al servidor
- `GET /api/style` — configuración actual
- `?dev=1` en composer — console.log visible + errores detallados

### B. Configuración sobre Código

Los cambios de comportamiento no deberían requerir recompilación. Idealmente ni siquiera reinicio.

```
config.json (YAML/JSON)  →  Runtime lo lee en caliente  →  Cambio inmediato
```

**Implementado en s72:**
- `POST /api/style` — cambiar voz, fuente, volumen música sin reiniciar
- `POST /api/config` — cambiar API keys y fuentes en caliente
- Valores default en `config.py` pero overrideable vía API

**Pendiente:** mover a archivo YAML externo con hot-reload (como en s71).

### C. Ciclo Corto

El feedback loop entre "hago un cambio" y "veo el resultado" debe ser < 10 segundos.

```
Antes:  código → esperar build → deploy manual → probar → reportar = minutos
Ahora:  código → agent-browser snapshot → test harness → reporte = segundos
```

**Implementado:**
- `test-reports/harness.py` — suite completa en < 30s
- `agent-browser snapshot` — inspección de UI en 1s
- Watchdog detecta cambios en window 0 y corre tests automáticamente

### D. Commits Pequeños y Frecuentes

El habilitador del trabajo multi-agente. Cada commit debe:

1. Hacer una sola cosa (feature, fix, refactor, doc)
2. Tener un mensaje claro del *por qué* (no del *qué*)
3. Incluir o actualizar tests cuando aplique

**Por qué es crítico para multi-agente:**
- `git diff HEAD~1` le dice a un agente exactamente qué cambió
- Si un agente rompe algo, otro agente puede revertir el cambio exacto
- Los reportes de test pueden referenciar commits: "el commit abc123 rompió X"
- Sin commits, los agentes tienen que comparar árboles de archivos completos

---

## 3. Infraestructura de Testing

### test-reports/harness.py

Suite de tests automatizados que verifica:

| Test | Qué prueba | Tiempo |
|------|-----------|--------|
| `api` | Todos los endpoints REST (queue, style, sources, assets, etc.) | 5s |
| `feed` | Ciclo completo: pop package, verificar estructura, download | 15s |
| `assets` | Todos los assets descargables (gameplay, audio) | 10s |

Uso:
```bash
python3.12 test-reports/harness.py              # todo
python3.12 test-reports/harness.py --test api   # solo API
```

### test-reports/watch.sh

Watchdog que monitorea la ventana 0 del desarrollador. Cuando detecta cambios (nuevo output en tmux), corre la suite y deja reporte con timestamp.

### agent-browser + CDP

Control programático del navegador vía Chrome DevTools Protocol:

```
agent-browser open <url>       # abrir página
agent-browser snapshot -i      # árbol de accesibilidad con refs (@e1)
agent-browser click @e1        # click por referencia
agent-browser fill @e2 "texto" # llenar campo
agent-browser console          # leer logs del browser
agent-browser errors           # leer errores JS
```

**Limitación actual:** No soporta eventos touch (swipe). Para s72 que requiere swipe como TikTok, se necesita una alternativa (Playwright, o CDP directo con dispatch touch events).

### screen-debug

Para apps nativas (GTK/Qt): usa xdotool + at-spi2 para leer árbol de accesibilidad y hacer click. Fallback a visión si no hay accesibilidad.

---

## 4. Flujo Multi-Agente

Con visibilidad total + testing automatizado + commits frecuentes, múltiples agentes pueden trabajar en paralelo:

```
Arquitecto:      define tickets y asigna
Backend x3:      cada uno toma un ticket, implementa, hace commit
Frontend x2:     implementan UI, hacen commit
Testing Agent:   detecta commits nuevos → corre tests → reporta regresiones
Integrador:      revisa reports, corrige si falla, cierra ticket
Escenógrafo:     actualiza dashboard de progreso automáticamente
```

Cada commit gatilla el pipeline:
1. Watchdog detecta cambio en git
2. `harness.py` corre suite completa
3. Reporte se guarda en `test-reports/auto-{timestamp}.txt`
4. Si falla, se notifica al agente responsable
5. Si pasa, el siguiente agente puede tomar el ticket

---

## 5. Estado Actual y Roadmap

### Lo que funciona hoy (s72)

| Componente | Estado |
|-----------|--------|
| API REST con estado completo | ✅ |
| CDP + agent-browser para testing | ✅ |
| test-reports/harness.py | ✅ |
| test-reports/watch.sh | ✅ |
| Reportes en md con trazabilidad | ✅ |
| Dev mode con errores al servidor | ✅ |

### Lo que falta

| Componente | Prioridad | Notas |
|-----------|-----------|-------|
| WebSocket de logs del browser → servidor | Alta | Hoy los console.log se pierden si no hay CDP conectado |
| Simulación de swipe (CDP touch events) | Alta | Necesario para testear feed TikTok-like |
| Git hooks para test automático pre-commit | Media | Hoy el watchdog es reactivo, no preventivo |
| Hot-reload de config desde YAML | Media | Ya tenemos API, falta el archivo externo |
| Test de regresión visual | Baja | Requiere visión (screenshot + diff) |

---

*Documento generado el 29 de mayo de 2026. Integra lecciones de s71 (VoiceButtonApp) y s72 (AI Video Studio) para el framework multi-agente.*
