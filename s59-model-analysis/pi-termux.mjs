/**
 * pi-termux.mjs — Preload para pi en Termux
 *
 * Carga el hook que rompe el render loop en pi's TUI.
 *
 * Uso: PI_TERMUX_FIX=1 NODE_OPTIONS="--import /ruta/a/pi-termux.mjs" pi
 */

if (!process.env.PI_TERMUX_FIX) {
  // No activado
} else {
  process.env.TERMUX_VERSION = process.env.TERMUX_VERSION || 'termux-fix';
  
  try {
    const { register } = await import('node:module');
    register('./pi-termux-hook.mjs', import.meta.url);
    console.error('[pi-termux] ✓ Hook registrado. Render loop roto.');
  } catch (e) {
    console.error('[pi-termux] Error:', e.message);
  }
}
