# Plan: Exploración de herramientas de producción de video

## Objetivo
Encontrar la herramienta que nos permita crear videos tutoriales desde la terminal con:
- Screen recording / browser recording
- TTS (Text-to-Speech)
- Efectos de sonido
- Efectos visuales / texto overlay
- Transiciones
- B-roll insertion
- Pipeline automatizado (script → video)

## Herramientas a explorar (en orden)

### 1. VibeFrame (`vericontext/vibeframe`)
- **Tipo:** CLI + MCP Server
- **Stack:** Node.js, ffmpeg, Hyperframes
- **Estado:** Activo (v0.99.0)
- **Por qué:** Hecho para AI agents, CLI-first, MCP-ready, soporta OpenCode
- **URL:** https://github.com/vericontext/vibeframe

### 2. script-to-video (`telegraph/s2v`)
- **Tipo:** CLI
- **Stack:** Node.js, ffmpeg, Edge TTS
- **Estado:** Activo
- **Por qué:** Slides + narración, 45+ transiciones, QA validation
- **URL:** https://github.com/telegraph/script-to-video

### 3. neurascreen (`NEURASCOPE/neurascreen`)
- **Tipo:** CLI + GUI
- **Stack:** Python, Playwright, ffmpeg
- **Estado:** Activo
- **Por qué:** JSON scenario → browser real + TTS → MP4
- **URL:** https://github.com/NEURASCOPE/neurascreen

## Progreso

- [x] Investigación inicial
- [x] **Fase 1: VibeFrame** — Instalado, explorado, testeado ✓
- [x] **Video v1-v4 creados** — Evolución de 4/10 a 43/50
- [x] **Retroalimentación multi-modelo** — Gemini + GPT-4o analizaron video de referencia
- [ ] **Fase 2: script-to-video** — Instalar, explorar comandos, crear intro de 5s
- [ ] **Fase 3: neurascreen** — Instalar, explorar comandos, crear intro de 5s
- [ ] **Decisión final** — Elegir la mejor para el flujo de video tutoriales

## Fase 1: VibeFrame — Conclusiones

### Estado: ✅ Funcional

### Lo que hace bien:
- **Storyboard pipeline**: `vibe init → vibe build → vibe render` produce videos completos desde un brief
- **TTS gratuito**: Kokoro TTS local (sin API key), generó 3 archivos WAV impecables
- **Comandos de edición gratuitos**: fade, silence-cut, noise-reduce, text-overlay, interpolate (todos ffmpeg, sin API key)
- **MCP Server**: Se puede conectar como herramienta MCP desde OpenCode
- **OpenCode support**: Genera SKILL.md y AGENTS.md específicos para OpenCode
- **Composición**: Usa Hyperframes (HTML/CSS/JS + GSAP animations) para escenas

### Lo que necesita API keys:
- **Backdrop images**: OpenAI DALL-E (~$3 c/u, se puede skip con `--skip-backdrop`)
- **Narración standalone** (`vibe generate narration`): ElevenLabs
- **Sound effects** (`vibe generate sound-effect`): ElevenLabs
- **Caption/transcribe**: OpenAI Whisper
- **Color grading, reframe**: Claude/Anthropic

### Comandos probados:
```bash
vibe init test-video --from "brief" -d 5 -r 16:9  # Crear proyecto
vibe build . --skip-backdrop                        # Build sin imágenes (solo TTS + HTML)
vibe storyboard validate .                          # Validar storyboard
```

### Limitaciones:
- La generación de imágenes de backdrop requiere API keys pagas
- Scene composition requiere autoría de HTML (Hyperframes) que necesita un agente LLM
- No hay screen recording built-in
- Pipeline completo requiere mínimo: Kokoro TTS (gratis) + autoría de composiciones

## Estrategia híbrida propuesta:
Combinar VibeFrame (storyboard, TTS, planning) con nuestros scripts ffmpeg (video-lib/) para:
- `produce intro` → usar `vibe generate narration` (Kokoro via build) + ffmpeg
- `produce demo` → VibeFrame para plan y assets + screen recording externo
- Edits rápidos gratis → `vibe edit fade`, `vibe edit text-overlay`, `vibe edit noise-reduce`

## Notas
- Usar DeepSeek como modelo base (el user cambió de Inworld a DeepSeek)
- Qwen 3.5 Plus como modelo de razonamiento en OpenCode
- Los scripts deben ejecutarse rápidamente "sin pensar" durante la grabación
