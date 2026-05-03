# 🔥 Bun in 100 Seconds

> **Format:** Fireship-style rapid-fire explainer
> **Total runtime:** ~100 seconds
> **Tone:** Dry humor, code-dense, zero fluff

---

## TIMESTAMPS & BEATS

### [0:00–0:04] HOOK — The Problem

**VISUAL:** Side-by-side terminal. Left: `npm install` with a progress bar crawling. Right: `bun install` instant, 0.00s output.

**TEXT OVERLAY:**
```
npm install: 47s
bun install:  0.00s
```

**NARRATION (deadpan):**
> "You spend 30% of your career waiting for `npm install`. Bun looked at that and chose violence."

---

### [0:04–0:12] WHAT IS BUN

**VISUAL:** Bun logo animation → architecture diagram: JS/TS runtime + Bundler + Package manager + Test runner, all in one box, powered by Zig + JavaScriptCore.

**TEXT OVERLAY:**
```
Bun = Runtime + Bundler + Package Manager + Test Runner
      Written in Zig. Uses JavaScriptCore. Not V8.
```

**NARRATION:**
> "Bun is an all-in-one JavaScript runtime. It's a runtime, bundler, package manager, and test runner. Written in Zig. Powered by JavaScriptCore from WebKit — not V8. One tool. Four jobs. Ship it."

---

### [0:12–0:22] INSTALLATION & HELLO WORLD — Code Block #1

**VISUAL:** Terminal recording — commands typed in real-time.

```bash
# Install Bun (macOS / Linux / WSL)
curl -fsSL https://bun.sh/install | bash

# Run TypeScript directly. No tsc. No config.
bun run index.ts
```

```ts
// index.ts — just works. No tsconfig.
const server = Bun.serve({
  port: 3000,
  fetch(req) {
    return new Response("Hello from Bun");
  },
});

console.log(`Listening on ${server.url}`);
```

**TEXT OVERLAY (mid-screen):**
```
Native TypeScript. Zero config. Zero compile step.
```

**NARRATION:**
> "Install with one curl. Run TypeScript directly — no tsc, no tsconfig, no existential dread. Bun parses TS natively. Here's a full HTTP server in eight lines. No Express. No dependencies. It just runs."

---

### [0:22–0:38] PACKAGE MANAGER — Code Block #2

**VISUAL:** Split: Left = `time npm install` on a real project. Right = `time bun install` on the same project. npm: 23s. Bun: 0.4s.

```bash
# Drop-in replacement for npm
bun install              # reads your package.json
bun add express          # add a dependency
bun remove express       # remove it
bunx create-next-app .   # npx equivalent, but fast
```

**TEXT OVERLAY:**
```
Hardlink cache. No duplicate downloads.
Lockfile: bun.lockb (binary, faster to parse)
```

**NARRATION:**
> "Bun's package manager is a drop-in replacement for npm. It hardlinks packages from a global cache — so installing the same dependency across ten projects costs zero disk and zero time. It reads your existing package.json. The lockfile is binary because parsing JSON at scale is a waste of your finite lifespan."

---

### [0:38–0:50] BUNDLER — Code Block #3

**VISUAL:** Terminal + file tree animation.

```bash
# Bundle for production — one command
bun build ./src/index.ts --outdir ./dist --target node

# With minification
bun build ./src/app.tsx --outdir ./dist --minify
```

```ts
// Dynamic imports? Tree shaking? Code splitting?
// Yes. Out of the box.
import("./heavy-module").then((mod) => mod.init());
```

**TEXT OVERLAY:**
```
esbuild speed. Built in. No plugin config.
```

**NARRATION:**
> "Need a bundler? It's built in. `bun build` runs at esbuild speeds because it's also written in a systems language that doesn't mess around. Tree shaking, code splitting, minification — all native. No webpack plugins. No four-hour config debugging session."

---

### [0:50–1:02] TEST RUNNER — Code Block #4

**VISUAL:** Terminal showing test output with green checkmarks.

```bash
# Run tests — Jest-compatible API
bun test
```

```ts
// sum.test.ts
import { expect, test, describe } from "bun:test";
import { sum } from "./sum";

describe("sum", () => {
  test("adds numbers", () => {
    expect(sum(1, 2)).toBe(3);
  });

  test("handles negatives", () => {
    expect(sum(-1, 1)).toBe(0);
  });
});
```

**TEXT OVERLAY:**
```
Jest-compatible. 100x faster on large suites.
No mocking library needed — it's built in.
```

