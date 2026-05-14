/**
 * hermes-termux-hook.mjs — Loader hook que repara el TUI de Hermes para Termux
 *
 * Parchea fullResetSequence_CAUSES_FLICKER para que cuando sea 'offscreen'
 * NO limpie la pantalla (\x1b[2J\x1b[3J), solo haga home + repintado.
 * Esto evita el salto de pantalla en Termux+SSH+tmux al hacer tap.
 *
 * Uso:
 *   export NODE_OPTIONS="--experimental-loader=/PATH/TO/hermes-termux-hook.mjs"
 *   hermes --tui
 *
 * O en una sola línea:
 *   NODE_OPTIONS="--experimental-loader=/PATH/TO/hermes-termux-hook.mjs" hermes --tui
 */

const TARGET = 'entry-exports.js';

export function load(url, context, nextLoad) {
  return nextLoad(url, context).then(result => {
    if (!url.includes(TARGET)) {
      return result;
    }

    let source = typeof result.source === 'string' 
      ? result.source 
      : Buffer.from(result.source).toString('utf8');

    // Buscar el patrón de fullResetSequence_CAUSES_FLICKER
    const idx = source.indexOf('function fullResetSequence_CAUSES_FLICKER');
    if (idx === -1) {
      console.error('[hermes-termux] ⚠ fullResetSequence_CAUSES_FLICKER no encontrado');
      return result;
    }

    // Encontrar el bloque: function ... { ... return [{ type: "clearTerminal", ... }] }
    const funcStart = idx;
    const returnPos = source.indexOf('return [{ type: "clearTerminal"', funcStart);
    if (returnPos === -1) {
      console.error('[hermes-termux] ⚠ clearTerminal return no encontrado');
      return result;
    }

    // Encontrar el cierre "];" que termina el return
    const stmtEnd = source.indexOf('];', returnPos);
    if (stmtEnd === -1) {
      console.error('[hermes-termux] ⚠ Fin de return no encontrado');
      return result;
    }

    const before = source.substring(0, returnPos);
    const after = source.substring(stmtEnd + 2);

    const replacement = 
      'if (reason === "offscreen") {\n' +
      '    return [\n' +
      '      { type: "stdout", content: CURSOR_HOME },\n' +
      '      ...screen.diff,\n' +
      '      { type: "stdout", content: "\\x1b[J" }\n' +
      '    ];\n' +
      '  }\n' +
      '  return [{ type: "clearTerminal", reason, debug }, ...screen.diff]';

    source = before + replacement + after;
    console.error('[hermes-termux] ✓ fullResetSequence_CAUSES_FLICKER parcheado');

    return { ...result, source };
  });
}
