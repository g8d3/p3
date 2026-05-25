# VoiceButtons - Tareas Completas y Pendientes

## 1. Funcionalidad Base (App Android)

### Completado
- [x] Overlay flotante con botón toggle (▲/▼) para expandir/contraer
- [x] Botones dinámicos configurables (texto, tecla, voz, enter)
- [x] Servicio de accesibilidad para inyectar texto en cualquier app
- [x] Guardar posición del overlay (SharedPreferences)
- [x] Guardar estado activo del panel (service_active)
- [x] Arrastre del overlay con offset correcto (no centrar)
- [x] Botones circulares con iconos según tipo
- [x] Diálogo de agregar/editar botón con selector de iconos
- [x] Autocompletado de teclas (ENTER, TAB, BACK, etc.)
- [x] Múltiples teclas separadas por espacio (ENTER TAB HOME)
- [x] Botón "Sugerir mejora" en la app
- [x] Botón "Configurar servidor" en la app
- [x] Botón "Ver logs" con buffer de 100 entradas
- [x] Permiso de micrófono solicitado al abrir la app
- [x] Panel se reinicia automáticamente al abrir la app si estaba activo
- [x] Presets de iconos predefinidos (🎤⏎⌫⬅️🏠↹⬆️⬇️▶️⏸📝🔑🔄🎯❌)

### Pendiente / Roto
- [ ] **RECONOCIMIENTO DE VOZ**: `onResults` se ejecuta pero text es null. Usa SpeechRecognizer directo (sin diálogo). Funcionó antes, se rompió al cambiar EXTRA_LANGUAGE. Sospecha: modelo de idioma no instalado. Intentar con `ACTION_RECOGNIZE_SPEECH` por actividad (el usuario no quiere el diálogo de Google).
- [ ] **TELEMETRÍA AL SERVIDOR**: `addLog()` envía POST a `http://100.102.52.59:9099/report` pero nunca llegan. Solo los reportes manuales (CrashReporter) funcionan. Diagnóstico pendiente.
- [ ] **ANIMACIÓN MICRÓFONO**: El botón 🎤 debe quedar quieto y un círculo interior debe pulsar (cambio de color/opacidad). Actualmente pulsa el fondo del botón. El usuario quiere una bola DENTRO del botón.
- [ ] **IDIOMA CONFIGURABLE**: Agregar selector de idioma para voz (es, en, etc.) en la configuración del servidor o un diálogo aparte.
- [ ] **VOZ CONTINUA**: Que el micrófono siga activo aunque haya silencios largos (el usuario piensa entre oraciones). Usar `EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS`.
- [ ] **TOAST DE TEXTO RECONOCIDO**: El usuario no quiere el popup Toast cuando se reconoce texto. Ya se quitó pero verificar.

## 2. Servidor Web (serve_apk.py)

### Completado
- [x] Servir APK con listado newest-first
- [x] Endpoint POST `/report` para recibir reportes
- [x] Página de reportes con tabla
- [x] Filtros por categoría (crash, feature, evento, estado, resultado)
- [x] Checkboxes para filtrar (funcionan)
- [x] Botones rápidos "Evento+Estado+Resultado" y "Mostrar todos"
- [x] Botón "Borrar todos" con confirmación
- [x] Panel de prueba con campo de texto (Enter simula telemetría)
- [x] Auto-refresh cada 2 segundos via JS polling
- [x] Endpoint `/api/reports` para JSON con filas HTML

### Pendiente
- [ ] Los botones rápidos de filtro deben funcionar sin recargar la página

## 3. Instalación y ADB

### Completado
- [x] ADB wireless funcionando con Tailscale
- [x] `adb install -r` para instalación rápida
- [x] `adb shell am start` para lanzar la app
- [x] Emparejamiento inicial con código de 6 dígitos

### Pendiente
- [ ] Después de instalar, lanzar la app brevemente y devolver al usuario a su app anterior (Termux). No se puede hacer `input keyevent HOME` sin INJECT_EVENTS.

## 4. UX y Diseño

### Completado
- [x] Botones circulares en lugar de rectángulos
- [x] Iconos según tipo de acción (🎤⏎📝🔑)
- [x] Toggle circular
- [x] Overlay sin fondo rectangular
- [x] Arrastre desde cualquier punto (incluyendo el triángulo)
- [x] Posición guardada al arrastrar
- [x] Diálogo simplificado: solo icono + tipo + acción con autocomplete
- [x] Eliminar botones duplicados Guardar/Cancelar del diálogo
- [x] Botón "Ver logs" con copia al portapapeles