**NARRATION:**
> "And a test runner. Jest-compatible API — your existing tests probably just work. On large test suites, Bun is up to a hundred times faster. It also ships with built-in mocking, so you can delete that `jest-mock-extended` dependency and pretend you never needed it."

---

### [1:02–1:15] BENCHMARKS & COMPETITION

**VISUAL:** Animated bar chart:

| Metric | Node 22 | Deno 1.44 | Bun 1.1 |
|---|---|---|---|
| HTTP req/s | ~65k | ~70k | ~160k |
| Install speed (1k deps) | 23s | 14s | 0.4s |
| Cold start | 40ms | 25ms | 5ms |
| TS support | experimental | native | native |

**TEXT OVERLAY:**
```
"Not the only game in town. But the fastest."
```

**NARRATION:**
> "Benchmarks — take with a grain of salt, as always. But Bun consistently outperforms Node on raw throughput and cold start. Deno is the other contender — stronger security model, better DX defaults — but Bun's package manager compatibility gives it an edge for migrating existing projects."

---

### [1:15–1:28] THE TRADEOFFS — Honest Segment

**VISUAL:** Text on dark background, no frills.

**TEXT OVERLAY (typed out, line by line):**
```
❌ Still v1.x — APIs may shift
❌ Smaller ecosystem than Node (but growing fast)
❌ JavaScriptCore quirks differ from V8 edge cases
✅ Node-compatible: most npm packages work out of the box
✅ SQLite built in. Yes, really.
```

**NARRATION:**
> "Reality check. Bun is young. Some Node APIs are still being polyfilled. You might hit a V8-specific edge case that doesn't exist in JavaScriptCore. But — most npm packages just work. Express works. Next.js works. Prisma works. And if you need a database, there's a built-in SQLite driver. For free. In the runtime."

---

### [1:28–1:37] WHO SHOULD USE THIS

**VISUAL:** Quick logos flying in — each with a one-liner.

**TEXT OVERLAY:**
```
✅ You: want faster dev loops and CI builds
✅ You: starting a new project from scratch
✅ You: tired of configuring 5 tools that do 1 job

❌ Not you: need battle-tested stability (use Node)
❌ Not you: deep Node ecosystem dependencies (wait for v2)
```

**NARRATION:**
> "If you're starting greenfield, building scripts, or just tired of your CI pipeline taking eight minutes to install node_modules — Bun is a serious upgrade. If you're maintaining a ten-year-old Express monolith... maybe wait for version two."

---

### [1:37–1:40] OUTRO CTA

**VISUAL:** Fireship-style subscribe animation.

**TEXT OVERLAY:**
```
🔥 bun.sh
⭐ Star the repo
👊 Like & subscribe
```

**NARRATION:**
> "Link in the description. Star the repo. Like and subscribe. Or don't. I'm a script, not a cop."

---

## PRODUCTION NOTES

### Visual Style
- **Font:** JetBrains Mono for code, Inter for overlays
- **Colors:** Dark bg (#0a0a0a), accent coral/orange (#FBF0DF → #F9A826 gradient), code syntax: One Dark Pro
- **Transitions:** Hard cuts, no dissolves. Zoom-ins on key code lines.
- **Code blocks:** Typing animation, ~40 chars/sec, syntax highlighted
- **Bun branding:** Use Bun's warm tan/gold color (#FBF0DF) as accent where relevant

### Audio
- **Music:** Lo-fi synth, low volume, subtle — think Fireship's background tracks
- **SFX:** Subtle "whoosh" on transitions, "click" on code highlights, "ding" on benchmark wins
- **Voice:** Fast but clear. Dry delivery. No hype voice. Let the numbers scream.

### Text Overlay Rules
- Max 2 lines visible at once
- Appear synced with narration
- Key numbers/statistics: **bold + larger font**
- Code snippets: monospace, syntax-highlighted, ~60% screen width
- Speed comparisons: animate as racing bar charts

### Pacing Checklist
- [ ] No segment exceeds 15 seconds
- [ ] At least one code block every 12 seconds
- [ ] Every claim backed by a number or visual proof
- [ ] One honest "here's the catch" moment
- [ ] Ends with a punchline, not a plea

---

## SCRIPT STATS

| Metric | Value |
|---|---|
| Word count | ~520 |
| Estimated read time | ~97 sec |
| Code blocks | 5 |
| Text overlays | 14 |
| Jokes | 4 |
| Times "npm install" dunked on | 3 |
