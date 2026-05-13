# Video Tutorial Production Library

Librería de comandos para producción rápida de videos tutoriales con OpenCode + Qwen 3.5 Plus.

## Estructura

```
video-lib/
├── bin/                    # Scripts ejecutables
│   ├── record              # Grabar pantalla
│   ├── tts                 # Text-to-speech
│   ├── sfx                 # Efectos de sonido
│   ├── vfx                 # Efectos visuales
│   ├── transition          # Transiciones
│   ├── broll               # Insertar B-roll
│   └── render              # Renderizar video final
├── assets/                 # Recursos multimedia
│   ├── sfx/                # Efectos de sonido
│   ├── vfx/                # Efectos visuales
│   ├── transitions/        # Transiciones
│   └── broll/              # Footage B-roll
├── scripts/                # Scripts de automatización
│   ├── intro.sh            # Video introductorio (5-10s)
│   ├── demo.sh             # Demo de herramienta
│   └── outro.sh            # Cierre
├── config/                 # Configuración
│   ├── inworld.json        # Inworld AI config
│   └── render.json         # Render settings
└── output/                 # Videos generados
```

## Uso Rápido

```bash
# Video introductorio de 5-10 segundos
./scripts/intro.sh "Magic Context" "Gestión de contexto para IA"

# Grabar sesión
./bin/record --session magic-context-demo

# Generar TTS
./bin/tts --text "Hola, hoy exploraremos..." --output voiceover.mp3

# Añadir efecto de sonido
./bin/sfx --name click --at 00:00:05 --output project.mp4

# Renderizar final
./bin/render --input project.mp4 --output final.mp4
```

## Inworld AI TTS

Configura tu API key en `config/inworld.json`:

```json
{
  "api_key": "tu-api-key",
  "model": "economic-model-id",
  "voice": "narrator"
}
```
