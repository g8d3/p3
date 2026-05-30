# AI Video Studio — Equipo Multi-Agente de Construcción v2

> Plan para que múltiples agentes de IA trabajen en paralelo construyendo el sistema. v2 añade: múltiples instancias por tipo, y 3 nuevos tipos de agente.

---

## 1. ¿Múltiples instancias del mismo tipo?

Sí. No hay límite de agentes por tipo — el límite es **tu proveedor de inferencia**.

```
Ejemplo: 3 agentes backend trabajando simultáneamente
  ┌─ Agente Backend A: ticket "Pool de pre-render"
  ├─ Agente Backend B: ticket "Streaming HLS"
  └─ Agente Backend C: ticket "Render en background"

Cada uno consume ~500 tokens por iteración.
Los 3 en paralelo consumen ~1500 tokens por ciclo.
```

**Restricciones:**
- **Tokens/segundo del proveedor**: si tienes 20 TPS, en 25s los 3 agentes completan un ciclo cada uno
- **Dependencias**: el ticket de Streaming HLS quizás necesita que exista el Pool de pre-render primero
- **Archivos compartidos**: 2 agentes no pueden editar el mismo archivo a la vez → el Arquitecto asigna archivos exclusivos

**Máximo teórico de agentes activos según TPS:**

| TPS | Agentes recomendados | Notas |
|-----|--------------------|-------|
| <5 | 1-2 | Competirían por tokens, mejor escalonarlos |
| 5-20 | 2-4 | Buenos para equipo pequeño |
| 20-50 | 4-8 | 3 backend + 2 frontend + 1 conector etc. |
| >50 | 8-15 | Equipo completo, todas las áreas cubiertas |

---

## 2. Mapa de Agentes v2

```
                         ┌─────────────────────────────┐
                         │        ARQUITECTO           │
                         │  (coordina, prioriza,       │
                         │   revisa integración)       │
                         └──────────┬──────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
   ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
   │  BACKEND x3  │        │  FRONTEND x2 │        │ CONECTORES x2│
   │  API, render,│        │  feed, player│        │ GitHub, HF,  │
   │  TTS, cola   │        │  controles   │        │ X, YT, TK    │
   └──────────────┘        └──────────────┘        └──────────────┘
          │                         │                         │
          └─────────────────────────┼─────────────────────────┘
                                    ▼
                         ┌─────────────────────────────┐
                         │       INTEGRADOR            │
                         │  (tests E2E, debugging)     │
                         └─────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
   ┌──────────────┐        ┌──────────────┐        ┌──────────────┐
   │UX/EXPERIENCE │        │  ESCENÓGRAFO │        │   NEGOCIOS   │
   │  Prueba con  │        │  dashboards, │        │  research,   │
   │  usuarios,   │        │  progress,   │        │  pricing,    │
   │  reseñas,    │        │  contenido   │        │  partners    │
   │  retroalim.  │        │  promocional │        │              │
   └──────────────┘        └──────────────┘        └──────────────┘
```

---

## 3. Nuevos Tipos de Agente

### 3.1 UX / Experience Agent

**Función:** Evaluar el sistema desde la perspectiva del usuario final. No le importa si el código funciona — le importa si la experiencia es placentera, intuitiva, y adictiva (como TikTok).

```
Preguntas que responde:
- "¿Un usuario normal entendería esta pantalla en 3 segundos?"
- "¿Por qué un usuario haría scroll al siguiente video?"
- "¿Qué haría que un usuario cierre la app?"
- "¿Esta animación se siente fluida o lenta?"
- "¿Hay demasiadas opciones? ¿Muy pocas?"

Métodos:
  - Revisar UI/UX de cada pantalla
  - Señalar fricciones (ej: "este botón debería estar más arriba")
  - Comparar con TikTok, YouTube, Instagram (referencias)
  - Sugerir tests A/B
  - Escribir reseñas simuladas de usuario

Output: Documento de fricciones + prioridades de mejora.

Relación con otros agentes:
  - Reporta fricciones al Frontend para corregir
  - Reporta deseos/necesidades al Arquitecto para nuevos tickets
  - Colabora con Escenógrafo para entender cómo el usuario percibe el contenido
```

### 3.2 Escenógrafo (antes "Visualization + Content Creator")

