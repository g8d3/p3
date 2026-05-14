/**
 * pi-alt-screen.mjs — Preload para pi en Termux (buffer normal con filtros)
 *
 * Cómo usar: PI_TERMUX_FIX=1 NODE_OPTIONS="--import /ruta/a/pi-alt-screen.mjs" pi
 * 
 * En lugar de alternate screen buffer (que elimina el scrollback),
 * filtramos las secuencias problemáticas en el buffer normal:
 *   - \x1b[3J — clear scrollback (salto post-respuesta)
 *   - \x1b[2J — clear screen (posible salto en transiciones)
 *
 * Así preservamos el scrollback de la terminal.
 */

if (!process.env.PI_TERMUX_FIX) {
  // No activado explícitamente
} else {
  process.env.TERMUX_VERSION = process.env.TERMUX_VERSION || 'termux-fix';

  try {
    const { register } = await import('node:module');
    register('./pi-alt-screen-hook.mjs', import.meta.url);
    console.error('[pi-termux] ✓ Hook registrado. Buffer normal sin clears problemáticos.');
  } catch (e) {
    console.error('[pi-termux] Error:', e.message);
  }
}
