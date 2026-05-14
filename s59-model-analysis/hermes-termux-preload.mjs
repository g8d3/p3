/**
 * hermes-termux-preload.mjs — Preload script que repara el TUI de Hermes para Termux
 *
 * Este script se carga con --import (Node.js 18+) y se ejecuta antes que el resto
 * de la aplicación. Utiliza la API `Module.register` (o `process.dlopen` en versiones
 * anteriores) para interceptar la carga del bundle de @hermes/ink y parchearlo.
 *
 * Uso (Node.js 18+):
 *   NODE_OPTIONS="--import ./hermes-termux-preload.mjs" tsx src/entry.tsx
 *
 * Uso (Node.js 16):
 *   NODE_OPTIONS="--experimental-loader ./hermes-termux-hook.mjs" tsx src/entry.tsx
 *
 * Nota: Este preload usa un enfoque diferente al loader hook. En lugar de interceptar
 * la carga del módulo, parchea el LogUpdate.prototype.render después de que el módulo
 * se haya cargado. Esto es más simple pero requiere que podamos acceder al prototipo.
 */

// Este es un placeholder - el enfoque de preload requiere que LogUpdate sea accesible
// desde fuera del bundle. Como @hermes/ink exporta la función render() desde root.ts,
// pero LogUpdate es interno, el loader hook es más fiable.

console.error('[hermes-termux] Usa el loader hook en su lugar:');
console.error('[hermes-termux]   NODE_OPTIONS="--experimental-loader ./hermes-termux-hook.mjs" tsx src/entry.tsx');
console.error('[hermes-termux] O exporta HERMES_NODE_LOADER antes de ejecutar hermes');
