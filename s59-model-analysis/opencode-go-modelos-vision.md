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

## Notas

- MiMo-V2-Omni y MiMo-V2-Pro **no estan disponibles en OpenCode Go** (la lista actual solo incluye `mimo-v2.5` y `mimo-v2.5-pro`).
- Todos los modelos vision-capable describieron correctamente los mismos detalles: gato tabby, rayas, ojos verdes, fondo blanco, sin texto.
- Los modelos text-only rechazaron explicitamente la imagen sin crashear.
