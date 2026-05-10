> Lee templates/arbol-tareas.md para el formato de reporte (incluye arbol_tareas).
# 🔊 Grupo C — Audio Profesional (TTS + Música + SFX)

## Enfoque
Diseño de sonido completo: voz en off multilingüe, música de fondo dinámica y efectos de sonido sincronizados. Este grupo puede trabajar independientemente (generando solo el audio) o en conjunto con otros grupos (produciendo la banda sonora para sus videos).

## Herramientas principales
- **TTS Chutes** (skill de pi) → Voiceover realista en múltiples idiomas
- **FFmpeg** → Mezcla, edición, efectos de audio
- **Sox** → Procesamiento de audio avanzado
- **agent-browser** → Para acceder a generadores de música/SFX online

## Variaciones que genera este grupo
1. `audio_a.mp3` — Voz en off + música + SFX (español, voz masculina)
2. `audio_b.mp3` — Misma producción pero en inglés
3. `audio_c.mp3` — Misma producción pero en portugués
4. `audio_d.mp3` — Solo música y SFX (sin voz) — versión ambiental
5. `audio_e.mp3` — Misma voz pero con diferente música (más enérgica)

## Flow

### Fase 1: Leer especificación
Lee `escenas.yaml` para entender:
- Texto del diálogo (TTS) por escena
- Estilo musical sugerido
- Efectos de sonido necesarios
- Timing de cada escena

### Fase 2: Generar TTS (Voz en off)
Usa el skill `tts-chutes` para generar la voz:
```bash
# Cargar el skill first
# El skill está en /home/vuos/.agents/skills/tts-chutes/SKILL.md
# Sigue sus instrucciones para generar TTS
```

Por cada escena, genera el audio TTS:
```bash
tts-chutes generate --text "Hace 13.8 mil millones de años..." \
  --voice "es_ES_01" --output "output/audio/escena1_tts.wav"
```

**Variaciones de voz:**
- `es_ES_01` — Español España, masculino
- `es_MX_01` — Español México, femenino
- `en_US_01` — Inglés US, masculino
- `en_US_02` — Inglés US, femenino
- `pt_BR_01` — Portugués Brasil
- `fr_FR_01` — Francés

### Fase 3: Generar o descargar música
Para cada escena, genera o descarga música que coincida con el estilo:

**Opción 1: Generar con IA**
```bash
agent-browser open "https://huggingface.co/spaces/facebook/musicgen"
agent-browser snapshot -i
# Prompt: "épica orquestal crescendo, cinematic trailer music"
```

**Opción 2: Usar biblioteca local**
```bash
# Busca en ~/music/ o descarga de fuentes libres de derechos
```

**Opción 3: Generar con FFmpeg (sintetizador simple)**
```bash
# Ritmo electrónico simple
ffmpeg -f lavfi -i "anoisesrc=d=10:c=pink:a=0.3" -af \
  "atempo=1.5,volume=0.5" output/audio/musica_ambiente.wav
```

### Fase 4: Generar efectos de sonido (SFX)

**Opción 1: Sintetizar con FFmpeg**
```bash
# Whoosh (transiciones)
ffmpeg -f lavfi -i "sine=frequency=200:duration=0.3,sine=frequency=800:duration=0.3" \
  -filter_complex "[0:a]acrossfade=d=0.1[out]" -map "[out]" whoosh.wav

# Impacto
ffmpeg -f lavfi -i "anoisesrc=d=0.2:c=brown:a=1" impacto.wav

# Rumble profundo
ffmpeg -f lavfi -i "sine=frequency=60:duration=2" -af "volume=0.8" rumble.wav

# Risers (tensión creciente)
ffmpeg -f lavfi -i "sine=frequency=100:duration=2" -af \
  "volume=0.3,afade=t=in:st=0:d=0.5,afade=t=out:st=1.5:d=0.5" riser.wav
```

### Fase 5: Mezclar todo
```bash
# Por escena: TTS + música + SFX
ffmpeg -i escena1_tts.wav -i escena1_musica.wav -i escena1_sfx.wav \
  -filter_complex "[0:a]volume=1.0[tts];[1:a]volume=0.3[mus];[2:a]volume=0.8[sfx];
   [tts][mus][sfx]amix=inputs=3:duration=first[out]" -map "[out]" escena1_final.wav

# Concatenar todas las escenas
ffmpeg -f concat -safe 0 -i escenas_audio.txt -c copy output/renders/audio_final.wav
```

### Fase 6: Exportar variaciones
```bash
cp output/renders/audio_final.wav output/renders/audio_a_es.wav
# Generar variaciones cambiando TTS
```

## Checklist de calidad interna
- [ ] El TTS es claro y con entonación natural
- [ ] La música cambia de estilo según la escena
- [ ] Los SFX están sincronizados con transiciones y acciones
- [ ] El volumen de TTS > música (la música no tapa la voz)
- [ ] Hay SFX en cada transición entre escenas
- [ ] El audio masterizado suena balanceado

## Al terminar

### 1. Escribe el reporte JSON
Crea `/home/vuos/code/p3/s51/reportes/audio.json`:
```bash
cat > /home/vuos/code/p3/s51/reportes/audio.json << 'EOF'
{
  "agente": "audio",
  "grupo": "C",
  "fecha": "$(date -Iseconds)",
  "sesion": "video-001",
  "resumen": "CANTIDAD pistas de audio generadas",
  "variaciones": [
    {
      "id": "audio_a_es.wav",
      "idioma": "es",
      "voz": "es_ES_01",
      "musica": "épica orquestal",
      "sfx": ["whoosh", "impacto", "rumble"],
      "duracion": 60,
      "calidad": "44100Hz stereo"
    }
  ],
  "metricas": {
    "idiomas": ["es", "en", "pt"],
    "voces_usadas": ["es_ES_01", "en_US_01", "pt_BR_01"],
    "sfx_generados": 15,
    "archivos_generados": ["output/renders/audio_a_es.wav"]
  },
  "errores": []
}
EOF
```

### 2. Actualiza progress.md
```markdown
## Grupo C - Audio - {fecha}
- Variaciones generadas: {lista}
- Idiomas: español, inglés, portugués
- Reporte: reportes/audio.json
- Estado: ✅ Completado
```
