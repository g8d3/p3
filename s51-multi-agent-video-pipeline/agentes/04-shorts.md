> Lee templates/arbol-tareas.md para el formato de reporte (incluye arbol_tareas).
# ⚡ Grupo D — Shorts Automáticos (ShortGPT)

## Enfoque
Pipeline completo para shorts/TikTok/Reels. Automatización desde el guión hasta el video final, optimizado para ritmo rápido y retención de atención.

## Herramientas principales
- **ShortGPT** → Framework de automatización de shorts
- **TTS Chutes** → Voiceover multilingüe
- **FFmpeg** → Post-procesado rápido
- **agent-browser** → Acceso a APIs de generación

## Variaciones que genera este grupo
1. `video_d1.mp4` — Short estándar (español, voz masculina, estilo informativo)
2. `video_d2.mp4` — Short en inglés (voz femenina, estilo entretenimiento)
3. `video_d3.mp4` — Short con subtítulos grandes (kinetic typography)
4. `video_d4.mp4` — Short con ritmo ultra-rápido (cada 2s cambia)
5. `video_d5.mp4` — Short con música electrónica de fondo (estilo TikTok)

## Flow

### Fase 1: Leer especificación
Lee `escenas.yaml` y adapta el contenido al formato short:
- Duración objetivo: 15-60 segundos
- Formato: 9:16 (vertical)
- Ritmo: cambios cada 2-4 segundos
- Gancho en primeros 3 segundos

### Fase 2: Configurar ShortGPT
```bash
cd /home/vuos/code/p3/s51
# Si ShortGPT está instalado
pip install shortgpt 2>/dev/null || true
```

### Fase 3: Generar script optimizado para shorts
Convierte el guión del director a formato short:
```
[HOOK 0-3s]
"¡El universo comenzó con una explosión!" 
▸ Visual: Big Bang + zoom out rápido + whoosh sfx

[CONTENT 3-10s]
"Las primeras estrellas iluminaron el cosmos..."
▸ Visual: Nebulosas + pan + música épica

[CONTENT 10-20s]
"Nuestra galaxia tiene 100 mil millones de estrellas..."
▸ Visual: Vía Láctea + fly-through + transición glitch

[CTA 20-25s]
"Sígueme para más historias cósmicas 🚀"
▸ Visual: Tierra desde órbita + zoom in + logo
```

### Fase 4: Generar variaciones con ShortGPT
```bash
# ShortGPT genera automáticamente:
# - TTS con la voz seleccionada
# - Búsqueda de videos/imágenes de stock
# - Subtítulos automáticos
# - Música de fondo
# - Edición con ritmo

shortgpt create --script script_shorts.txt --style informativo --output output/renders/video_d1.mp4
```

### Fase 5: Post-procesado manual con FFmpeg
```bash
# Añadir efectos extra si es necesario
# Recorte vertical si no está en 9:16
ffmpeg -i video_d1.mp4 -vf "crop=ih*9/16:ih" output/renders/video_d1_crop.mp4

# Añadir barra de progreso (típica de YouTube Shorts)
# Añadir like/subscribe animation
```

### Fase 6: Generar múltiples variaciones
```bash
# Variación 1: Informativo español
shortgpt create --script script_shorts.txt --voice es_ES_01 --style informativo ...

# Variación 2: Entretenimiento inglés
shortgpt create --script script_shorts_en.txt --voice en_US_02 --style entretenimiento ...

# Variación 3: Ultra rápido
shortgpt create --script script_shorts.txt --pace ultra-fast ...
```

## Tips para retención de atención en shorts
1. **Hook en 0-1s**: Primer frame debe ser impactante
2. **Cambio cada 2-3s**: Nuevo visual, nuevo ángulo, nuevo SFX
3. **Subtítulos grandes**: Que ocupen 30% de la pantalla
4. **Música con beat**: Cortes sincronizados con el ritmo
5. **CTA al final**: "Like", "Sígueme", "Comenta X"

## Checklist de calidad
- [ ] Hook en primeros 3 segundos (texto + visual + SFX)
- [ ] Ritmo rápido: cambio cada 2-4 segundos
- [ ] Subtítulos claros y sincronizados
- [ ] Música de fondo presente
- [ ] Efectos de sonido en cada transición
- [ ] Formato vertical 9:16
- [ ] CTA al final

## Al terminar

### 1. Escribe el reporte JSON
Crea `/home/vuos/code/p3/s51/reportes/shorts.json`:
```bash
cat > /home/vuos/code/p3/s51/reportes/shorts.json << 'EOF'
{
  "agente": "shorts",
  "grupo": "D",
  "fecha": "$(date -Iseconds)",
  "sesion": "video-001",
  "resumen": "CANTIDAD shorts generados",
  "variaciones": [
    {
      "id": "video_c1.mp4",
      "estilo": "informativo",
      "idioma": "es",
      "duracion": 25,
      "fps": 30,
      "resolucion": "1080x1920",
      "ritmo": "normal",
      "subtitulos": true,
      "musica": "electrónica",
      "sfx_por_transicion": true,
      "hook_segundos": 3,
      "puntuacion_calidad": 8.0
    }
  ],
  "metricas": {
    "estilos": ["informativo", "entretenimiento", "ultra-rápido"],
    "idiomas": ["es", "en"],
    "archivos_generados": ["output/renders/video_c1.mp4"]
  },
  "errores": []
}
EOF
```

### 2. Actualiza progress.md
```markdown
## Grupo D - Shorts - {fecha}
- Variaciones generadas: {lista}
- Estilos: informativo, entretenimiento, ultra-rápido
- Reporte: reportes/shorts.json
- Estado: ✅ Completado
```
