> Lee templates/arbol-tareas.md para el formato de reporte (incluye arbol_tareas).
# 🤖 Grupo B — AI Generation (Wan2.2 + HunyuanVideo)

## Enfoque
Generación de clips base usando modelos de IA de última generación. Produce variaciones visuales dramáticas cambiando prompts, semillas y modelos.

## Herramientas principales
- **Wan2.2** → Modelo generativo de video (OpenSora plan)
- **HunyuanVideo** → Framework de generación (Tencent)
- **CogVideo** → Alternativa texto-a-video
- **FFmpeg** → Recorte y ensamblaje de clips

## Variaciones que genera este grupo
1. `video_b1.mp4` — Clips con Wan2.2 (realista)
2. `video_b2.mp4` — Clips con HunyuanVideo (cinematic)
3. `video_b3.mp4` — Clips con estilización artística
4. `video_b4.mp4` — Misma escena con diferentes semillas/ángulos

## Flow

### Fase 1: Leer especificación
Lee `escenas.yaml` en `/home/vuos/code/p3/s51/templates/escenas.yaml`

### Fase 2: Generar prompts para cada modelo
Por cada escena, genera MULTIPLES prompts variando:
- **Estilo**: "realista", "cinematic", "animación 3D", "pintura al óleo", "cyberpunk"
- **Ángulo**: el especificado en escenas.yaml + variaciones
- **Iluminación**: la especificada + variaciones (luz de atardecer, neón, dramática)
- **Movimiento**: el especificado + variaciones (cámara lenta, rápida, estable)

Ejemplo de prompts para una escena:
```
Escena 1 - "Big Bang":
  Prompt Wan2.2: "Explosión cósmica, big bang, energía brillante, partículas 
                  expansivas, cámara cenital zoom out rápido, 8K, cinematic"
  Prompt Hunyuan: "4K cosmic explosion, big bang, bright energy, particles 
                   expanding, top-down camera fast zoom out, cinematic lighting"
```

### Fase 3: Ejecutar generación
```bash
# Wan2.2 (si está instalado localmente o vía API)
cd /home/vuos/code/p3/s51 && python scripts/generate_wan.py \
  --prompt "..." \
  --output output/clips/escena1_wan.mp4

# HunyuanVideo (vía API o local)
python scripts/generate_hunyuan.py \
  --prompt "..." \
  --output output/clips/escena1_hunyuan.mp4
```

Si no tienes acceso local, usa agent-browser para navegar a las APIs web:
```bash
agent-browser open "https://huggingface.co/spaces/Wan-Video/Wan2.1"
```

### Fase 4: Ensamblar clips en secuencia
```bash
# Crear lista de archivos
for f in output/clips/escena*.mp4; do echo "file '$f'" >> clips.txt; done
# Concatenar
ffmpeg -f concat -safe 0 -i clips.txt -c copy output/renders/video_b1.mp4
```

### Fase 5: Post-procesar con FFmpeg
```bash
# Añadir transiciones entre clips
ffmpeg -i output/renders/video_b1.mp4 \
  -vf "fade=t=in:st=0:d=1,fade=t=out:st=58:d=2" \
  -af "afade=t=in:st=0:d=1,afade=t=out:st=58:d=2" \
  output/renders/video_b1_final.mp4
```

## Tips para este grupo
- **Seed variation**: Genera el mismo prompt con 3-5 semillas diferentes y elige la mejor
- **Model variation**: Combina clips de diferentes modelos en un mismo video
- **Style transfer**: Aplica filtros FFmpeg para cambiar el estilo (cartoon, oil paint, etc.)
- Si los modelos no están instalados localmente, usa agent-browser para acceder a demos web
- Guarda los prompts usados en `output/prompts_usados.txt` para reproducibilidad

## Checklist de calidad interna
- [ ] Cada escena tiene al menos 2 variaciones de prompt
- [ ] Los clips generados tienen movimiento visible
- [ ] Las transiciones entre clips son suaves
- [ ] La iluminación varía entre escenas
- [ ] Los prompts especifican ángulo y movimiento de cámara

## Al terminar

### 1. Escribe el reporte JSON
Crea `/home/vuos/code/p3/s51/reportes/aigen.json`:
```bash
cat > /home/vuos/code/p3/s51/reportes/aigen.json << 'EOF'
{
  "agente": "aigen",
  "grupo": "B",
  "fecha": "$(date -Iseconds)",
  "sesion": "video-001",
  "resumen": "CANTIDAD variaciones con IA generativa",
  "variaciones": [
    {
      "id": "video_b1.mp4",
      "estilo": "realista",
      "modelo": "Wan2.2",
      "duracion": 60,
      "resolucion": "1920x1080",
      "fps": 30,
      "prompts_usados": ["Big Bang cósmico..."],
      "movimientos_camara": ["zoom out", "pan"],
      "puntuacion_calidad": 7.5
    }
  ],
  "metricas": {
    "modelos_usados": ["Wan2.2", "HunyuanVideo"],
    "prompts_generados": 12,
    "archivos_generados": ["output/renders/video_b1.mp4"]
  },
  "errores": []
}
EOF
```

### 2. Actualiza progress.md
```markdown
## Grupo B - AI Gen - {fecha}
- Variaciones generadas: {lista}
- Modelos usados: Wan2.2, HunyuanVideo
- Reporte: reportes/aigen.json
- Estado: ✅ Completado
```
