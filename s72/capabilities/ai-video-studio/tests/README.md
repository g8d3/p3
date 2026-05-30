READ FIRST — Cómo usar a Crush para testing

## Flujo de trabajo

1. Trabajas en **window 0** (tu Crush con el código)
2. Cuando termines una iteración, **cambia a window 3** (mi ventana) o simplemente **escribe "test" en window 0**
3. Yo detecto cambios, ejecuto pruebas y dejo reportes en `test-reports/`

## Lo que puedo probar

| Tipo | Cobertura |
|------|-----------|
| ✅ APIs REST | Todos los endpoints (feed, style, sources, config, assets) |
| ✅ Árbol de accesibilidad | Botones, sliders, checkboxes, selects, textos |
| ✅ Consola JS | Errores, warnings, logs |
| ✅ Navegación | Carga de paquetes, preload, cola |
| ✅ Estilo | Voice, font, music volume — aplicar y verificar |
| ❌ Swipe táctil | No puedo simular touch events vía CDP (solo clicks) |
| ❌ Visual | Sin capacidad de visión (layout, colores, animaciones) |

## Reportes generados

| Archivo | Contenido |
|---------|-----------|
| `test-reports/000-inicial.md` | Smoke test inicial |
| `test-reports/001-verificacion-features.md` | Verificación 6/6 To-Do |
| `test-reports/harness.py` | Suite de tests automatizada |
| `test-reports/auto-*.txt` | Tests automáticos al detectar cambios |

## Cómo pedir una prueba específica

- "ejecuta el test suite completo"
- "prueba que el feed tenga 5 videos en cola"
- "verifica que el swipe funcione" (reviso el código)
- "testea que los assets se sirvan correctamente"
- "abre el composer y dime qué ves"
