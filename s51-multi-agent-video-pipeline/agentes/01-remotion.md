> Lee templates/arbol-tareas.md para el formato de reporte (incluye arbol_tareas).
# 🎞️ Grupo A — Cinematic (Remotion + Audio Pro)

## Enfoque
Videos de alta calidad cinematográfica con transiciones suaves, cámara programática y audio profesional.

## Herramientas principales
- **Remotion** → Renderizado frame por frame con React
- **FFmpeg** → Post-procesado (color grading, estabilización)
- **TTS Chutes** → Voiceover profesional

## Variaciones que genera este grupo
Cada corrida produce MÚLTIPLES variaciones:
1. `video_a1.mp4` — Estilo cinematic clásico (24fps, letterbox, grano)
2. `video_a2.mp4` — Estilo vaporwave (colores neón, glitch, retro)
3. `video_a3.mp4` — Estilo documental (colores naturales, cámara en mano)
4. `video_a4.mp4` — Estilo kinetic typography (texto animado dominante)

## Flow

### Fase 1: Setup de Remotion
```bash
cd /home/vuos/code/p3/s51
npx create-video@latest --template blank output/remotion_project
```

### Fase 2: Leer especificación
Lee `escenas.yaml` en `/home/vuos/code/p3/s51/templates/escenas.yaml`

### Fase 3: Generar componentes React por escena
Cada escena es un componente React con:
- `<Sequence>` de Remotion para duración
- `useCurrentFrame()` para animaciones
- `spring()` para movimientos de cámara suaves
- Transiciones CSS personalizadas
- Overlays de texto, partículas, efectos

### Fase 4: Renderizar
```bash
cd output/remotion_project && npx remotion render src/index.ts ../renders/video_a1.mp4
```

### Fase 5: Post-procesar con FFmpeg
```bash
# Color grading cinematic (teal/orange)
ffmpeg -i video_a1.mp4 -vf "eq=contrast=1.2:brightness=0.05:saturation=1.1" \
  -af "volume=1.2" video_a1_graded.mp4

# Añadir letterbox (barras negras)
ffmpeg -i video_a1.mp4 -vf "pad=iw:ih+120:0:60:black" video_a1_final.mp4
```

### Fase 6: Exportar
Copia el video final a:
```
/home/vuos/code/p3/s51/output/renders/video_a_{estilo}.mp4
```

## Tips para este grupo
- Usa `@remotion/transitions` para transiciones fluidas
- Para cámara: combina `interpolate()` con `spring()` para movimientos naturales
- La música debe ir en un `<Audio>` tag de Remotion
- Subtítulos: usa `@remotion/captions` o `react-native-style` para animación de texto
- Genera múltiples variaciones cambiando: paleta de colores, velocidad de cámara, tipografía

## Checklist de calidad interna (antes de exportar)
- [ ] Cada escena tiene movimiento de cámara
- [ ] Las transiciones son variadas (mínimo 3 tipos diferentes)
- [ ] Hay TTS sincronizado
- [ ] Hay música de fondo
- [ ] Hay al menos 1 efecto de sonido por transición
- [ ] El ritmo es dinámico (cada 3-5s hay un cambio)
- [ ] La iluminación varía entre escenas

## Al terminar

### 1. Escribe el reporte JSON
Crea `/home/vuos/code/p3/s51/reportes/remotion.json`:
```bash
cat > /home/vuos/code/p3/s51/reportes/remotion.json << 'EOF'
{
  "agente": "remotion",
  "grupo": "A",
  "fecha": "$(date -Iseconds)",
  "sesion": "video-001",
  "resumen": "3 variaciones generadas con Remotion",
  "variaciones": [
    {
      "id": "video_a1.mp4",
      "estilo": "cinematic",
      "duracion": 60,
      "resolucion": "1920x1080",
      "fps": 24,
      "tamaño_mb": 245,
      "transiciones_usadas": ["fundido", "barrido", "zoom", "glitch"],
      "movimientos_camara": ["zoom in", "pan", "dolly"],
      "sfx_por_transicion": true,
      "musica": "épica orquestal",
      "tts_idioma": "es",
      "puntuacion_calidad": 8.5
    }
  ],
  "metricas": {
    "tiempo_renderizado_min": 12,
    "archivos_generados": ["output/renders/video_a1.mp4"],
    "escenas_procesadas": 6
  },
  "errores": []
}
EOF
```

### 2. Actualiza progress.md
```markdown
## Grupo A - Cinematic - {fecha}
- Variaciones generadas: {lista}
- Tool: Remotion
- Estilos: cinematic, vaporwave, documental, kinetic
- Reporte: reportes/remotion.json
- Estado: ✅ Completado
```