**Función:** Construir la visualización del progreso del proyecto + crear contenido promocional usando la propia plataforma.

```
Dos sub-rols:

A) Dashboard de progreso
  - Mapa visual del proyecto: qué se ha completado, qué está en progreso
  - Gráfico de velocidad (tickets/día, tokens consumidos, TPS real)
  - Estado de cada fuente de datos
  - Errores recientes y su resolución
  - Se actualiza automáticamente con cada avance

B) Creación de contenido promocional (meta)
  - Usa la propia plataforma para crear videos sobre el desarrollo
  - Ej: "Mira cómo construimos un clon de TikTok con IA — día 1"
  - Los videos se publican en el feed interno y en redes
  - El progress dashboard también puede renderizarse como video

Relación con otros agentes:
  - Recibe reportes de todos los agentes para el dashboard
  - Usa el pipeline de render de Backend para generar videos promocionales
  - Colabora con UX para que el dashboard sea claro y útil
  - Colabora con Negocios para alinear el contenido con la estrategia
```

### 3.3 Business Development Agent

**Función:** Investigar mercado, competidores, oportunidades de monetización, partnerships, y estrategia de lanzamiento.

```
Tareas:
  - Investigar productos similares (Rev-id, Opus Clip, etc.)
  - Analizar modelos de negocio: suscripción, ads, freemium
  - Investigar APIs necesarias: costos de X API, YouTube API, etc.
  - Identificar partnerships potenciales (proveedores de GPU, hosting)
  - Estimar costo de operación por video generado
  - Estimar cuántos usuarios necesita para ser rentable
  - Investigar regulaciones (GDPR, derechos de autor, contenido generado)

Output: Documento de estrategia de negocio.

Relación con otros agentes:
  - Informa a Arquitecto sobre restricciones de costo
  - Informa a Conectores sobre APIs que priorizar según ROI
  - Colabora con Escenógrafo para contenido promocional alineado
```

---

## 4. Ejemplo: Ciclo Completo con Todos los Agentes

Escenario: Se completa un ticket de "Feed infinito".

```
1. ARQUITECTO:              Asigna ticket "Feed infinito" a Frontend
2. AGENTE FRONTEND:         Implementa scroll infinito en 3 ciclos
3. AGENTE INTEGRADOR:       Verifica que el scroll carga videos nuevos
4. UX AGENT:                Prueba la experiencia:
                            "El scroll se siente fluido, pero el primer
                             video tarda 2s en cargar — hay que mostrar
                             un skeleton loader"
5. AGENTE FRONTEND:         Añade skeleton loader (nuevo ticket rápido)
6. ESCENÓGRAFO:             Actualiza dashboard: "Feed infinito ✅"
                            Crea video promocional:
                            "Demo: scroll infinito en AI Video Studio"
7. BUSINESS AGENT:          Reporta: "Esta funcionalidad nos diferencia
                            de Rev-id que no tiene feed en vivo"
8. ARQUITECTO:              Revisa todo, cierra ticket, asigna siguiente
```

---

## 5. Gestión del Recurso Limitado: Tokens en Tiempo Real

La velocidad de tokens (TPS) de tu proveedor **no es fija**. Varía según:
- Carga del proveedor en ese momento
- Tamaño del prompt (prompts más largos = más latency)
- Tipo de tarea (streaming vs no streaming)
- Otros usuarios compartiendo el mismo proveedor

**Por esto, el sistema debe medir TPS en tiempo real y auto-ajustarse:**

```yaml
monitoreo:
  - Cada agente reporta su TPS real al completar una llamada
  - El Arquitecto mantiene una ventana móvil de los últimos 60s
  - Si el TPS promedio baja de un umbral → se reducen agentes activos
  - Si sube → se lanzan más agentes
  - El dashboard del Escenógrafo muestra: TPS actual, histórico, agentes activos

colas_de_tokens:
  - No todos los agentes tienen la misma prioridad
  - Prioridad 1: Backend + Frontend (construcción del núcleo)
  - Prioridad 2: Conectores + Integrador
  - Prioridad 3: UX + Escenógrafo + Negocios
  - Prioridad 4: User Clone (bajo consumo, corre en idle)
  - Prioridad 5: DX (documentación, se hace cuando sobra capacidad)

ejemplo_de_autoajuste:
  TPS actual: 15 → activos: 3 agentes (Backend, Frontend, Conectores)
  TPS sube a 40 → activos: 6 agentes (+UX, +Escenógrafo, +Integrador)
  TPS baja a 8  → activos: 2 agentes (Backend, Frontend)
```

