/**
 * pi-alt-screen.js — Hace que pi use alternate screen buffer en Termux
 *
 * Cómo funciona:
 *   1. Se registra un loader hook via `register()` de Node.js
 *   2. Cuando pi-tui/tui.js está siendo cargado, modifica el source
 *      para agregar \x1b[?1049h (alternate screen) al start()
 *      y \x1b[?1049l al stop()
 *   3. Sin modificar node_modules, sin monkey-patch a streams
 *
 * Uso: PI_TERMUX_FIX=1 NODE_OPTIONS="--import /ruta/a/pi-alt-screen.js" pi
 */

// Este módulo se carga con --import (ESM)
// Registra el loader hook que transforma tui.js en carga

const ESC = '\x1b';

// Solo activar si PI_TERMUX_FIX=1
if (!process.env.PI_TERMUX_FIX) {
  // No hacemos nada
} else {
  // Forzar TERMUX_VERSION para que isTermuxSession() funcione
  process.env.TERMUX_VERSION = process.env.TERMUX_VERSION || 'alternate-screen';

  try {
    const { register } = await import('node:module');
    const { fileURLToPath } = await import('node:url');
    
    register('./pi-alt-screen-hook.js', import.meta.url);
    
    console.error('[pi-alt-screen] Loader hook registrado. Se usará alternate screen buffer.');
  } catch (e) {
    console.error('[pi-alt-screen] Error al registrar loader hook:', e.message);
  }
}