### Pendiente
- [ ] Animación del micrófono: bola azul pulsando DENTRO del botón 🎤 (no escalar el botón completo)
- [ ] Feedback de voz: sin Toast, sin diálogo, solo la bola pulsando
- [ ] Botón de "Detener" escucha (presionar el mismo botón de voz mientras está activo)

## 5. Nombres y Conceptos (Español vs Técnico)

| Término usuario | Término Android |
|----------------|-----------------|
| Popup | Toast |
| Panel flotante | Overlay / System overlay window |
| Servicio de accesibilidad | AccessibilityService |
| Botón triángulo | Toggle button (overlay expand/collapse) |
| Bola pulsante | ValueAnimator + GradientDrawable (círculo) |
| Logs / Consola | logcat / Buffer circular en memoria |
| Superposición | SYSTEM_ALERT_WINDOW permission |
| Depuración inalámbrica | ADB over Wi-Fi |

## 6. Bugs Conocidos

1. **Voice onResults null**: SpeechRecognizer callback recibe Bundle sin resultados. Sospecha: caché del recognizer, idioma no soportado, o falta de datos de idioma descargados.
2. **Telemetría no llega**: POST desde `addLog()` (companion object) al servidor falla silenciosamente. Misma URL que CrashReporter (que sí funciona).
3. **Botón "Iniciar Panel" no abre permisos de overlay**: El intent `ACTION_MANAGE_OVERLAY_PERMISSION` falla en algunos dispositivos. Tiene fallback a `ACTION_APPLICATION_DETAILS_SETTINGS`.
4. **El panel no se puede mover cuando está minimizado**: Resuelto con el cambio a offset de arrastre.

## 7. Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| `FloatingButtonService.kt` | Overlay, drag, voz, todo lo principal (~370 lines) |
| `MainActivity.kt` | UI de configuración, botones, logs |
| `ActionAccessibilityService.kt` | Inyectar texto en otras apps |
| `Telemetry.kt` | Enviar eventos al servidor |
| `CrashReporter.kt` | Reportes de crash + feature requests |
| `ButtonStorage.kt` | Guardar/cargar botones en SharedPreferences |
| `ButtonConfig.kt` | Data class ButtonConfig |
| `ButtonAdapter.kt` | RecyclerView para lista de botones |
| `overlay_buttons.xml` | Layout del overlay flotante |
| `dialog_button_config.xml` | Diálogo de agregar botón |
| `activity_main.xml` | Pantalla principal |
| `serve_apk.py` | Servidor HTTP (APK + reportes) |
| `AndroidManifest.xml` | Permisos, servicios, activity |
| `accessibility_service_config.xml` | Config del AccessibilityService |
| `HANDOFF.md` | Este archivo |

## 8. Próximos Pasos (Prioridad)

1. **ARREGLO #1**: Hacer que `SpeechRecognizer` devuelva texto. Diagnóstico: revisar `matches=` en logs, probar con `EXTRA_LANGUAGE="es"` explícito, asegurar que el recognizer no se destruye antes de onResults.
2. **ARREGLO #2**: Logs al servidor. Cambiar `addLog` para usar contexto estático o enviar desde el service en lugar del companion.
3. **ARREGLO #3**: Animación del micrófono: mantener el botón quieto, agregar una segunda capa (View interna) para la bola pulsante.
4. **FEATURE**: Selector de idioma para voz en configuración.
5. **FEATURE**: Silencios largos para voz continua (EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS).

## 9. Comandos Rápidos

```bash
# Compilar, instalar y lanzar
cd /home/vuos/code/p3/s71/VoiceButtonApp
ANDROID_SDK_ROOT=/home/vuos/android-sdk ./gradlew assembleDebug && \
ANDROID_SDK_ROOT=/home/vuos/android-sdk /home/vuos/android-sdk/platform-tools/adb -s 100.125.188.101:39267 install -r app/build/outputs/apk/debug/app-debug.apk && \
ANDROID_SDK_ROOT=/home/vuos/android-sdk /home/vuos/android-sdk/platform-tools/adb -s 100.125.188.101:39267 shell am start -n com.voicebutton/.MainActivity

# Solo instalar y lanzar (sin compilar)
adb -s 100.125.188.101:39267 install -r app/build/outputs/apk/debug/app-debug.apk
adb -s 100.125.188.101:39267 shell am start -n com.voicebutton/.MainActivity

# ADB reconectar (cuando el puerto cambia)
adb connect 100.125.188.101:NUEVO_PUERTO

# Servidor
cd /home/vuos/code/p3/s71/VoiceButtonApp && python3 serve_apk.py &

# Servidor con logs
cd /home/vuos/code/p3/s71/VoiceButtonApp && python3 serve_apk.py 2>&1 | tee server.log
```