---

## 6. Developer Experience Agent (DX)

**Función:** Que el código sea un placer de leer, modificar y extender. Sin DX, el proyecto se vuelve una bola de lodo y los agentes pierden tiempo descifrando código en vez de construyendo.

```
Qué hace:
  - Revisa consistencia del código: imports, naming, estructura de carpetas
  - Escribe y mantiene documentación técnica (README, docstrings, CONTRIBUTING.md)
  - Crea y actualúa diagrams de arquitectura (mermaid, ascii)
  - Señala dead code, código duplicado, complejidad innecesaria
  - Mantiene un archivo CHANGELOG.md con cada cambio relevante
  - Escribe tests donde falten (no tests funcionales — eso es del Integrador)
  - Sugiere refactors cuando el código se vuelve difícil de navegar

Ritmo de trabajo:
  - Corre en segundo plano con prioridad baja
  - Cada vez que otro agente completa un ticket, DX revisa el diff y documenta
  - No bloquea a nadie — trabaja con lo que sobra de tokens

Relación con otros agentes:
  - Sirve a TODOS los agentes: un códigobase limpio los hace más rápidos
  - El Arquitecto lo consulta para saber el estado real del código
  - El Integrador usa su documentación para escribir mejores tests
```

---

## 7. User Clone Agent

**Función:** Un clon digital del usuario dueño del proyecto. Se conecta a TODOS sus chats con IA (Crush, ChatGPT, Claude, Gemini, etc.), indexa las conversaciones, y puede opinar como lo haría él.

```
Esto es posible porque:
  - Cada chat con IA contiene las preferencias, decisiones y opiniones del usuario
  - Un índice de búsqueda sobre esos chats permite consultar:
    "¿Qué opina el usuario sobre interfaces versus pipelines?"
    "¿Cuál fue su decisión sobre usar ASS vs SRT?"
    "¿Prefiere música synthwave o la que está en tendencia?"
  - El User Clone no adivina — busca en el índice y responde con referencias

Fuentes de datos:
  - Chat actual (Crush) → historial completo de la conversación
  - ChatGPT → exportar historial como JSON
  - Claude → exportar proyectos
  - Cualquier otro chat donde el usuario haya discutido el proyecto

Formato del índice:
  ```
  /home/vuos/code/p3/s72/knowledge-base/
    conversations/
      2026-05-27_discusion-subtitulos.md
      2026-05-27-multi-agente-arquitectura.md
      2026-05-26-fix-compositor-duracion.md
    decisions/
      FORMATO-SUBTITULOS.md      -> "ASS con karaoke, no SRT plano"
      FONDO-MUSICAL.md           -> "Synthwave 80s o tendencias TikTok"
      UI-FILOSOFIA.md            -> "Feed automático, no pipeline manual"
  ```

Cuándo consultarlo:
  - El Arquitecto pregunta: "¿Prefieres X o Y?" → User Clone responde con cita textual
  - El UX Agent pregunta: "¿Crees que al usuario le gustaría esto?" → User Clone busca patrones
  - Cualquier agente puede etiquetarlo: @user-clone para pedir su opinión

Límites éticos:
  - El User Clone NO toma decisiones — solo informa lo que el usuario ya ha dicho
  - Las decisiones las toma siempre el humano o el Arquitecto
  - El índice se construye con datos que el usuario ha compartido explícitamente
```

---

## 8. Más Tipos que Podrían Existir

| Agente | Función | ¿Cuándo agregarlo? |
|--------|---------|-------------------|
| **Seguridad** | Audita código en busca de vulnerabilidades, APIs keys expuestas, inyecciones | Cuando haya algo que auditar |
| **Legal** | Revisa términos de servicio, licencias, derechos de contenido generado | Antes del lanzamiento público |
| **SEO/ASO** | Optimiza para búsquedas en web y app stores | Pre-lanzamiento |
| **Traductor** | Localiza la app a otros idiomas | Post-MVP |
| **Datos** | Analiza métricas de uso, retención, engagement | Cuando haya usuarios |
| **Sonido** | Diseña paisajes sonoros, alertas, transiciones de audio | Cuando la UI esté estable |
| **Animador** | Crea transiciones, micro-interacciones, motion design | Cuando la UI esté estable |
| **Comunidad** | Gestiona feedback de usuarios tempranos, escribe updates | Post-lanzamiento |

