# AI Video Studio — Bitácora de aprendizaje

## 2026-05-28: Feed pipeline + browser compositing

### Arquitectura final

```
Servidor (FastAPI, ~10s por video)
  └── Fetch trends (GitHub + HF) → Script LLM → edge-tts narración → Subtítulos ASS
  └── Queue: packages de componentes (NO videos renderizados)

Browser (compositor.html, instantáneo)
  └── Descarga assets individuales
  └── Video< muted + Audio + subtítulos CSS sincronizados
  └── Sin ffmpeg.wasm — APIs nativas del browser
```

### Lecciones aprendidas

#### 1. ffmpeg.wasm no es práctico para este caso
- **31MB** de descarga inicial (ffmpeg-core.wasm)
- Requiere headers `Cross-Origin-Embedder-Policy: require-corp` y `Cross-Origin-Opener-Policy: same-origin`
- SharedArrayBuffer necesario — no funciona en todos los navegadores
- La compilación WASM es más lenta que ffmpeg nativo (2-3x)
- **Alternativa correcta**: `<video muted>` + `<audio>` + subtítulos CSS sincronizados con `requestAnimationFrame`
  - Sin descargas masivas
  - Codecs nativos (hardware accelerated)
  - Sincronización perfecta

#### 2. Streamlit no es ideal para apps multimedia
- No tiene callbacks para eventos de video (end, timeupdate)
- `st.video()` no acepta `key` parameter en todas las versiones
- La comunicación con APIs externas requiere urllib o requests
- **Mejor**: servir una página HTML standalone desde FastAPI (`/composer`)

#### 3. edge-tts es rápido pero blockeante en el event loop
- `subprocess.run` en ffmpeg bloquea el event loop de asyncio
- Solución: `loop.run_in_executor()` para calls blocking
- edge-tts en sí es async y funciona bien

#### 4. Cola de pre-render vs. generación on-demand
- Pre-render pool de 3 videos funciona bien
- Pero renderizar ffmpeg (~40s) hace que la cola se sienta lenta
- **Solución**: generar solo componentes rápidos (~10s) y dejar la composición al browser

#### 5. Gestión de recursos
- Los navegadores abiertos (Chrome CDP) consumen mucha RAM (~500MB+)
- Siempre cerrar con `agent-browser close` y `pkill -f chrome`
- ffmpeg.wasm en particular es pesado de cargar
- Preferir `run_in_background` para servicios largos

#### 6. Proxy de LLM
- El proxy TPS (puerto 9100) a veces queda colgado
- Verificar con `lsof -ti :9100` y matar PID antes de reiniciar
- OPENCODE_GO_API_KEY necesaria en entorno

### Comandos útiles

```bash
# Iniciar todo
cd ai-video-studio
python3.12 agents/proxy.py &
PROXY_URL=http://127.0.0.1:9100 python3.12 -m uvicorn backend.main:app --host 0.0.0.0 --port 8777

# Verificar
python3.12 -c "import urllib.request,json; print(json.loads(urllib.request.urlopen('http://127.0.0.1:8777/api/health',timeout=5).read()))"

# Probar package
python3.12 -c "import urllib.request,json; d=json.loads(urllib.request.urlopen('http://127.0.0.1:8777/api/feed/package',timeout=5).read()); print('ready' if d['status']=='ready' else 'waiting')"

# Limpiar
pkill -f "uvicorn" 2>/dev/null; pkill -f "proxy.py" 2>/dev/null; pkill -f "chrome" 2>/dev/null

# Browser testing
agent-browser --cdp 9222 open "http://localhost:8777/composer"
agent-browser --cdp 9222 snapshot
agent-browser --cdp 9222 close
```

### Endpoints activos

| Endpoint | Descripción |
|----------|-------------|
| `GET /api/health` | Health check |
| `GET /api/feed/package` | Siguiente package de componentes |
| `GET /api/feed/queue` | Estado de la cola |
| `GET /api/feed/next` | Consumir y obtener package |
| `GET /api/feed/peek` | Ver sin consumir |
| `GET /api/style` | Estilo actual (voz, fuente, etc.) |
| `POST /api/style` | Actualizar estilo |
| `GET /api/actions` | Historial de acciones |
| `GET /api/sources` | Estado de conexiones |
| `GET /api/download/{file}` | Descargar archivo de output/assets |
| `GET /composer` | Player browser |
| `GET /player` | Alias de /composer |


### Acceso desde cualquier dispositivo


Las URLs de descarga son relativas — funcionan desde cualquier host.

## 2026-05-28: Visibilidad + limpieza + contenido fresco

### Problemas y soluciones

| Problema | Causa raiz | Solucion |
|----------|------------|----------|
| Mismo contenido siempre | Cache trends 5min | `force=True` en fetch, cada package datos frescos |
| Mismo tema repetido | LLM recibe mismos trends | `_last_topic` tracker + prompt pide evitar tema anterior |
| Audio se superpone | Audio objects no se destruian | `pause(); src=""; null` antes de cargar nuevo |
| Video no empieza solo | Browser bloquea autoplay | Primer tap del usuario inicia todo |
| Acumulacion archivos | Nunca se limpiaban | `POST /api/cleanup` + boton en panel visibilidad |
| Sin visibilidad | No habia dashboard | `GET /api/status` + panel en composer |

### Endpoints nuevos
- `GET /api/status` - cola, archivos, tamanos, assets, caches
- `POST /api/cleanup` - elimina packages viejos (param: keep)

### Lecciones
1. Cache vs frescura: APIs con cache de 5min util pero malo para variedad
2. Limpieza auto: outputs se acumulan rapido (~100 archivos/sesion)
3. Null safety en JS: referencias a DOM eliminados crashean todo el JS
4. Browser autoplay: navegadores bloquean audio autoplay, primer tap inicia

## 2026-05-29: Hallazgos críticos

### Modelo LLM razonador
`deepseek-v4-flash` es un modelo razonador. Devuelve la respuesta en `reasoning_content` (no en `content`). El campo `content` queda vacío. Esto causaba "Script (0 chars)" y la cola nunca se llenaba.

**Solución:** Fallback: si `content` está vacío pero `reasoning_content` tiene texto, usarlo.

### Browser fantasma
El `cdp.sh` lanzó Chrome en background. Ese Chrome tenía el composer abierto y recargaba la página cada ~5s. Esto consumía los packages en cuanto se generaban. La cola nunca pasaba de 1.

**Solución:** Matar Chrome explícitamente: `pkill -9 -f chrome`

### Documento completo
Se generó `docs/bitacora_completa.md` con toda la sesión: arquitectura, decisiones, 15 problemas documentados, principios de framework.
