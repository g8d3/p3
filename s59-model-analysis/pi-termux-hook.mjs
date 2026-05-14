const TUI_PATH = 'dist/tui.js';

export function load(url, context, nextLoad) {
  return nextLoad(url, context).then(result => {
    if (!url.includes(TUI_PATH) || !url.includes('@earendil-works')) {
      return result;
    }

    let source = typeof result.source === 'string' 
      ? result.source 
      : Buffer.from(result.source).toString('utf8');

    // Patch 1: firstChanged < prevViewportTop → ya no fullRender(true)
    // Si es input (últimas 5 líneas): clear screen + home + escribir todo
    // Si no: solo actualizar estado en memoria (skip)
    const OLD = 'if (firstChanged < prevViewportTop) {\n' +
      '            logRedraw(`firstChanged < viewportTop (${firstChanged} < ${prevViewportTop})`);\n' +
      '            fullRender(true);\n' +
      '            return;\n' +
      '        }';

    const NEW = 'if (firstChanged < prevViewportTop) {\n' +
      '            if (firstChanged >= newLines.length - 5) {\n' +
      '                logRedraw(`firstChanged < viewportTop INPUT (${firstChanged} < ${prevViewportTop}) SOFT_RENDER`);\n' +
      '                let buf = "\\x1b[?2026h";\n' +
      '                buf += "\\x1b[2J\\x1b[H";\n' +
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

    if (!source.includes(OLD)) {
      console.error('[pi-termux] ⚠ OLD pattern not found');
      return result;
    }

    source = source.replace(OLD, NEW);
    console.error('[pi-termux] ✓ Render loop roto');
    return { ...result, source };
  });
}
