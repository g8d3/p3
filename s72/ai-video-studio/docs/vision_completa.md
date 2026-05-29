# AI Video Studio — Visión Completa

Todas las ideas, observaciones y requisitos extraídos de la conversación.

---

## Filosofía (norte del proyecto)

1. **Consumo = Producción.** El usuario nunca debería sentir que está "creando contenido". Está consumiendo (scrolleando, viendo, eligiendo) y ese mismo acto genera contenido para otros. Es el reemplazo de TikTok/YouTube/X — pero el usuario no es el producto.

2. **Autonomía máxima.** La app hace todo sola: fetch de tendencias, escritura de guión, generación de video, sugerencia de cambios. El usuario solo decide qué ver y ajusta parámetros si quiere.

3. **Cero fricción.** No hay botones para obtener datos, no hay cajas de texto para escribir guiones, no hay botones de "renderizar". Todo ocurre automáticamente.

4. **El usuario nunca es el producto.** A diferencia de las redes sociales tradicionales, aquí el usuario no está siendo vendido. Su interacción genera valor para otros usuarios del sistema.

---

## UI / Experiencia de usuario

5. **Feed de video infinito** (como TikTok). El usuario scrollea y cada video es nuevo, autogenerado.

6. **Reproductor de video con controles superpuestos.** No una interfaz de pipeline. El usuario ve un video y los controles de estilo (fuente, voz, volumen, música, fondo) aparecen como overlay, tipo OSD de reproductor.

7. **Sin pestañas.** La organización actual (Guión / Estilo / Renderizar / Historial) es de pipeline, no de app interactiva. Debe desaparecer o fusionarse en una sola pantalla: el reproductor.

8. **Sin botón "Obtener tendencias".** Las fuentes se fetchan automáticamente al cargar y periódicamente.

9. **Sin caja de texto de guión.** Un LLM escribe los guiones combinando datos de tendencias + cuentas conectadas del usuario.

10. **Sin botón "Renderizar".** El video se pre-renderiza en background o se genera progresivamente (streaming). El usuario solo ve el resultado.

11. **El Historial debe ser de acciones** (del usuario + automáticas del sistema), no de renders.

12. **Slider de "qué tan automático vs manual".** Un extremo: todo automático. El otro: control total. El usuario elige dónde situarse.

---

## Fuentes de datos

13. **GitHub** — repositorios trending de IA/ML.
14. **Hugging Face** — modelos y datasets trending + inferencia (no solo leer datos, sino correr modelos para generar multimedia).
15. **Pixabay** — videos y música libres (API key gratuita incluida).
16. **X.com (Twitter)** — requiere API key paga ($100/mo Basic, $5000/mo Pro).
17. **YouTube** — requiere YouTube Data API v3 key (gratuita).
18. **TikTok** — requiere TikTok Business API (aprobación de 2-4 semanas) o scraper.

19. **Las cuentas reales del usuario deben estar conectadas.** No es suficiente con trends genéricos. La app debe ver lo que el algoritmo ya le sugiere al usuario en cada red social.

20. **Múltiples cuentas por red social.** El usuario puede conectar varias cuentas de X, varias de TikTok, etc.

21. **Conexión a jardines cerrados (X, TikTok).** Es lo más difícil. Evaluar APIs oficiales (pagas) vs scrapers (frágiles, pero a veces la única opción).

22. **Dashboard de estado de conexiones.** En tiempo real e histórico. El usuario debe poder ver el estado detallado de cada fuente: última vez que se fetchó, cuántos items, errores, rate limit restante.

---

## Generación de video

23. **Streaming, no renderizado bloqueante.** ffmpeg tarda 30-60s. Para que sea en tiempo real:
    - Pre-renderizar cola de videos en background (pool de próximos N videos)
    - Usar HLS (HTTP Live Streaming) para reproducción progresiva
    - Calidad menor para velocidad (ej. 720p en vez de 1080p, bitrate más bajo)

24. **Cambios en vivo.** El usuario cambia el tamaño de fuente, la voz TTS, el volumen de música, y el video debería actualizarse. Si no es posible en tiempo real:
    - Versión preliminar de baja calidad rápida
    - Luego versión completa en background

25. **Variedad de fondos.** No usar el mismo video de fondo ni la misma canción. Aleatoriedad real.

26. **Música synthwave 80s.** O música que siga tendencias de TikTok. El usuario debe poder cambiarla.

27. **Subtítulos tamaño 96.** Confirmado como el mejor por el usuario. Tamaños 144 y 192 como opciones.

28. **Números como dígitos.** "16%" no "dieciséis por ciento". "$35B" no "treinta y cinco mil millones".

29. **Subtítulos en una sola línea, parte inferior o central.** Ocupando buena parte de la pantalla para fácil lectura.

30. **Karaoke word highlighting.** La palabra actual se resalta (ASS con \K). Las palabras anteriores y siguientes en otro color.

31. **Algoritmo de subtítulos adaptivo por tiempos.** edge-tts elimina puntuación. No se puede dividir por palabras clave. Se divide por pausas entre palabras (~875ms = oración, ~12ms = dentro de frase).

32. **Evitar huérfanos en subtítulos.** No dejar 1-2 palabras colgando en un bloque.

33. **Una sola pantalla.** Sin dual-screen / PiP. Un solo video de fondo de alta calidad.

34. **Audio sincronizado exactamente.** El video debe terminar cuando termina la narración, no antes ni después.

---

## Infraestructura técnica

35. **Visibilidad absoluta.** Toda herramienta que permita ver errores debe estar activa: curl, agent-browser, CDP Chrome, logs estructurados, stderr.

36. **Logs de errores en archivos.** Cada error de herramienta o de código debe quedar registrado para referencia futura.

37. **Configuración de proveedores.** El modelo actual es deepseek-v4-flash vía opencode-go (API key en variable de entorno OPENCODE_GO_API_KEY). agentic_fetch usa Gemini (free tier con rate limits). Para mejorar: API key paga de Gemini, o cambiar proveedor.

38. **Curl está restringido por el sistema.** Alternativas: Python (urllib, requests), CDP, agent-browser.

---

## Próximas iteraciones

39. **App en tiempo real v1.** Ya existe backend (FastAPI) + frontend (Streamlit) + 6 conectores + render queue. El bug principal encontrado y corregido: falta de `/api` en rutas del frontend.

40. **Migrar a feed.** El siguiente paso es reemplazar la UI de pipeline por un reproductor con feed infinito.

41. **Perfiles de usuario.** Que el usuario pueda tener múltiples "identidades" o configuraciones guardadas.

42. **Colaboración.** Que un usuario pueda ver lo que otros están generando (feed social interno).

43. **Marketplace de plantillas.** Usuarios comparten sus configuraciones de estilo (fuente, música, layout) como "presets".

---

*Documento generado el 28 de mayo de 2026. Fuente: conversación completa con el usuario.*
