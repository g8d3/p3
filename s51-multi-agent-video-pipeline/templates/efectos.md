# 🎬 Biblioteca de Efectos, Cámara y Transiciones
## Úsala en cualquier agente para generar variaciones

---

## 1. MOVIMIENTOS DE CÁMARA

| Movimiento | Descripción | Cuándo usarlo |
|------------|-------------|---------------|
| **Quiet** | Cámara fija | Solo para planos de impacto |
| **Pan** | Giro horizontal | Para revelar paisajes o seguir acción |
| **Tilt** | Giro vertical | Para revelar altura o profundidad |
| **Dolly** | Cámara se acerca/aleja | Para enfoque dramático |
| **Zoom** | Lente se acerca/aleja | Para énfasis, menos físico que dolly |
| **Ken Burns** | Zoom lento + pan | Para fotos o escenas estáticas |
| **Crane** | Cámara sube/baja | Para grandiosidad |
| **Steadicam** | Cámara sigue a sujeto | Para inmersión |
| **Fly-through** | Cámara vuela entre objetos | Para tours virtuales |
| **Whip Pan** | Pan muy rápido | Para transiciones energéticas |
| **Orbital** | Cámara orbita sujeto | Para mostrar entorno 360° |
| **Snorricam** | Cámara fija al sujeto | Para sensación de movimiento |

### Variaciones de velocidad:
- `lento` (0.25x) → dramático, reflexivo
- `normal` (1x) → natural
- `rápido` (2x) → energético
- `explosivo` (4x+) → caótico, acción
- `speed ramp` → lento→rápido→lento

---

## 2. ÁNGULOS DE CÁMARA

| Ángulo | Efecto |
|--------|--------|
| **Normal** | Neutro, objetivo |
| **Picado** (alta) | Sujeto parece pequeño/débil |
| **Contrapicado** (baja) | Sujeto parece poderoso |
| **Cenital** (90° arriba) | Abstracto, diagrámico |
| **Nadir** (90° abajo) | Desorientador |
| **Dutch angle** (inclinado) | Tensión, inquietud |
| **Primera persona** (POV) | Inmersión total |
| **Over-the-shoulder** | Conversación |
| **Plano detalle** | Énfasis en objeto |

### Combinaciones ganadoras:
- Contrapicado + lento zoom in = poder creciente
- Picado + dolly out = revelación
- Dutch angle + whip pan = caos controlado

---

## 3. TRANSICIONES

| Transición | Tool | Cómo se hace |
|------------|------|-------------|
| **Corte directo** | FFmpeg/Remotion | `-c copy` (lossless) |
| **Fundido a negro** | FFmpeg | `fade=t=out:st=5:d=1` |
| **Fundido desde negro** | FFmpeg | `fade=t=in:st=0:d=1` |
| **Fundido cruzado** | FFmpeg | `xfade=transition:fade` |
| **Barrido** | Remotion | CSS `clip-path` animado |
| **Zoom** | Remotion | Escala + movimiento |
| **Wipe** | FFmpeg | `xfade=transition:wipeleft` |
| **Slide** | Remotion | `translateX` animado |
| **Dissolve** | FFmpeg | `xfade=transition:fade` |
| **Glitch** | FFmpeg/Remotion | frame scrambling + RGB shift |
| **Pixelate** | Remotion | filter CSS + animación |
| **Rotate** | Remotion | rotate 3D |

### Variaciones de transición:
- Transiciones suaves = profesionales
- Transiciones rápidas = energéticas
- Sin transición (corte directo) = documental

---

## 4. ILUMINACIÓN

| Tipo | Descripción | Tool |
|------|-------------|------|
| **High-key** | Brillante, sin sombras | Color grading: subir exposición |
| **Low-key** | Sombras profundas, dramático | Contraste alto, negros profundos |
| **Luz natural** | Suave, difusa | Desaturar ligeramente |
| **Luz dura** | Sombras marcadas | Contraste fuerte |
| **Neón** | Colores brillantes RGB | Curvas de color en forma de S |
| **Dramática** | Claroscuro | Un solo foco de luz |
| **Crepúsculo** | Azul/naranja | Balance de frío/caliente |
| **Luz de abertura** | Desde una ventana | Degradado direccional |
| **Color wash** | Baño de color | Overlay de color + blending |

