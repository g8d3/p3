# 🎛️ Video Console

Consola de producción de videos tutoriales para OpenCode.
Cada comando está pre-testado — no requiere calcular filtros ffmpeg.

## Requisitos

- ffmpeg, ffprobe
- Node.js 20+
- `INWORLD_API_KEY` en el entorno
- `@inworld/tts` (`npm install @inworld/tts`)

## Instalación

```bash
npm install @inworld/tts
export INWORLD_API_KEY="tu-api-key"
chmod +x bin/video bin/tts-inworld.js
```

## Flujo típico (5s intro)

```bash
cd video-console

video init intro 5
video bg                        # Fondo oscuro animado
video tts "Magic Context. Tu agente con memoria infinita."  # Voz Rafael español
video music                     # Música ambiental drone
video code "> import magic_context" "> ctx.cache.enable()"  # Código sutil al fondo
video title "MAGIC" "CONTEXT"   # Título split con sombra
video sub "Cache-aware | Cross-session"  # Subtítulo
video footer "github.com/cortexkit/magic-context"  # Link inferior
video sfx whoosh 1100 0.5      # Whoosh a 1.1s
video sfx click 1500 0.5       # Click a 1.5s
video render                    # Exporta output/final.mp4
```

## Referencia rápida

| Comando | Descripción | Probado |
|---------|-------------|---------|
| `init <name> [dur]` | Crear proyecto | ✓ |
| `bg [dur]` | Background animado | ✓ v5.1 |
| `title "A" "B" [s]` | Título split | ✓ v5.1 |
| `sub "texto" [s]` | Subtítulo centrado | ✓ v5.1 |
| `footer "texto" [s]` | Texto inferior | ✓ v5 |
| `code <line> [...]` | Código al fondo | ✓ v5.1 |
| `tts "texto"` | TTS (Rafael español) | ✓ v5.1 |
| `sfx <tipo> <ms> [vol]` | Efecto de sonido | ✓ v5.1 |
| `music` | Música ambiental | ✓ v5 |
| `render [output]` | Exportar video | ✓ v5.1 |
| `status` | Estado del proyecto | ✓ |
| `list-sfx` | Efectos disponibles | ✓ |
| `list-voices` | Voces español | ✓ |

## Voces español verificadas

- **Rafael** — Profunda, compuesta. Ideal narración. ✓ TESTED
- Sofia — Rápida, clara, neutro latino
- Mateo — Joven, ritmo moderado
- Miguel — Calma, storytelling

## SFX disponibles

- **whoosh** (0.5s) — Transición energética
- **click** (0.05s) — Interfaz, sutil
- **pop** (0.15s) — Aparición juguetona

## Arquitectura

```
video-console/
├── bin/
│   ├── video              # CLI principal
│   └── tts-inworld.js     # TTS con Inworld AI
├── lib/
│   ├── ffmpeg.sh          # Funciones ffmpeg pre-testadas
│   └── project.sh         # Gestión de proyectos JSON
├── assets/sfx/            # Efectos de sonido
├── build/                 # Archivos temporales
├── output/                # Videos finales
└── project.json           # Estado del proyecto
```
