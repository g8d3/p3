# video-templator

AI-powered video template engine. Create videos fast using templates, TTS, and ffmpeg.

## Features

- **Narration + subtitles** — `edge-tts` generates audio and word-level timestamps in one call (free, no GPU, no API key)
- **Karaoke highlighting** — ASS subtitles highlight the current spoken word
- **Smart subtitle grouping** — words grouped into readable blocks with correct timing
- **Dual-screen / PiP** — picture-in-picture secondary gameplay
- **Background music** — auto-mixed with narration
- **No GPU required** — everything runs on CPU

## Quick start

```python
import asyncio
from video_templator import GamingTemplate

template = GamingTemplate()

asyncio.run(template.render(
    script="Hoy vamos a explorar las ruinas más peligrosas del mapa.",
    gameplay_primary="gameplay.mp4",
    output="video_final.mp4",
    voice="es-MX-DaliaNeural",           # Spanish (Mexican)
    subtitle_format="ass",               # karaoke word highlighting
))
```

## Pipeline

```
Script (text) ──► edge-tts ──► Audio mp3 + word timestamps
                                       │
                                       ▼
                              Subtitle grouper ──► SRT or ASS
                                       │
                                       ▼
                              ffmpeg compositor ──► Final video
                                       ▲
                              Gameplay clips + music
```

## Templates

| Template | Description |
|----------|-------------|
| `GamingTemplate` | ReVid-style: fullscreen gameplay + optional PiP + bottom subtitles + narration |

## Installation

```bash
pip install edge-tts moviepy pillow
# ffmpeg must be installed on your system
```

## Advanced usage

```python
from video_templator import (
    GamingTemplate,
    TemplateConfig,
)

config = TemplateConfig(
    width=1920,
    height=1080,
    subtitle_font="Montserrat-Bold",
    subtitle_font_size=48,
    max_words_per_block=4,
    pip_width=540,
    bg_music_volume=0.10,
)

template = GamingTemplate(config)
await template.render(
    script="...",
    gameplay_primary="main.mp4",
    gameplay_secondary="pip.mp4",    # picture-in-picture
    bg_music="bg_music.mp3",         # background music
    subtitle_format="srt",           # plain subtitles (no highlighting)
)
```