---

## 9. Próximo Paso — Prueba de Concepto Inmediata

No medir TPS artificialmente. Empezar a trabajar con un proxy que mida TPS en tiempo real, y que el coordinador use esa métrica para decidir cuántos agentes lanzar.

### 9.1 Arquitectura de comunicación

```
window 0 (yo, Crush)          window 1 (agente-1)        window 2 (agente-2)
┌────────────────────┐       ┌────────────────────┐     ┌────────────────────┐
│  tmux: p3/s72      │       │  tmux: agente-1     │     │  tmux: agente-2    │
│                    │──────►│  python server.py   │     │  python server.py  │
│  main agent        │◄──────│  puerto 9101        │     │  puerto 9102       │
│  coordina, reporta │  HTTP │                     │     │                    │
│  al usuario        │       │  hace tareas        │     │  hace tareas       │
└────────────────────┘       └────────────────────┘     └────────────────────┘
         │                                                       │
         │                    ┌────────────────────┐             │
         └────────────────────┤  agente-resumidor  │◄────────────┘
                              │  window 3           │
                              │  puerto 9103        │
                              │  comprime updates   │
                              │  para el usuario    │
                              └────────────────────┘
```

**Protocolo:** HTTP simple. Cada agente expone:
- `GET /health` → estado
- `POST /task` → recibe una tarea, la ejecuta, responde
- `GET /status` → última tarea completada, métricas (TPS, tiempo)

### 9.2 Prueba 1: Un agente funcional

```bash
# 1. Yo (Crush) abro un nuevo tmux window con un agente echo
tmux new-window -n agente-echo
tmux send-keys -t agente-echo 'python3.12 -c "
import http.server, json, time

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers[\"Content-Length\"]))
        data = json.loads(body)
        task = data.get(\"task\", \"\")
        print(f\"Recibí: {task}\")
        # Hacer la tarea (ej: leer un archivo)
        result = f\"Procesé: {task.upper()}\"
        self.send_response(200)
        self.send_header(\"Content-Type\", \"application/json\")
        self.end_headers()
        self.wfile.write(json.dumps({\"result\": result}).encode())
    def do_GET(self):
        self.send_response(200)
        self.send_header(\"Content-Type\", \"application/json\")
        self.end_headers()
        self.wfile.write(json.dumps({\"status\": \"ok\"}).encode())

http.server.HTTPServer((\"127.0.0.1\", 9101), Handler).serve_forever()
"' Enter

# 2. Desde mi window, le envío una tarea
curl -s -X POST http://127.0.0.1:9101/task \
  -H 'Content-Type: application/json' \
  -d '{"task": "leer el archivo plan_multiagente.md y resumir los primeros 3 agentes"}'

# 3. El agente responde y me muestra el resultado
```

### 9.3 Agente Resumidor (el que habla con el usuario)

Este agente es el **único** con el que el usuario interactúa directamente. Recibe actualizaciones de todos los demás agentes y las comprime en un mensaje legible.

```python
# Resumidor — window 3, puerto 9103
# Recibe POST /update de cualquier agente
# Acumula updates en un buffer
# Cuando el usuario pide "status" o cada N segundos, comprime todo en un párrafo

Input:  múltiples {agente: str, accion: str, resultado: str, timestamp: float}
Output: un resumen tipo:
  "[agente-backend] completó pool de pre-render (2.3s)
   [agente-frontend] trabajando en scroll infinito (60%)
   [ux-agent] encontró 3 fricciones en la pantalla de inicio"
```

### 9.4 Plan de prueba concreto

```
Paso 1: Yo abro ventana tmux con agente-echo (HTTP en puerto 9101)  ✅
Paso 2: Le envío tarea via HTTP, recibe respuesta                        ⬜
Paso 3: Mido TPS real del proveedor durante la comunicación              ⬜
Paso 4: Abro segundo agente, ambos responden                             ⬜
Paso 5: Implemento agente resumidor (el del usuario)                     ⬜
Paso 6: El flujo completo: 2 agentes → resumidor → yo → usuario         ⬜
```
