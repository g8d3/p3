# AI Video Studio — Bitácora Completa de la Sesión

**Fecha:** 29 de mayo de 2026
**Contexto:** Desarrollo de pipeline de video autónomo tipo TikTok, con composición en navegador.
**Tags:** `#feed-autónomo` `#browser-compositing` `#ffmpeg-wasm` `#edge-tts` `#razonamiento-llm`

---

## Arquitectura Final

```
┌─────────────────────────────────────────────────────────┐
│                      SERVIDOR (FastAPI :8777)            │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │ Fuentes  │  │ Feed     │  │ API REST             │  │
│  │ · GitHub │  │ Engine   │  │ · /api/feed/next     │  │
│  │ · HF     │  │ (prod.   │  │ · /api/feed/package  │  │
│  │ · Pixabay│  │  continuo│  │ · /api/style          │  │
│  │ · X      │  │  ~10s    │  │ · /api/config         │  │
│  │ · YouTube│  │  c/u)    │  │ · /api/status         │  │
│  │ · TikTok │  └────┬─────┘  │ · /api/cleanup        │  │
│  └──────────┘       │        │ · /api/dev/error      │  │
│                     │        └──────────────────────┘  │
│                     ▼                                   │
│           ┌─────────────────┐                           │
│           │  Cola de        │                           │
│           │  Packages       │                           │
│           │  (máx 10, FIFO) │                           │
│           │  · narración    │                           │
│           │  · subtítulos   │                           │
│           │  · assets URLs  │                           │
│           └────────┬────────┘                           │
│                    │                                     │
├────────────────────┼─────────────────────────────────────┤
│                    ▼                                     │
│  ┌──────────────────────────────────────────────────┐   │
│  │            NAVEGADOR (composer.html)              │   │
│  │                                                   │   │
│  │  GET /api/feed/next  → pop package                │   │
│  │  Download narración.mp3 + gameplay.mp4 + subs     │   │
│  │  Composicion en browser:                          │   │
│  │  · <video muted>  (background gameplay auto-play) │   │
│  │  · <Audio> narración                              │   │
│  │  · <Audio> música de fondo (loop, volumen estilo) │   │
│  │  · Subtítulos CSS con requestAnimationFrame       │   │
│  │  · Seek bar, swipe up/down, tap play/pause        │   │
│  │  · Panel estilo (voz, fuente, música, loop, dev)  │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Decisiones de Arquitectura

### 1. Composición en el navegador, no en el servidor

**Decisión:** El servidor genera solo componentes rápidos (~10s: trends → script → TTS → subtítulos).  
El navegador descarga los componentes y los reproduce sincronizados con APIs nativas (`<video muted>`, `<Audio>`, CSS subtítulos).

**Por qué:** ffmpeg en servidor tomaba 30-70s por video. ffmpeg.wasm en browser era 31MB de descarga y requería headers COEP/COOP problemáticos.

**Alternativas descartadas:**
- ffmpeg.wasm (31MB, SharedArrayBuffer, COEP/COOP, lento en WASM)
- ffmpeg server-side (colas de 30-70s, bloqueante)
- Streamlit como reproductor (sin control de eventos de video)

### 2. Producer continuo vs reactivo

**Decisión:** El feed engine genera packages ininterrumpidamente (0.5s entre generaciones), la cola se llena hasta 10 y rota FIFO.

**Por qué:** El modelo reactivo (generar solo cuando la cola está baja) mantenía la cola siempre en 1-2 packages. Con N usuarios simultáneos, se agotaba inmediatamente.

### 3. Sin caché de trends

**Decisión:** Cada package obtiene datos frescos de todas las fuentes (`force=True`).

**Por qué:** El caché de 5 minutos (heredado de los conectores) hacía que todos los packages de la misma ventana tuvieran las mismas noticias.

### 4. Modelo LLM razonador

**Decisión:** Usar `reasoning_content` como fallback cuando `content` está vacío.

**Por qué:** `deepseek-v4-flash` es un modelo razonador que pone la respuesta en `reasoning_content` y deja `content` vacío cuando se queda sin tokens.

---

## Problemas Encontrados y Soluciones

| # | Problema | Síntoma | Causa Raíz | Solución |
|---|----------|---------|------------|----------|
| 1 | ffmpeg.wasm no funciona | Worker no se construye, 31MB descarga | COEP/COOP headers, SharedArrayBuffer, CORS | APIs nativas del browser |
| 2 | Server-side ffmpeg lento | 30-70s por video | ffmpeg escala + quema subs + mezcla audio + codifica | Mover composición al browser |
| 3 | Mismo contenido siempre | Todos los videos mismas noticias | Cache de 5 min en conectores | `force=True` + `random.sample()` + `_last_topic` |
| 4 | Audio se superpone | Al cambiar de video, el anterior sigue | Objetos Audio no se destruían | `pause(); src=''; null` explícito |
| 5 | Autoplay no funciona | Usuario debe tocar botón | Política de autoplay del browser | Video muted siempre, badge "toca para iniciar" |
| 6 | Loader bloqueante | Pantalla completa impide interacción | Full-screen loader | Barra delgada no bloqueante |
| 7 | JavaScript crashea | Controles no funcionan, swipe no anda | Referencia a elemento DOM eliminado | Null-safety: `if(el) el.onclick=...` |
| 8 | TTS sin internet | "Cannot connect to speech.platform.bing.com" | edge-tts requiere conexión a Microsoft | Manejo de error + reintento |
| 9 | Producer lento | Cola nunca se llena | Producer esperaba consumo para generar | Producer continuo sin pausa |
| 10 | Archivos acumulados | 122 archivos, 805MB | Nunca se limpiaban | `POST /api/cleanup` + botón en UI |
| 11 | Estilo no inmediato | Cambios solo afectan siguiente video | Todo "al aplicar" | Música/fuente: `input` event inmediato |
| 12 | Subtítulos tamaño incorrecto | Textos enormes en browser | Reusar tamaños ASS (96, 144, 192) en CSS | Input libre default 32px |
| 13 | LLM devuelve vacío | Script (0 chars) | Modelo razonador pone respuesta en `reasoning_content` | Fallback a `reasoning_content` |
| 14 | Browser fantasma | Cola se consume sola inmediatamente | `cdp.sh` + Chrome en background recargando composer cada 5s | Matar Chrome explícitamente |
| 15 | Sin visibilidad errores | "Failed to fetch" sin contexto | Error genérico | Modo dev: `?dev=1` muestra errores reales + upload al server |

---

## Principios de Framework Aplicados

### 1. Visibilidad Total

- **Para el usuario:** Panel 📊 con archivos, tamaños, cola, últimas acciones, botón limpiar
- **Para el desarrollador:** Modo 🐛 Dev con `?dev=1`, console.errors subidos al server via `POST /api/dev/error`
- **Para Crush:** Logs estructurados en `logs/studio_YYYYMMDD.log`, endpoint `GET /api/actions` con historial completo

### 2. Configuración sobre Código

- API keys configurables desde la UI (panel 🔧 Configurar API keys)
- `POST /api/config` persiste cambios en runtime
- Estilo (voz, fuente, volumen) configurable en tiempo real vía `POST /api/style`
- Evitamos hardcodear valores: todo parámetro tiene endpoint propio

### 3. Ciclos Cortos

- Cada iteración: implementar → testear en browser → corregir → documentar
- Feedback inmediato: el composer se prueba con `agent-browser --cdp 9222 snapshot`
- Errores se ven al instante en el modo dev o en los logs

### 4. Testing Automatizado

- `agent-browser` via CDP para snapshot, click, scroll (aunque scroll no es swipe real)
- Snapshot de accesibilidad para verificar elementos DOM
- Endpoint `GET /api/dev/errors` recolecta errores del browser
- **Limitación actual:** No se puede simular touch swipe con xdotool. CDP/selenium sería ideal.

---

## Dependencias Externas y Riesgos

| Servicio | Puerto | Dependencia | Riesgo |
|----------|--------|-------------|--------|
| Proxy LLM | 9100 | opencode.ai (API key) | Rate limits, cambios de API, key vencida |
| edge-tts | — | speech.platform.bing.com | Sin internet no hay narración |
| GitHub API | — | api.github.com | Rate limit (60/h sin key) |
| HuggingFace | — | huggingface.co | Rate limit (30/min sin key) |
| Pixabay | — | pixabay.com | API key gratuita pero con límite |

### Mejoras pendientes

1. **TTS local** (Piper/Coqui) para eliminar dependencia de internet
2. **Cola persistente** (SQLite) para mantener packages entre reinicios
3. **WebSocket** para empujar nuevos packages al browser sin polling
4. **Service Worker** para cache de assets y offline
5. **End-to-end testing real** con swipe simulado (Playwright/CDP)

---

## Comandos Útiles

```bash
# Iniciar servicios
cd ai-video-studio
python3.12 agents/proxy.py &
PROXY_URL=http://127.0.0.1:9100 python3.12 -m uvicorn backend.main:app --host 0.0.0.0 --port 8777

# Ver estado
python3.12 -c "import urllib.request,json; print(json.loads(urllib.request.urlopen('http://127.0.0.1:8777/api/status',timeout=5).read()))"

# Modo desarrollador
open http://192.168.0.34:8777/composer?dev=1

# Matar Chrome fantasma
pkill -9 -f chrome 2>/dev/null

# Ver errores del browser
python3.12 -c "import urllib.request,json; print(json.loads(urllib.request.urlopen('http://127.0.0.1:8777/api/dev/errors',timeout=5).read()))"
```

---

*Documento generado el 29 de mayo de 2026. Contiene toda la información de la sesión de desarrollo de ai-video-studio.*
