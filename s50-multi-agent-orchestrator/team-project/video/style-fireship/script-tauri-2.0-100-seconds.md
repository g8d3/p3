# 🔥 Tauri 2.0 in 100 Seconds

> **Format:** Fireship-style rapid-fire explainer
> **Total runtime:** ~100 seconds
> **Tone:** Dry humor, code-dense, zero fluff

---

## TIMESTAMPS & BEATS

### [0:00–0:04] HOOK — The Problem

**VISUAL:** Split screen. Left: Electron app consuming 800MB RAM in Task Manager. Right: Tauri app at 12MB.

**TEXT OVERLAY:**
```
Electron: 800MB
Tauri:    12MB
```

**NARRATION (deadpan):**
> "Electron gave us Slack, VS Code, and a reason to buy more RAM. Tauri 2.0 says: what if we didn't need 800 megabytes to render a chat app?"

---

### [0:04–0:12] WHAT IS TAURI

**VISUAL:** Tauri logo animation → quick diagram: Frontend (HTML/CSS/JS) ↔ Rust backend ↔ Native OS

**TEXT OVERLAY:**
```
Tauri = Rust backend + Any frontend
        ↓
   Native binary. Not Chromium.
```

**NARRATION:**
> "Tauri is a framework for building desktop and mobile apps. Your frontend — React, Svelte, Vue, whatever — talks to a Rust backend through an IPC bridge. No bundled Chromium. No Node runtime. Just a native binary that uses the OS webview."

---

### [0:12–0:22] SCAFFOLDING — Code Block #1

**VISUAL:** Terminal recording — commands typed in real-time.

```bash
# Install the CLI
cargo install create-tauri-app

# Scaffold a new project (React + TypeScript)
cargo create-tauri-app my-app --template react-ts

cd my-app
cargo tauri dev
```

**TEXT OVERLAY (mid-screen):**
```
3 commands. That's it.
```

**NARRATION:**
> "Three commands. You now have a native app with hot reload. No webpack config. No existential crisis."

---

### [0:22–0:38] IPC — Code Block #2

**VISUAL:** Split: Left = Rust backend file, Right = React frontend file. Highlight connections.

**Rust side (`src-tauri/src/lib.rs`):**
```rust
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! From Rust.", name)
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![greet])
        .run(tauri::generate_context!())
        .expect("failed to run");
}
```

**Frontend side (`src/App.tsx`):**
```tsx
import { invoke } from "@tauri-apps/api/core";

const greeting = await invoke("greet", { name: "Fireship" });
// → "Hello, Fireship! From Rust."
```

**TEXT OVERLAY:**
```
invoke() → Rust function
Type-safe. Async. Zero boilerplate.
```

**NARRATION:**
> "Frontend calls Rust with invoke. That's it. It's type-safe, async, and serializes data through serde. No REST endpoints. No GraphQL. Just function calls across the void."

---

### [0:38–0:50] PLUGINS & PERMISSIONS — Code Block #3

**VISUAL:** `capabilities/default.json` file + terminal showing `cargo tauri add`

```json
{
  "identifier": "main-capability",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "dialog:allow-open",
    "fs:allow-read",
    "shell:allow-open"
  ]
}
```

```bash
# Add a plugin in one command
cargo tauri plugin add notification
```

**TEXT OVERLAY:**
```
Capabilities = fine-grained permissions
No "access everything" mode.
```

**NARRATION:**
> "Tauri 2.0 introduces capabilities — a permission system inspired by Android. You declare exactly what each window can do. File access. Notifications. Camera. No more 'this app can read your entire filesystem and also your thoughts.'"

---

### [0:50–1:02] MOBILE SUPPORT — Code Block #4

**VISUAL:** Terminal + iOS Simulator and Android Emulator side by side.

```bash
# Initialize mobile targets
cargo tauri ios init
cargo tauri android init

# Run on iOS simulator
cargo tauri ios dev

# Run on Android emulator
cargo tauri android dev
```

**TEXT OVERLAY:**
```
Same codebase. Desktop + iOS + Android.
One Rust backend. Three platforms.
```

**NARRATION:**
> "The headline feature: mobile support. Same codebase, same Rust backend, now runs on iOS and Android. You're not writing Swift AND Kotlin AND JavaScript. Just JavaScript. Let Rust handle the rest."

---

### [1:02–1:15] SIZE & PERFORMANCE COMPARISON

**VISUAL:** Animated bar chart comparing:

| Metric | Electron | Tauri 2.0 |
|---|---|---|
| Bundle size | ~150MB | ~3MB |
| Memory (idle) | ~300MB | ~15MB |
| Startup time | ~2s | ~0.3s |
| Language | C++ / Node | Rust |

**TEXT OVERLAY:**
```
3MB installer. Let that sink in.
```

**NARRATION:**
> "Three. Megabyte. Installer. Electron's is fifty times larger. Tauri doesn't ship a browser — it borrows yours. WebKit on macOS. WebView2 on Windows. WebKitGTK on Linux."

---

### [1:15–1:28] THE TRADEOFFS — Honest Segment

**VISUAL:** Text on dark background, no frills.

**TEXT OVERLAY (typed out, line by line):**
```
❌ No access to Chrome DevTools extensions
❌ WebView inconsistencies across OS
❌ Rust learning curve (you WILL fight the borrow checker)
✅ But: memory safety, native speed, tiny binaries
```

**NARRATION:**
> "Honesty hour. Webviews aren't identical — Safari on macOS, Chromium on Windows, GTK on Linux. You'll hit CSS quirks. And if you don't know Rust, there's a learning curve. The compiler will reject your code. Repeatedly. It's building character."

---

### [1:28–1:37] WHO SHOULD USE THIS

**VISUAL:** Quick logos flying in — each with a one-liner.

**TEXT OVERLAY:**
```
✅ You: ship lightweight desktop/mobile apps
✅ You: know (or want to learn) Rust
✅ You: hate shipping 150MB for a calculator app

❌ Not you: need Chromium-specific APIs
❌ Not you: allergic to new things
```

**NARRATION:**
> "If you build internal tools, indie apps, or just refuse to ship a 150-megabyte calculator — Tauri is your weapon. If you need Chrome extensions or deep Chromium APIs... Electron still has you. For now."

---

### [1:37–1:40] OUTRO CTA

**VISUAL:** Fireship-style subscribe animation.

**TEXT OVERLAY:**
```
🔥 tauri.app
⭐ Star the repo
👊 Like & subscribe
```

**NARRATION:**
> "Link in the description. Star the repo. Like and subscribe. Or don't. I'm a script, not a cop."

---

## PRODUCTION NOTES

### Visual Style
- **Font:** JetBrains Mono for code, Inter for overlays
- **Colors:** Dark bg (#0a0a0a), accent orange (#FF6B35), code syntax: Dracula theme
- **Transitions:** Hard cuts, no dissolves. Zoom-ins on key code lines.
- **Code blocks:** Typing animation, ~40 chars/sec, syntax highlighted

### Audio
- **Music:** Lo-fi synth, low volume, subtle — think Fireship's background tracks
- **SFX:** Subtle "whoosh" on transitions, "click" on code highlights
- **Voice:** Fast but clear. Dry delivery. No hype voice.

### Text Overlay Rules
- Max 2 lines visible at once
- Appear synced with narration
- Key numbers/statistics: **bold + larger font**
- Code snippets: monospace, syntax-highlighted, ~60% screen width

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
| Word count | ~480 |
| Estimated read time | ~95 sec |
| Code blocks | 4 |
| Text overlays | 12 |
| Jokes | 3 |
| Times "borrow checker" mentioned | 1 (restraint) |