---

## 5. EFECTOS DE SONIDO ESENCIALES

| Efecto | Cuándo | Archivo sugerido |
|--------|--------|-----------------|
| **Whoosh** | Transiciones, cambios de escena | whoosh_01.wav |
| **Impacto** | Cambios bruscos, golpes | impact_01.wav |
| **Rumble** | Tensión, expectativa | rumble_deep.wav |
| **Rising** | Climax, revelación | rise_01.wav |
| **Stinger** | Giro argumental | sting_01.wav |
| **Ambiente** | Fondo continuo | room_tone.wav |
| **Foley** | Pasos, roces, objetos | foley_step.wav |
| **Naturaleza** | Viento, agua, bosque | nature_forest.wav |
| **Tecnología** | Beeps, clicks, UI | tech_beep.wav |
| **Glitch** | Transiciones glitch | glitch_noise.wav |

### Generación de SFX con IA:
```bash
# Usar tts-chutes o herramientas similares
agent-browser open "https://huggingface.co/spaces/..." 
# O generar con FFmpeg:
ffmpeg -f lavfi -i "sine=frequency=440:duration=0.5" -af "volume=0.5" beep.wav
```

---

## 6. PLANTILLAS DE ESTILO VISUAL

| Estilo | Descripción | Características |
|--------|-------------|-----------------|
| **Cinematic** | Look de cine | 24fps, grano, letterbox, color grading teal/orange |
| **Documental** | Natural, realista | 30fps, colores naturales, cámara en mano suave |
| **Vaporwave** | Retro 80s/90s | Neón, púrpura/rosa, glitch, CRT scanlines |
| **Cyberpunk** | Futuro oscuro | Azul/rojo, neón, lluvia, contraste alto |
| **Animación 2D** | Dibujo animado | Líneas claras, colores planos, motion graphics |
| **Kinetic typography** | Texto animado | Tipografía grande, movimiento sincronizado con TTS |
| **Found footage** | Cámara casera | Grano, aberración cromática, shake |
| **Minimalista** | Limpio, simple | Fondo blanco/negro, formas geométricas |
| **Dark fantasy** | Oscuro, épico | Sombras, partículas, niebla, contraluz |
| **Retro futurista** | Pasado del futuro | Colores pastel, formas redondeadas, gradientes |

---

## 7. RECETAS RÁPIDAS (Combinaciones probadas)

### Receta: "Atención máxima" (para Shorts/Reels)
```
Escena 1 (0-3s): Gancho fuerte
  - Ángulo: Primera persona o contrapicado
  - Cámara: Dolly in rápido
  - Transición: Corte directo + whoosh
  - SFX: Impacto + riser

Escena 2 (3-7s): Desarrollo rápido
  - Ángulo: Normal a picado
  - Cámara: Whip pan entre planos
  - Transición: Fundido cruzado rápido
  - SFX: Whoosh

Escena 3 (7-12s): Climax
  - Ángulo: Contrapicado extremo
  - Cámara: Zoom out explosivo + shake
  - Transición: Glitch
  - SFX: Stinger + rumble

Escena 4 (12-15s): Cierre con gancho
  - Ángulo: Normal
  - Cámara: Quiet con zoom in lento final
  - Transición: Fundido a negro
  - SFX: Rising a silencio
```

### Receta: "Cinemático lento" (para narrativa)
```
Duración por escena: 8-12 segundos
Cámara: Lenta, movimientos suaves (dolly, crane)
Transiciones: Fundidos cruzados largos (1-2s)
Iluminación: Dramática o low-key
Música: Orquestal o ambient
SFX: Sutiles (rumble, ambiente)
```
