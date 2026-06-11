---
name: video-maker
description: "Genera videos cortos con texto, color de fondo y audio. Usa ffmpeg. Produce clips MP4 para el reproductor web."
---

> **Protocol**: You MUST follow the Universal Agent Protocol in `orquestar-agentes/protocol.md` (READ → ACT → VERIFY) before and after every action.


# Video Maker

Generas videos cortos a partir de texto usando `ffmpeg`. Cada video tiene fondo de color, texto centrado, y audio de tono.

## Cómo generar un video

```bash
# Desde el script instalado:
video-maker "texto del video" /tmp/video-cache/mi-video.mp4 10

# O directo con ffmpeg:
ffmpeg -y -f lavfi -i "color=c=#1a1a2e:s=1280x720:d=10" \
  -f lavfi -i "sine=frequency=440:duration=10" \
  -filter_complex "drawtext=text='Hola':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.5:boxborderw=20" \
  -c:v libx264 -preset ultrafast -c:a aac -shortest output.mp4
```

## Streaming (segmentos)

Los videos se guardan en `/tmp/video-cache/`. El web dashboard los detecta automáticamente y los muestra en un reproductor. Para streaming, genera segmentos cortos (5-10s) que el browser reproduce en secuencia.

## Output

- Formato: MP4 (H.264 + AAC)
- Resolución: 1280x720
- Los archivos se sirven vía `/api/video/` en el web dashboard
