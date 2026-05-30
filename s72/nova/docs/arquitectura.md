# video-templator: Documentación de Arquitectura

## Problemas encontrados y soluciones

### 1. Audio silencioso después de X segundos
- **Causa**: `-shortest` en ffmpeg no funcionaba correctamente con `amix`.
- **Solución**: Probamos la duración de la narración con ffprobe y usamos `-t` en el input de video para recortarlo exactamente.

### 2. Subtítulos cortados en mitad de oración
- **Causa**: edge-tts elimina signos de puntuación. Intentar dividir por palabras clave era frágil.
- **Solución**: Dividir por **pausas temporales** entre palabras (~875ms = límite de oración). Para oraciones largas, escanear hacia atrás desde el límite para evitar terminar en preposiciones.

### 3. Números escritos como texto
- **Solución**: Escribir scripts con dígitos (16% en vez de "dieciséis por ciento").

### 4. Doble pantalla no se notaba
- **Solución**: Eliminar PiP, usar una sola pantalla con gameplay de alta calidad.

### 5. Variedad de contenido
- **Solución**: Sistema de assets aleatorios (`random_gameplay()`, `random_music()`).
- Descargamos 3 gameplays distintos y 4 pistas de música.

## Arquitectura actual

```
render_v2.py (script con datos reales)
  └─ GamingTemplate.render()
       ├─ generate_narration() → audio.mp3 + word timestamps
       ├─ save_ass() → subtitles.ass con karaoke (\K)
       └─ FfmpegCompositor.compose()
            ├─ Prob narración duración → -t en video
            ├─ scale + crop a 1080×1920
            ├─ ass filter (subtítulos quemados)
            ├─ volume + amix (narración + música)
            └─ encoding H264 + AAC
```

## Hacia una app en tiempo real

Para permitir que un usuario varíe en tiempo real:
- Canciones
- Videos de fondo
- Subtítulos (tamaño, posición, color)
- Volumen, calidad, fuente

### Componentes necesarios

| Componente | Tecnología sugerida | Notas |
|---|---|---|
| **Frontend UI** | Streamlit o Gradio (rápido) / Next.js (profesional) | Sliders para volumen, dropdown para assets, preview de subtítulos |
| **Cola de render** | Celery + Redis o ASGI background tasks | El render tarda 30-60s, no puede ser síncrono |
| **Template engine** | Esta librería (`video_templator`) | Ya soporta configuración por `TemplateConfig` |
| **Preview** | ffmpeg `-ss` para thumbnail + player HTML5 | Mostrar frame representativo mientras se renderiza |
| **Caché** | Disco con hash del contenido | Si el usuario cambia solo volumen, reusar video y re-mezclar audio |

### Flujo de la app

```
Usuario elige:
  - Script (o lo genera LLM)
  - Gameplay background
  - Música
  - Tamaño subtítulos (slider)
  - Volumen música (slider)
  - Voz TTS
       │
       ▼
  Backend inicia render:
    POST /render → task_id
    GET  /status/:id → progreso
    GET  /download/:id → video final
       │
       ▼
  Mientras tanto: preview del frame actual cada 5s
```

### Lo más complejo

1. **Render asíncrono**: ffmpeg corre 30-60s. No bloquear el request. Usar Celery o hilos.
2. **Variación de subtítulos sin re-render completo**: Si solo cambia el tamaño de fuente, ¿re-generar solo el ASS y re-quemar? ffmpeg puede hacer esto rápido si el video ya está renderizado sin subtítulos.
3. **Streaming progresivo**: Que el usuario pueda ver el video mientras se termina de renderizar (ffmpeg a HLS).

### Prioridad de implementación

1. MVP con Streamlit (1-2 días)
2. Cola de render con Celery (1-2 días)  
3. Preview durante render (1 día)
4. Caché inteligente (1 día)
5. UI pulida con Next.js (1 semana)

El MVP en Streamlit se puede tener funcionando en muy poco tiempo porque la librería ya tiene toda la lógica.
