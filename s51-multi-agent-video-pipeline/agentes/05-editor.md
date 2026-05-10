> Lee templates/arbol-tareas.md para el formato de reporte (incluye arbol_tareas).
# 🎬 Grupo E — Editor FFmpeg (MoviePy + FFmpeg)

## Enfoque
Edición y post-procesado de video usando pipelines de FFmpeg y MoviePy. Este grupo toma clips existentes (de AI Gen, stock, o grabaciones) y los transforma aplicando efectos, transiciones, color grading, y movimientos de cámara.

## Herramientas principales
- **FFmpeg** → Procesamiento de video por línea de comandos
- **MoviePy** → Edición programática con Python
- **Python** → Scripts de automatización

## Variaciones que genera este grupo
1. `video_e1.mp4` — Estilo documental (colores naturales, transiciones suaves)
2. `video_e2.mp4` — Estilo cinematic (color grading teal/orange, letterbox, grano)
3. `video_e3.mp4` — Estilo TikTok (colores vibrantes, recorte 9:16, subtítulos)
4. `video_e4.mp4` — Estilo vaporwave (neón, glitch, CRT scanlines)
5. `video_e5.mp4` — Estilo acción rápida (speed ramps, cortes rápidos, shake)

## Flow

### Fase 1: Leer especificación
Lee `escenas.yaml` y los clips disponibles en `output/clips/`

### Fase 2: Pipeline de edición con MoviePy
Crea un script Python que procese todas las escenas:

```python
from moviepy.editor import *
from moviepy.video.fx import *

# Cargar clips
clips = []
for escena in escenas:
    clip = VideoFileClip(f"output/clips/escena{escena['id']}.mp4")
    
    # Aplicar movimiento de cámara (Ken Burns / zoom / pan)
    if escena['camara']['movimiento'] == 'zoom in':
        clip = clip.fx(vfx.resize, lambda t: 1 + 0.3*t/clip.duration)
    elif escena['camara']['movimiento'] == 'zoom out':
        clip = clip.fx(vfx.resize, lambda t: 1.3 - 0.3*t/clip.duration)
    elif escena['camara']['movimiento'] == 'pan':
        clip = clip.fx(vfx.scroll, h=100, w=clip.w, x_speed=50)
    
    # Aplicar color grading
    if escena['estilo_visual'] == 'cinematic':
        clip = clip.fx(vfx.colorx, 1.2)  # más contraste
    elif escena['estilo_visual'] == 'vaporwave':
        clip = clip.fx(vfx.colorx, 1.5).fx(vfx.lum_contrast, 0, 50, 0)
    
    # Añadir transición
    # ...
    
    clips.append(clip)

# Concatenar con transiciones
final = concatenate_videoclips(clips, method="compose")
final.write_videofile("output/renders/video_e1.mp4", fps=30)
```

### Fase 3: Pipeline alternativo con FFmpeg puro
Si prefieres FFmpeg directo, usa comandos como estos:

```bash
# Zoom in (Ken Burns) en un clip
ffmpeg -i input.mp4 -vf "zoompan=z='min(zoom+0.002,1.5)':d=150:fps=30" output_zoom.mp4

# Pan lateral
ffmpeg -i input.mp4 -vf "crop=iw/2:ih:iw/2*sin(t/2):0" output_pan.mp4

# Color grading cinematic (teal/orange)
ffmpeg -i input.mp4 -vf "eq=contrast=1.3:brightness=0.1:saturation=1.2:gamma=1.1" \
  -af "volume=1.5" output_graded.mp4

# Glitch effect (frame scrambling)
ffmpeg -i input.mp4 -vf "crop=iw:ih/2:0:0,split[c0][c1];[c0]palettegen[p];[c1][p]paletteuse" \
  -af "volume=1.2" output_glitch.mp4

# Speed ramp (acelerar y ralentizar)
ffmpeg -i input.mp4 -vf "setpts=0.5*PTS" -af "atempo=2.0" output_fast.mp4
```

### Fase 4: Generar variaciones
Cada variación cambia parámetros globales:

```python
# Variations
variations = [
    {"name": "documental", "contrast": 1.0, "saturation": 1.0, "grain": False},
    {"name": "cinematic", "contrast": 1.3, "saturation": 1.1, "grain": True, "letterbox": True},
    {"name": "vaporwave", "contrast": 1.5, "saturation": 1.8, "neon": True, "crt": True},
    {"name": "tiktok", "contrast": 1.2, "saturation": 1.4, "crop": "9:16"},
    {"name": "accion", "speed_ramp": True, "shake": True, "cuts": "fast"},
]

for var in variations:
    apply_pipeline(clips, var)
    output_path = f"output/renders/video_e_{var['name']}.mp4"
```

### Fase 5: Añadir audio
```bash
# Mezclar video editado con audio producido por el Grupo C
ffmpeg -i video_e1.mp4 -i output/renders/audio_a_es.wav \
  -c:v copy -map 0:v:0 -map 1:a:0 -shortest output/renders/video_e1_final.mp4
```

## Biblioteca de efectos FFmpeg

### Transiciones
```bash
# Fundido cruzado entre dos clips
ffmpeg -i clip1.mp4 -i clip2.mp4 -filter_complex \
  "[0:v]fade=t=out:st=5:d=1[v0];[1:v]fade=t=in:st=0:d=1[v1];
   [v0][v1]concat=n=2:v=1:a=0" output_transition.mp4

# Glitch transition (saltar frames)
ffmpeg -i clip1.mp4 -i clip2.mp4 -filter_complex \
  "[0:v]crop=iw:ih/2:0:0,split[c0][c1];[c0]palettegen[p];[c1][p]paletteuse[v0];
   [1:v]vflip[v1];[v0][v1]concat=n=2:v=1:a=0" output_glitch.mp4
```

### Efectos visuales
```bash
# Aberración cromática
ffmpeg -i input.mp4 -vf "split[s1][s2];[s1]chromashift=10:10[s1];[s2]chromashift=-10:-10[s2];[s1][s2]blend=all_mode=addition" output_chromatic.mp4

# Viñeta
ffmpeg -i input.mp4 -vf "vignette=PI/4:max_eval=frame" output_vignette.mp4

# Grano de cine
ffmpeg -i input.mp4 -vf "noise=alls=10:allf=t+u" output_grain.mp4
```

## Checklist de calidad
- [ ] Cada escena tiene movimiento de cámara aplicado
- [ ] Las transiciones son variadas
- [ ] El color grading es coherente con el estilo
- [ ] El ritmo del video es dinámico
- [ ] Los efectos no son excesivos (no distraen)

## Al terminar

### 1. Escribe el reporte JSON
Crea `/home/vuos/code/p3/s51/reportes/editor.json`:
```bash
cat > /home/vuos/code/p3/s51/reportes/editor.json << 'EOF'
{
  "agente": "editor",
  "grupo": "E",
  "fecha": "$(date -Iseconds)",
  "sesion": "video-001",
  "resumen": "CANTIDAD variaciones de edición",
  "variaciones": [
    {
      "id": "video_e1.mp4",
      "estilo": "documental",
      "duracion": 60,
      "fps": 30,
      "resolucion": "1920x1080",
      "transiciones_usadas": ["fundido", "corte directo"],
      "movimientos_camara": ["Ken Burns", "zoom"],
      "color_grading": "natural",
      "efectos_aplicados": ["viñeta", "grano"],
      "puntuacion_calidad": 7.0
    }
  ],
  "metricas": {
    "estilos": ["documental", "cinematic", "vaporwave", "tiktok", "acción"],
    "herramientas": ["FFmpeg", "MoviePy"],
    "archivos_generados": ["output/renders/video_e1.mp4"]
  },
  "errores": []
}
EOF
```

### 2. Actualiza progress.md
```markdown
## Grupo E - Editor - {fecha}
- Variaciones generadas: {lista}
- Estilos: documental, cinematic, vaporwave, tiktok, acción
- Reporte: reportes/editor.json
- Estado: ✅ Completado
```
