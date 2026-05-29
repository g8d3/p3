

# AI Video Studio — Problemas y Soluciones

## Arquitectura actual

```
Servidor (FastAPI, puerto 8777)
  ├── Fuentes: GitHub, HuggingFace, Pixabay, X, YouTube, TikTok
  ├── Feed engine: producer continuo (~10-20s por package)
  │   ├── fetch_all_trends(force=True) — sin cache
  │   ├── generate_script() — LLM vía proxy (puerto 9100)
  │   ├── generate_narration() — edge-tts (speech.platform.bing.com)
  │   ├── save_ass() — subtítulos con karaoke
  │   └── queue: hasta 10 packages, rotación FIFO
  ├── API REST (30+ endpoints)
  └── Composer: /composer (HTML+JS, composición en browser)

Browser (composer.html)
  ├── Video< muted + Audio narración + Audio música
  ├── Subtítulos CSS sincronizados con requestAnimationFrame
  ├── Seek bar, swipe up/down, tap play/pause
  ├── Panel de estilo (voz, fuente, música, loop, dev mode)
  └── Dev console con errores detallados
```

---

## Problemas encontrados y soluciones

### 1. ffmpeg.wasm era inviable

**Problema**: Se intentó usar ffmpeg.wasm para composición en browser.
**Síntoma**: 31MB de descarga, requiere headers COEP/COOP, SharedArrayBuffer, no funcionaba en todos los browsers.
**Solución**: APIs nativas del browser (`<video muted>` + `<Audio>` + subtítulos CSS con requestAnimationFrame).
**Lección**: No asumir que herramientas de desktop funcionan en browser. Preferir APIs nativas.

### 2. Server-side ffmpeg era lento

**Problema**: ffmpeg en servidor tomaba 30-70s por video para escalar, quemar subtítulos, mezclar audio, codificar.
**Síntoma**: El usuario esperaba 30-70s para cada video nuevo.
**Solución**: Mover composición al browser. Servidor solo genera componentes rápidos (~10s).
**Lección**: Separar "generación de contenido" (rápido, server) de "composición de medios" (pesado, cliente).

### 3. Mismo contenido siempre

**Problema**: Cada video traía las mismas noticias.
**Causa raíz**: Cache de 5 minutos en los conectores de fuentes. Todos los packages usaban los mismos trends.
**Solución**: 
- `force=True` en fetch para bypass de cache
- `random.sample()` para elegir items aleatorios de cada fuente
- `_last_topic` tracker para evitar que el LLM repita tema
- Cada package usa datos frescos
**Lección**: Caché es bueno para rate limiting, malo para feeds. Siempre freshness check.

### 4. Audio se superponía al cambiar de video

**Problema**: Al hacer swipe al siguiente video, el audio del anterior seguía sonando.
**Causa raíz**: Los objetos `Audio` no se destruían al cargar el nuevo package.
**Solución**: `currentAudio.pause(); currentAudio.src=''; currentAudio=null;` antes de cargar nuevo. Lo mismo para música.
**Lección**: Siempre limpiar recursos multimedia explícitamente.

### 5. Autoplay bloqueado por el browser

**Problema**: El usuario tenía que tocar un botón para iniciar el video.
**Causa raíz**: Política de autoplay de Chrome: `audio.play()` sin interacción del usuario falla.
**Solución**: 
- Video comienza muteado (autoplay permitido)
- Badge "🔇 Sin audio — toca la pantalla" si audio no arranca
- Al tocar, se intenta `audio.play()` de nuevo
- Subtítulos funcionan incluso sin audio
**Lección**: No pelear contra autoplay policy — aceptarla y diseñar UX alrededor.

### 6. Loader bloqueante

**Problema**: Pantalla de "Generando..." impedía cualquier interacción.
**Solución**: Reemplazar full-screen loader con barra delgada no bloqueante en la parte superior.
**Lección**: Nunca bloquear la UI mientras se carga contenido en segundo plano.

### 7. Null reference en JavaScript

**Problema**: Referencias a elementos DOM eliminados (`next-btn-big`, `next-overlay`) causaban `TypeError: Cannot set properties of null`.
**Síntoma**: El JavaScript entero crasheaba antes de ejecutar cualquier handler (swipe, controles, estilo).
**Solución**: Null-safety en todas las referencias: `if($('id')) $('id').onclick=...`.
**Lección**: Siempre verificar que un elemento existe antes de operar sobre él.

### 8. edge-tts falla sin internet

**Problema**: `generate_narration()` requiere conexión a `speech.platform.bing.com` (API de Microsoft).
**Síntoma**: "Cannot connect to host speech.platform.bing.com:443".
**Solución**: Manejar el error y reintentar. Pero la dependencia externa sigue siendo frágil.
**Lección**: TTS externo es un punto de falla. Considerar TTS local (e.g., Coqui, Piper) para futuro.

### 9. Producer reactivo vs continuo

**Problema**: El feed engine solo generaba packages cuando la cola estaba por debajo del límite.
**Síntoma**: Si la cola tenía 1 package, el producer dormía 3s y generaba 1 más, manteniéndose siempre en 1.
**Solución**: Producer continuo que genera packages sin parar, con solo 0.5s entre sí. La cola se llena hasta 10 y rota.
**Lección**: En un sistema multi-usuario, el productor debe ser agresivo e independiente del consumo.

### 10. Acumulación de archivos en output/

**Problema**: Cada package genera ~5 archivos (narración.mp3, subtítulos.ass, etc.). En una sesión se acumulan cientos.
**Síntoma**: 122 archivos, 805MB después de unas horas.
**Solución**: Endpoint `POST /api/cleanup` que elimina packages viejos (default: keep 5). Botón en panel de visibilidad.
**Lección**: Siempre tener un mecanismo de limpieza. Los archivos temporales se acumulan rápido.

### 11. Estilo no se aplicaba en tiempo real

**Problema**: Cambiar volumen, fuente, o voz solo afectaba al siguiente video.
**Solución**: Música: `input` event → `currentMusic.volume` inmediato. Fuente: `input` event → `#sub-text.style.fontSize` inmediato.
**Lección**: Separar controles "inmediatos" (volumen, fuente) de "necesitan regeneración" (voz).

### 12. Subtítulos con tamaño incorrecto en browser

**Problema**: Los tamaños de fuente del servidor (96, 120, 144, 192) son para ASS a 1080x1920. En browser CSS se ven enormes.
**Solución**: Input numérico libre con default 32px. El valor se guarda en sessionStorage.
**Lección**: No reusar parámetros de renderizado server-side para CSS. Son contextos diferentes.

---

## Dependencias externas frágiles

| Servicio | Dependencia | Riesgo |
|----------|-------------|--------|
| edge-tts | speech.platform.bing.com | Sin internet no hay narración |
| Proxy LLM | opencode.ai | API key necesaria, rate limits |
| GitHub API | api.github.com | Rate limit sin API key |
| HuggingFace | huggingface.co | Rate limit sin API key |

---

## Próximas mejoras sugeridas

1. **TTS local** (Piper, Coqui) para eliminar dependencia de internet
2. **Cola persistente** (SQLite) para mantener packages entre reinicios
3. **WebSocket** para empujar nuevos packages al browser sin polling
4. **Service Worker** para cache de assets y reproducción offline
5. **Tests automatizados** con CDP para cada control
6. **Modo desarrollador** con upload de errores al servidor
