# Smoke Test — AI Video Studio

**Fecha**: 2026-05-29
**App**: http://127.0.0.1:8777/composer
**Backend**: FastAPI via uvicorn en puerto 8777
**CDP**: Chrome Headless 148 vía agent-browser 0.27.0
**Dev log**: window 0 — To-Do 0/6 (prefilling queue, autoplay, swipe, etc.)

---

## 1. API Backend

| Endpoint | Status | Detalle |
|----------|--------|---------|
| `GET /api/feed/queue` | ✅ | 3 videos en cola |
| `GET /api/feed/package` | ✅ | Siguiente paquete listo |
| `GET /api/feed/next` | ✅ | Pop del paquete funciona |
| `GET /api/style` | ✅ | Voice: Dalia, font:96, max_words:5, music:0.12 |
| `POST /api/style` | ✅ | Cambio de voice/font/music funciona |
| `GET /api/sources` | ✅ | github, huggingface, pixabay conectados |
| `GET /api/assets` | ✅ | 5 gameplay videos, 4 music tracks |

**API funcional — sin errores.**

---

## 2. Página /composer (Frontend)

| Aspecto | Status | Evidencia |
|---------|--------|-----------|
| Carga inicial | ✅ | Title: "AI Video Studio" |
| Dev mode | ✅ | Activo vía URL `?dev=1` — logs visibles |
| Video player | ✅ | Elemento `<video>` presente |
| Seek bar | ✅ | Range slider operativo, muestra "0:00 / 0:27" |
| Gear button | ✅ | Click abre panel de estilo |
| Style panel | ✅ | Voice, font, music, loop, dev controls |
| Apply button | ✅ | Presente |
| Subtitles | ✅ | Elemento `#sub-text` en DOM |
| Muted indicator | ✅ | "🔇 Sin audio — toca la pantalla" visible |

### Console logs (observados)
```
🐛 Dev mode (URL)
load c99b62bd
autoplay blocked: play() failed because the user didn't interact with the document first.
preloaded: 81c6849d
```

**No hay errores JS.** Autoplay bloqueado es comportamiento esperado del browser (requiere interacción del usuario).

---

## 3. Paquetes generados

| ID | Duración | Script (resumen) |
|----|----------|-------------------|
| `c99b62bd` | ~27s | Primer video cargado |
| `b6c5cd6b` | 28.2s | WorldParticle, RigidFormer, BGE-m3 |
| `81c6849d` | ~31s | Preload listo para siguiente |

---

## 4. Assets disponibles

- **Gameplay**: primary.mp4, secondary.mp4, bg1.mp4, bg2.mp4, bg3.mp4 (5)
- **Música**: synthwave.mp3, music.mp3, music2.mp3, music1.mp3 (4)

---

## 5. Issues detectados

| Issue | Severidad | Detalle |
|-------|-----------|---------|
| Autoplay bloqueado | 🟡 Media | Chrome bloquea autoplay sin interacción. El botón "🔇" da instrucciones pero requiere tap del usuario. Esperado pero puede confundir en primera carga. |
| Tooltips/instrucciones ausentes | 🟢 Baja | El hint "↑ abajo historia · ↑ arriba siguiente" se ve, pero no hay indicación visual de que hay que tocar para activar audio. |
| Hover states no probables | - | Sin mouse en mobile, OK. |

---

## Próximas pruebas planificadas

1. Swipe up/down navigation (tocar elementos con las coordenadas)
2. Style panel: cambiar voice, aplicar, verificar
3. Preload: confirmar que el preload funciona entre videos
4. History: swipe down para volver atrás
5. Loop toggle
