# Bug Report: Screen jumping in Termux via SSH + tmux when using pi (pi-tui)

## Summary

When using `pi` from Termux (Android terminal emulator) via SSH into a remote machine running tmux, tapping on the screen causes the display to jump/scroll erratically. This happens specifically during section transitions (thinking → command → response) and when the input box is visible.

**OpenCode does NOT have this issue**, which helped identify the root cause.

## Environment

- **Device**: Android phone running Termux
- **Connection**: `ssh` from Termux to a Linux machine
- **Terminal multiplexer**: tmux (`TERM=tmux-256color`)
- **pi version**: 0.74.0
- **pi-tui**: as bundled with pi
- **Node.js**: 22.22.2

## Root Causes Found

### Issue 1: `fullRender(true)` sends `\x1b[3J` (erase scrollback)

**File**: `packages/pi-tui/src/tui.ts` → `fullRender()` method

When `fullRender(true)` is called, it sends the sequence:
```
\x1b[2J\x1b[H\x1b[3J
```

The `\x1b[3J` (erase scrollback / CSI 3 J) clears the terminal's scrollback buffer. In Termux, this causes the viewport position to reset, resulting in a visible jump when the user taps the screen after a response is complete.

**Fix**: Remove `\x1b[3J` from `fullRender()`, or make it conditional (e.g., only when `isTermuxSession()` returns true, or never since most terminals don't need it).

**Confirming the fix**: Simply filtering `\x1b[3J` from the terminal output (via monkey-patch) completely stopped the post-response jumping.

### Issue 2: Infinite full-render loop triggered by `firstChanged < prevViewportTop`

**File**: `packages/pi-tui/src/tui.ts` → `doRender()` method

The TUI has a condition:
```typescript
if (firstChanged < prevViewportTop) {
    logRedraw(`firstChanged < viewportTop (${firstChanged} < ${prevViewportTop})`);
    fullRender(true);
    return;
}
```

This triggers when content changes above the visible viewport. In pi's case, some component (likely a status indicator, cursor marker, or timer) constantly produces small changes above the viewport. This causes:

1. A full render with `\x1b[2J\x1b[H\x1b[3J` (clear screen + home + clear scrollback)
2. The full render takes time, during which the indicator changes again
3. Next render cycle detects another change → another full render
4. **Infinite loop of full re-renders** (observed in diagnostic logs: 30+ identical full renders per second)

Each render sends the same ~300KB of data (the entire conversation history), causing constant screen clearing and re-drawing. In Termux with the keyboard visible, this creates the perception of the screen "jumping" when tapping.

**Diagnostic evidence** (from `/tmp/pi-render.log`):
```
R#33 len=294120 rn=2779 [2J|3J|SYNCH|SYNCL|HOME] 
R#36 len=294120 rn=2779 [2J|3J|SYNCH|SYNCL|HOME] 
R#39 len=294120 rn=2779 [2J|3J|SYNCH|SYNCL|HOME] 
... (30+ identical renders)
```

**Fix**: When `firstChanged < prevViewportTop` (changes outside the visible area), instead of calling `fullRender(true)`, just update internal state (`previousLines`, `prevViewportTop`, etc.) and skip the full redraw. The content is above the viewport, so the user can't see it. Update it in memory for when the user scrolls up.

**Confirming the fix**: Modifying the TUI to skip `fullRender(true)` in this case completely eliminated ALL jumping behavior in Termux, while preserving normal terminal scrollback.

### Issue 3: No scrollback when using alternate screen buffer

As a test, we tried using the alternate screen buffer (`\x1b[?1049h`/`\x1b[?1049l`) like OpenCode does. This isolated pi's rendering from the terminal scrollback and also fixed all jumping. However, the user lost the ability to scroll through conversation history because pi doesn't implement internal scroll within the alternate screen buffer.

OpenCode does support scrolling within the alternate screen buffer, so it's possible. Pi would need to:
1. Capture scroll events (mouse wheel, PageUp/PageDown)
2. Adjust `prevViewportTop` accordingly
3. Re-render only the visible portion of the conversation

This is a feature request rather than a bug fix.

### Issue 4 (Additional): Cursor/input behavior when scrolled up

When the user scrolls up (using terminal scrollback) so that pi's input box is no longer visible, typing in Termux's text input area does not populate pi's input box. This is somewhat expected since the input box isn't in the visible viewport, but it creates a UX inconsistency.

## Suggested Fixes (in priority order)

1. **Remove `\x1b[3J` from `fullRender()`** — The CSI 3 J sequence (erase scrollback) is rarely needed and causes issues in Termux. It should be removed or made opt-in.

2. **Replace `fullRender(true)` with state-only update when `firstChanged < prevViewportTop`** — Content changes above the viewport should not trigger a full screen clear and redraw. Update internal state and wait for the user to scroll into the changed area.

3. **Consider using alternate screen buffer** — This is the long-term solution that would isolate pi's rendering from the terminal, preventing all scrollback-related issues. Scroll support would need to be implemented internally (mouse wheel, keyboard shortcuts).

## Working Monkey-Patch / Workaround

We created a Node.js loader hook that patches pi-tui at load time (without modifying node_modules). The fix is in two parts:

**`pi-termux-hook.mjs`** — Loader hook that transforms `tui.js` source:
```javascript
// Replace:
//   if (firstChanged < prevViewportTop) {
//       fullRender(true);
//       return;
//   }
// With:
//   if (firstChanged < prevViewportTop) {
//       this.previousLines = newLines;
//       this.previousKittyImageIds = this.collectKittyImageIds(newLines);
//       this.previousWidth = width;
//       this.previousHeight = height;
//       this.previousViewportTop = prevViewportTop;
//       this.positionHardwareCursor(cursorPos, newLines.length);
//       return;
//   }
```

**`pi-termux.mjs`** — Preload script that registers the hook:
```javascript
import { register } from 'node:module';
register('./pi-termux-hook.mjs', import.meta.url);
```

Usage:
```bash
PI_TERMUX_FIX=1 NODE_OPTIONS="--import /path/to/pi-termux.mjs" pi
```

## Related Files

- `packages/pi-tui/src/tui.ts` — Main TUI implementation (contains `fullRender`, `doRender`)
- `packages/pi-tui/src/terminal.ts` — Terminal abstraction (contains `isTermuxSession()` which checks `process.env.TERMUX_VERSION`, but this env var is NOT present when connecting via SSH from Termux — it only exists on the Android device itself)
