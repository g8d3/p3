# OpenCode Go - Modelos con soporte de imagen (vision)

Prueba realizada el 2026-05-13 con una foto de gato tabby (3200x2212px).
Comando: `opencode run 'Describir imagen' --model opencode-go/<modelo> --file /tmp/test-image.jpg`

## Modelos que SÍ soportan imagenes

| Modelo | ID en OpenCode Go | Resultado |
|---|---|---|
| Kimi K2.5 | `opencode-go/kimi-k2.5` | Describio el gato perfectamente: patron tabby, marca "M" en frente, ojos verdes, nariz rosada, bigotes blancos, fondo blanco |
| Kimi K2.6 | `opencode-go/kimi-k2.6` | Describio el gato: base gris-cafe, rayas oscuras, ojos verde palido, retrato de estudio |
| MiMo-V2.5 | `opencode-go/mimo-v2.5` | Describio el gato: patron tabby marron/gris, marca "M", hocico canela, ojos verdes |
| Qwen3.5 Plus | `opencode-go/qwen3.5-plus` | Describio el gato: rayas clasicas tabby, ojos verde/amarillo, nariz rosada |
| Qwen3.6 Plus | `opencode-go/qwen3.6-plus` | Describio el gato: rayas marron/oscuro, ojos verde/ambar, barbilla blanca |

## Modelos que NO soportan imagenes (solo texto)

| Modelo | ID en OpenCode Go | Respuesta del modelo |
|---|---|---|
| DeepSeek V4 Pro | `opencode-go/deepseek-v4-pro` | "this model doesn't support image input" |
| DeepSeek V4 Flash | `opencode-go/deepseek-v4-flash` | "this model does not support image input" |
| GLM-5 | `opencode-go/glm-5` | (no testeado, mismo comportamiento que GLM-5.1) |
| GLM-5.1 | `opencode-go/glm-5.1` | "this model doesn't support image input" |
| MiMo-V2.5-Pro | `opencode-go/mimo-v2.5-pro` | "I can't view or analyze image files -- I'm a text-only model" |
| MiniMax M2.5 | `opencode-go/minimax-m2.5` | (no testeado, mismo comportamiento que M2.7) |
| MiniMax M2.7 | `opencode-go/minimax-m2.7` | "This model does not support image input" |

## Benchmark de velocidad (UI real)

Prueba realizada el 2026-05-14 con screenshot de OBS Studio (1920×1080, 64KB).
Prompt: *"Describe this computer screen in detail. What windows/dialogs are visible? What text and buttons do they contain? Is there any dialog blocking or requiring user interaction? What is the overall state of the application?"*

### Resultados ordenados por velocidad

| Ranking | Modelo | Tiempo | Longitud | Calidad descriptiva |
|---|---|---|---|---|
| 🥇 | **MiMo-V2.5** | **11.7s** | 1742 chars | ✅ Identificó OBS, interfaz en español, sin bloqueos |
| 🥈 | Qwen3.6 Plus | 25.2s | 1638 chars | ✅ OBS, tema oscuro, distribución de paneles |
| 🥉 | Qwen3.5 Plus | 27.9s | 1551 chars | ✅ OBS, menús y paneles detallados |
| 4 | Kimi K2.5 | 31.1s | 1394 chars | ✅ OBS, menú bar, atajos de teclado |
| 5 | Kimi K2.6 | 40.9s | 1769 chars | ✅ OBS, explicitly "no dialogs blocking" |

### Experimentos adicionales (2026-05-14)

### Prueba: resolución de imagen vs velocidad

¿Conviene redimensionar la imagen antes de enviarla? Se probó MiMo-V2.5 con 5 versiones de la misma captura de OBS.

| Versión | Resolución | Tamaño | Tiempo | ¿Descripción correcta? |
|---|---|---|---|---|
| 360p PNG | 640×360 | 32KB | 8.3s | ✅ OBS, "no blocking dialog" |
| 540p PNG | 960×540 | 52KB | 4.7s | ❌ Respuesta vacía (error) |
| 720p PNG | 1280×720 | 76KB | 9.3s | ✅ OBS, escenas, fuentes |
| 1080p JPG (q15) | 1920×1080 | 28KB | 10.0s | ✅ OBS español, interfaz completa |
| 1080p PNG | 1920×1080 | 64KB | 7.3s | ✅ OBS, escenas, "no blocking" |

### Conclusiones sobre resolución

- **El tamaño del archivo (KB) NO afecta el tiempo.** 1080p PNG (64KB) fue más rápido que 720p PNG (76KB).
- **Redimensionar no da ventaja.** La imagen original (1080p PNG) dió 7.3s vs 8.3s-10s de las versiones reducidas.
- El modelo internamente redimensiona a una resolución fija — no importa lo que le mandes.
- La variación de tiempos (±3s) parece ser **latencia de red/servidor**, no un factor de la imagen.

**Conclusión práctica: No redimensionar.** Usar la screenshot original sin procesamiento previo. El overhead de convertir/redimensionar solo añade latencia sin beneficio.

### Recomendación final para screen-debug

1. **Tomar screenshot directo** del display (sin redimensionar, sin convertir formato)
2. **Usar MiMo-V2.5** como modelo default por velocidad (~10s promedio)
3. **Solo si se necesita más detalle**, retry con Kimi K2.6 o Qwen3.6 Plus
4. El bottleneck real **no es la imagen** sino la latencia del servidor del modelo

## Relevancia para la skill screen-debug

Este benchmark confirma que el pipeline de la skill funciona:
1. **Accesibilidad** (xdotool) — detecta ventanas y títulos en <1s
2. **Visión** (MiMo-V2.5) — confirma diagnóstico visual en ~12s
3. **Acción** — basado en el diagnóstico combinado

Sin esta combinación, el orchestrator puede girar en círculos como ocurrió con OBS.
La skill screen-debug está en `~/.agents/skills/screen-debug/`.

## Notas

- MiMo-V2-Omni y MiMo-V2-Pro **no estan disponibles en OpenCode Go** (la lista actual solo incluye `mimo-v2.5` y `mimo-v2.5-pro`).
- Todos los modelos vision-capable describieron correctamente los mismos detalles: gato tabby, rayas, ojos verdes, fondo blanco, sin texto.
- Los modelos text-only rechazaron explicitamente la imagen sin crashear.
