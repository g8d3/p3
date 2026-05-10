# 📊 Sistema de Reportes JSON

## El problema
La salida de pi es una cascada de texto enorme (tool calls, pensamientos, resultados). Difícil de leer, filtrar, ordenar.

## La solución
Cada agente, al terminar, escribe un archivo `reporte.json` estructurado en `reportes/`. Luego usamos un visor para ver los datos como tabla.

## Formato del reporte JSON

Cada reporte sigue este esquema:

```json
{
  "agente": "director",
  "fecha": "2026-05-04T12:00:00Z",
  "sesion": "video-001",
  "resumen": "Video sobre el Big Bang, 60s, 6 escenas",
  "resultados": [
    {
      "tipo": "escena",
      "id": 1,
      "descripcion": "Big Bang - Explosión de energía",
      "duracion_seg": 8,
      "camara": "zoom out explosivo",
      "iluminacion": "explosión brillante",
      "transicion": "fundido a negro",
      "sfx": ["explosión", "rumble"],
      "estado": "ok"
    }
  ],
  "metricas": {
    "duracion_total": 60,
    "escenas": 6,
    "archivos_generados": ["escenas.yaml"]
  },
  "errores": []
}
```

Para grupos que producen videos:

```json
{
  "agente": "remotion",
  "grupo": "A",
  "fecha": "2026-05-04T12:30:00Z",
  "sesion": "video-001",
  "resumen": "3 variaciones cinematicas generadas con Remotion",
  "variaciones": [
    {
      "id": "video_a1.mp4",
      "estilo": "cinematic",
      "duracion": 60,
      "resolucion": "1920x1080",
      "fps": 24,
      "tamaño_mb": 245,
      "transiciones_usadas": ["fundido", "barrido", "zoom", "glitch"],
      "movimientos_camara": ["zoom in", "pan", "dolly", "fly-through"],
      "sfx_por_transicion": true,
      "musica": "épica orquestal",
      "tts_idioma": "es",
      "puntuacion_calidad": 8.5
    }
  ],
  "metricas": {
    "tiempo_renderizado_min": 12,
    "archivos_generados": ["video_a1.mp4", "video_a2.mp4", "video_a3.mp4"],
    "escenas_procesadas": 6
  },
  "errores": []
}
```

## Cómo usar en los agentes

Cada archivo de tarea (`agentes/*.md`) ya incluye al final instrucciones para escribir el reporte. El agente debe:

1. Al comenzar: leer el último `reportes/director.json` para saber qué hacer
2. Al terminar: escribir su reporte en `reportes/{agente}.json`

## Visor de terminal

```bash
# Ver todos los reportes como tabla
bash tools/visor.sh

# Ver solo un agente
bash tools/visor.sh director

# Ver solo variaciones de video
bash tools/visor.sh --variaciones

# Follow mode (actualiza cada 5s)
bash tools/visor.sh --follow
```

## Visor web

Abre `tools/visor.html` en el browser con `agent-browser` o simplemente `termux-open`:
```bash
termux-open tools/visor.html
```
