/**
 * pi-termux-hook.mjs — Loader hook que repara el TUI de pi para Termux
 *
 * Parches:
 *   Patch 1: Romper render loop (firstChanged < prevViewportTop)
 *     - Si el cambio es en input (últimas 5 líneas): soft render desde home
 *     - Si no: skip (solo actualizar estado en memoria)
 *     - Así el input se ve al escribir y el loop no salta la pantalla
 *
 * Nota: El input box fijo (como OpenCode) requiere cambiar la arquitectura
 * de pi-tui para renderizar el input como overlay. Reportado en issue #4506.
 */

const TUI_PATH = 'dist/tui.js';

export function load(url, context, nextLoad) {
  return nextLoad(url, context).then(result => {
    if (!url.includes(TUI_PATH) || !url.includes('@earendil-works')) {
      return result;
    }

    let source = typeof result.source === 'string' 
      ? result.source 
      : Buffer.from(result.source).toString('utf8');

    const p1search = 
      'if (firstChanged < prevViewportTop) {\n' +
      '            logRedraw(`firstChanged < viewportTop (${firstChanged} < ${prevViewportTop})`);\n' +
      '            fullRender(true);\n' +
      '            return;\n' +
      '        }';
    
    const p1replace = 
      'if (firstChanged < prevViewportTop) {\n' +
      '            if (firstChanged >= newLines.length - 5) {\n' +
      '                logRedraw(`firstChanged < viewportTop INPUT (${firstChanged} < ${prevViewportTop}) SOFT_RENDER`);\n' +
      '                let buf = "\\x1b[?2026h";\n' +
      '                buf += "\\x1b[H";\n' +
      '                for (let i = 0; i < newLines.length; i++) {\n' +
      '                    if (i > 0) buf += "\\r\\n";\n' +
      '                    buf += newLines[i];\n' +
      '                }\n' +
      '                buf += "\\x1b[?2026l";\n' +
      '                this.terminal.write(buf);\n' +
      '                this.cursorRow = Math.max(0, newLines.length - 1);\n' +
      '                this.hardwareCursorRow = this.cursorRow;\n' +
      '                this.maxLinesRendered = Math.max(this.maxLinesRendered, newLines.length);\n' +
      '            } else {\n' +
      '                logRedraw(`firstChanged < viewportTop (${firstChanged} < ${prevViewportTop}) SKIPPED`);\n' +
      '                this.previousLines = newLines;\n' +
      '                this.previousKittyImageIds = this.collectKittyImageIds(newLines);\n' +
      '                this.previousWidth = width;\n' +
      '                this.previousHeight = height;\n' +
      '                this.previousViewportTop = prevViewportTop;\n' +
      '            }\n' +
      '            this.positionHardwareCursor(cursorPos, newLines.length);\n' +
      '            return;\n' +
      '        }';

    if (!source.includes(p1search)) {
      console.error('[pi-termux] ⚠ Patrón no encontrado');
      const idx = source.indexOf('firstChanged < prevViewportTop');
      if (idx >= 0) console.error('Contexto:', source.substring(idx, idx + 250));
      return result;
    }

    source = source.replace(p1search, p1replace);
    console.error('[pi-termux] ✓ Render loop roto, input accesible al escribir');

    return { ...result, source };
  });
}
