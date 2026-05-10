# 🌳 Árbol de Tareas — Formato para reportes JSON

Cada agente debe incluir en su reporte JSON un campo `arbol_tareas` 
que describa TODO lo que hizo como un árbol estructurado.

## Estructura

```json
{
  "agente": "editor",
  "resumen": "5 variaciones de edición generadas",
  "arbol_tareas": [
    {
      "nombre": "Leer especificación",
      "descripcion": "Leer templates/escenas.yaml para entender las 6 escenas",
      "tipo": "lectura",
      "duracion_seg": 5,
      "estado": "ok",
      "hijos": []
    },
    {
      "nombre": "Pipeline de edición",
      "descripcion": "Aplicar movimientos de cámara, color grading, transiciones",
      "tipo": "procesamiento",
      "duracion_seg": 300,
      "estado": "ok",
      "hijos": [
        {
          "nombre": "Zoom in escena 1",
          "descripcion": "Aplicar Ken Burns zoom in a escena del Big Bang",
          "tipo": "efecto",
          "duracion_seg": 45,
          "estado": "ok",
          "hijos": []
        },
        {
          "nombre": "Color grading cinematic",
          "descripcion": "Aplicar LUT teal/orange + viñeta + grano",
          "tipo": "color",
          "duracion_seg": 60,
          "estado": "ok",
          "hijos": []
        }
      ]
    },
    {
      "nombre": "Generar variaciones",
      "descripcion": "5 estilos diferentes: documental, cinematic, vaporwave, tiktok, acción",
      "tipo": "render",
      "duracion_seg": 600,
      "estado": "ok",
      "hijos": [
        {"nombre": "video_e1.mp4 - Documental", "descripcion": "Colores naturales, transiciones suaves", "tipo": "variacion", "duracion_seg": 120, "estado": "ok", "hijos": []},
        {"nombre": "video_e2.mp4 - Cinematic", "descripcion": "Teal/orange, letterbox, grano", "tipo": "variacion", "duracion_seg": 120, "estado": "ok", "hijos": []}
      ]
    }
  ]
}
```

## Tipos de tarea

| tipo | Descripción | Icono |
|------|-------------|-------|
| `lectura` | Leer archivos, especificaciones | 📖 |
| `escritura` | Escribir archivos, reportes | ✍️ |
| `procesamiento` | Procesamiento general | ⚙️ |
| `render` | Renderizar video/audio | 🎬 |
| `efecto` | Aplicar efecto visual o de audio | ✨ |
| `color` | Color grading | 🎨 |
| `variacion` | Generar variación | 🔀 |
| `evaluacion` | Evaluar calidad | ✅ |
| `error` | Tarea con errores | ❌ |
| `espera` | Esperando a otro agente | ⏳ |

## Cómo incluirlo en el reporte

Al final de tu tarea, cuando escribes `reportes/AGENTE.json`, 
incluye el campo `arbol_tareas` con toda la estructura.
Sé descriptivo pero conciso en `descripcion` (máximo 120 caracteres).

Esto alimenta el dashboard web que muestra el árbol expandible
y las tablas con filtros.
