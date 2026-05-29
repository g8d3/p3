# Análisis — 5 Ideas Principales

**Fuente:** `docs/vision_completa.md`

---

### 1. Consumo = Producción

El usuario genera contenido para otros simplemente consumiendo (scrolleando, viendo). La app reemplaza a TikTok/YouTube/X, pero el usuario no es el producto ni está siendo vendido.

### 2. Feed infinito tipo TikTok

No hay UI de pipeline (Guión / Estilo / Renderizar / Historial). Una sola pantalla: reproductor de video con feed infinito y controles superpuestos (overlay OSD). Cada video es nuevo y autogenerado.

### 3. Fuentes de datos conectadas

Las cuentas reales del usuario se conectan a GitHub, Hugging Face, Pixabay, X, YouTube y TikTok. No trends genéricos: la app ve lo que el algoritmo ya le sugiere al usuario en cada red social. Dashboard de estado en tiempo real.

### 4. Streaming y cambios en vivo

El video se reproduce vía HLS, no se renderiza de forma bloqueante. Cola de pre-renderizado en background. Los cambios del usuario (fuente, voz, música) se reflejan en vivo con previsualización rápida de baja calidad y versión completa después.

### 5. Cero fricción / Autonomía máxima

No hay botones para obtener datos, escribir guiones ni renderizar. Todo ocurre automáticamente: fetch de tendencias, escritura de guión por LLM, generación de video. El usuario solo decide qué ver y ajusta parámetros opcionales.

---

*Resumen generado el 28 de mayo de 2026.*
