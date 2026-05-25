# VoiceButtonApp Development — Postmortem Analysis

## Concrete metrics

| Metric | Value |
|---------|-------|
| Kotlin code | 1,452 lines across 8 files (64 KB) |
| XML layouts | 463 lines across 14 files (17 KB) |
| Python server | 274 lines (serve_apk.py) |
| **Total source** | **~2,189 lines, ~81 KB** |
| Compiled APK | **5.8 MB** |
| Full project (excluding build) | **2.6 MB** |
| Largest file | `MainActivity.kt` (545 lines) |
| Most complex file | `FloatingButtonService.kt` (310 lines: overlay + voice + animation) |
| Source files total | 22 (8 .kt, 14 .xml) |
| HANDOFF.md | 7,914 bytes |

## Feedback loop

| Phase | Typical time |
|-------|-------------|
| Read code + understand change | 10-30s |
| Edit files | 5-20s |
| Compile (Gradle incremental) | 1-3s |
| Compile (Gradle clean) | 10-15s |
| Install via ADB | 3-5s |
| User test + report results | 10-60s |
| **Full cycle** | **30s - 2min** |

For each subtle bug (IME action, hint text, fail-silent), 10-15 cycles were needed. That is 30-45 minutes of real time per bug.

---

## Structural problems found

### 1. Domino effect in code

A small change touches many layers. Example: adding `language` to `ButtonConfig`:
- `ButtonConfig.kt` (data class + Parcelable)
- `ButtonStorage.kt` (JSON serialization)
- `dialog_button_config.xml` (add Spinner to layout)
- `MainActivity.kt` (dialog logic, language options, save)
- `FloatingButtonService.kt` (pass language to SpeechRecognizer intent)

If `ButtonConfig` lived in an external JSON schema instead of code, the change would be one file edit + restart — no compilation needed.

### 2. Fail-silent bugs (the worst enemy)

Several bugs manifested as "nothing happens" with no visible error.

| Symptom | Root cause | Time to detect |
|---------|-----------|----------------|
| Voice recognition does not transcribe | `onResults` returns text=null (mic permission? language not installed?) | Multiple cycles until logs were added |
| Telemetry never reaches server | POST from `addLog()` companion object fails silently (empty catch) | Never fully diagnosed |
| Enter does nothing on imeOptions field | `performAction(0x10001000)` returns false with no explanation | ~15 cycles until actionId=4 was seen with physical keyboard |
| Dictated text has hint concatenated | `node.text` returns the hint when EditText is empty | Hours until `suffix='Caja de prueba...'` appeared in logs |

**Pattern**: every `catch (_: Exception) {}` is an information black hole.
The framework should:
- Never swallow exceptions without logging them
- Show visible errors (Toast + log) when something fails
- Have a diagnostic panel with subsystem state (microphone, permissions, accessibility, recognizer, server)

### 3. Zero device visibility

- I cannot see the screen, cannot see live logs
- I depend on you copying and pasting log text
- The EditText hint bug (cursor at -1) was solved in one cycle when we FINALLY saw the correct log entry

Without visual access, even simple bugs require multiple back-and-forth cycles.

### 4. Opaque AccessibilityService

- Very limited API for keyboard-related actions
- `ACTION_PERFORM_IME_ACTION` (0x10001000) is NOT implemented in standard Android EditText — only physical keyboard + native IME can trigger IME actions
- Accessibility actions return `true`/`false` with zero explanation on failure
- Official documentation is incomplete about what each View class implements

**Example that cost us hours**: `findFocusedNode()` returns the EditText, `ACTION_CLICK` returns `true` (the field gets focus) but does NOT trigger the IME action. The only way to discover this was trial and error over many cycles.

### 5. Unnecessary compilation for configuration changes

Changes that required compilation but should not have:
- Language for voice recognition (add a field + Spinner → recompile)
- Silence duration (change an int → recompile)
- Button icons and labels (edit XML → recompile)
- Overlay colors and sizes (edit XML → recompile)
- Server URL (change SharedPreferences → recompile)

**Estimated 80%** of the changes you requested were configuration, not logic. If they lived in an external JSON file, the cycle would be:
- **Today**: edit code → compile → install → test = 2-5 min
- **With config**: edit JSON → restart service = 5-10 seconds

---

## Missing: remote vision and control

The analysis above covers logs and diagnostics but NOT **seeing the screen like a human**.

### The core problem

Today my visibility of the device is zero:
- I cannot see what is on the screen
- I cannot see animations, toasts, popups, virtual keyboards
- I cannot tell if a button is visible, disabled, or nonexistent
- For visual bugs (microphone animation, overlay position, colors), I depend entirely on your description

And my control is indirect:
- I can only inject via AccessibilityService (limited API)
- I cannot tap, swipe, or long-press at arbitrary coordinates
- I cannot interact with elements that the accessibility tree does not expose

### The solution: closed visual loop

```
App on device
    │
    ├─ adb exec-out screencap -p → PNG image
    │      │
    │      ▼
    │  Vision model describes the screen:
    │  "There is a keyboard with a Send button at bottom right"
    │      │
    │      ▼
    │  I decide the next action:
    │  "Tap the Send button at coordinates (950, 1800)"
    │      │
    │      ▼
    ├─ adb shell input tap 950 1800
    │
    └─ visible change → new screencap → repeat
```

This closes the circle:
- **I see** what happens (screencap + vision) → instant diagnosis
- **I control** like a human (input tap/swipe/text) → no AccessibilityService limits
- **Cycle time**: ~2-3 seconds per visual iteration

### What this would enable in practice

Bugs that took us hours would resolve in seconds:

- "The Enter button does not work" → I see the keyboard on screen, I see if there is a Send button, I see if it is visible or grayed out
- "The microphone animation looks wrong" → I see the exact frame, the color, whether it pulses the button background or the inner ball
- "The overlay went to the corner of the screen" → I see exactly where it is
- "The Toast looks ugly" → I see the Toast, I read the text
- "The field has weird text after dictation" → I see the field content directly

### How to integrate it into the framework

The framework should expose a remote control endpoint (WebSocket or HTTP):

```
GET  /screenshot           → PNG image of screen
POST /input/tap            { x, y }
POST /input/text           { text }
POST /input/swipe          { x1, y1, x2, y2, duration_ms }
POST /input/key            { keycode }
GET  /accessibility/tree   → full node tree as JSON
GET  /logs                 → live log buffer (SSE or WebSocket)
```

With this, any external agent (me, a script, a different model) can:
1. Take a screenshot
2. Analyze it with a vision model
3. Decide what to tap
4. Execute the tap
5. See the result
6. Repeat until the goal is achieved

### Current state: tools already exist

In my environment there are two skills that follow exactly this pattern:

- **`cdp`** (Total browser control): agent-browser + Chrome CDP for navigating, clicking, filling forms, taking snapshots with element references. Same concept, for web browsers.
- **`screen-debug`**: uses xdotool/xprop/at-spi2 for desktop GUI accessibility, falls back to vision model if the accessibility tree is insufficient.

These are designed for desktop Linux, not Android. But the pattern is identical:

| Desktop component | Android equivalent |
|-------------------|-------------------|
| xdotool (click, type) | `adb shell input tap/text/swipe` |
| xprop / at-spi2 tree | `uiautomator dump` / Accessibility node tree |
| Screenshot (import) | `adb exec-out screencap -p` |
| Vision fallback | Same vision model |

### Conclusion

The current analysis covers **what** to build (framework with external config, hot-reload, unified accessibility API, telemetry). But for an AI agent to effectively operate the framework, the **remote vision and control** layer is essential.

This should be a first-class requirement, not an afterthought. Without it, I still depend on you describing what you see — which is the biggest bottleneck in the entire development cycle.

---

## Framework design ideas

### Design principles

1. **Configuration over Code**
   - Everything that can be configurable SHOULD be (inputs, outputs, UI, behavior)
   - Schema in JSON/YAML validated against a JSON Schema
   - The app reads config on startup and adapts at runtime

2. **Feedback loop in seconds, not minutes**
   - Hot-reload: change config → see result in <1s
   - Built-in REPL / shell for test commands
   - Live logs with filters, exportable, viewable remotely

3. **Total visibility**
   - Remote screen capture (adb screencap + optional compression)
   - Live logs pushed over WebSocket
   - Inspectable internal state (current config, event buffer, accessibility tree)

4. **Self-developing application**
   - The app loads its own logic from external files
   - Embedded scripting (Lua / Python via Chaquopy / Kotlin scripting)
   - Config editor runs inside the app itself
   - No compilation: the runtime interprets the scripts

### Proposed architecture

```
config.json (external, on device filesystem)
    │ reads
Lightweight runtime (loads scripts, connects inputs to outputs)
    │
Unified accessibility API (write text, key events, IME, tap)
    │
Resulting app (overlay, voice, buttons, telemetry)

Cycle: edit config → signal → runtime reloads → you see the result
```

### Super-configurability

| Category | What should be configurable |
|----------|----------------------------|
| **Input** | Voice: language, min/max silence, partials or final only, language model |
| **Input** | Keyboard: physical key → action mapping |
| **Input** | Gestures: swipe, long-tap, double-tap → custom actions |
| **Output** | Visual feedback: animation type, color, duration, position on screen |
| **Output** | Sound feedback: audio file path, TTS text template |
| **Output** | Haptic feedback: duration, intensity pattern |
| **UI** | Overlay layout: vertical/horizontal, button size, margins, spacing |
| **UI** | Theme: colors, fonts, border radius, shadow, opacity |
| **UI** | Animations: type (fade, slide, scale), speed, easing function |
| **Actions** | Sequences: one button triggers N sub-actions in order with delays |
| **Actions** | Conditions: "if field is empty → do nothing", "if text is selected → replace it" |
| **Behavior** | Persistence: what to save (position, state, config, logs) |
| **Behavior** | Auto-start: on device boot, when certain apps are opened |
| **Behavior** | Timeouts: listen duration, pause between actions, auto-collapse overlay |
| **Integration** | Server: URL, endpoints, auto-report frequency, offline queue |
| **Integration** | IME: default action, keys to intercept and block |
| **Telemetry** | Event types to report, destination, detail level, sampling rate |

### The self-contained app

```
┌──────────────────────────────────────────┐
│  App (the framework runtime)              │
│                                           │
│  ┌────────────────────────────────────┐  │
│  │  Config editor (inside the app)    │  │
│  │  - Change language, silence        │  │
│  │  - Add / remove / reorder buttons  │  │
│  │  - Change colors, sizes, layout    │  │
│  │  - View live logs                  │  │
│  │  - Test actions (Enter, voice)     │  │
│  └────────────────────────────────────┘  │
│                                           │
│  ┌────────────────────────────────────┐  │
│  │  Runtime                           │  │
│  │  - Loads config.json on boot       │  │
│  │  - Executes Lua / Kotlin scripts   │  │
│  │  - Overlay + voice + accessibility │  │
│  │  - Telemetry                       │  │
│  └────────────────────────────────────┘  │
│                                           │
│  ┌────────────────────────────────────┐  │
│  │  Remote console (WebSocket)         │  │
│  │  - Live log stream                 │  │
│  │  - Execute commands                │  │
│  │  - Remote screenshot endpoint      │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

### Why this drastically reduces the cycle

**Before (VoiceButtonApp)**:
You request change → I read code → I edit → compile → install → you test → you report → I diagnose → repeat

One cycle = **3-5 minutes**. For subtle bugs: 10-15 cycles = **45 minutes to 1 hour**.

**With framework + external config**:
You edit config in the app (or edit the JSON file) → the app detects the change → reloads → you see the result

One cycle = **5-10 seconds**. Bug diagnosis = 1-2 cycles with remote vision + logs.

**Compilation only happens** when the runtime itself (the base) needs changes, not when the behavior or configuration changes.

---

## Unified API Design

### Philosophy

Every Android API call should feel like telling a human what to do.
Not like filling out a customs form.

### Comparison

**Today (Android)**:
```kotlin
val node = findFocusedNode()
val args = Bundle().apply {
    putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, "hello")
}
node?.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
```

**Tomorrow (Unified API)**:
```python
accessibility.write("hello")
accessibility.enter()    # auto-chooses fallback path
voice.listen(lang="en")  # returns text
```

### Design principles

1. **Few tokens** — max 2 words per action
   - `accessibility.write()` not `node.performAction(Bundle(ACTION_SET_TEXT_CHARSEQUENCE, ...))`
   - `voice.listen(lang=)` not `Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).putExtra(EXTRA_LANGUAGE, ...)`

2. **Simple values** — strings in English, not magic integers
   - `"send"`, `"search"`, `"done"` instead of `EditorInfo.IME_ACTION_DONE` (int 6)
   - `"network"`, `"permission"`, `"no speech"` instead of `SpeechRecognizer.ERROR_NETWORK` (int 2)
   - `"en"`, `"es"`, `"fr"` instead of `Locale("en", "US")`
   - `"microphone"`, `"overlay"`, `"notifications"` instead of each permission having its own Intent action

3. **Automatic fallbacks**
   - `accessibility.enter()` internally tries: IME action → keyboard Send button → clipboard paste
   - Reports which path was used
   - Returns clear error if everything fails

4. **Readable errors**
   - `"Enter sent via IME action (DONE)"`
   - `"Enter sent via keyboard 'Send' button"`
   - `"Error: no focused field found"`

5. **Automatic logging**
   - Every action is logged with timestamp, path used, duration
   - No manual `addLog()` calls needed

### API skeleton

```python
# Module: accessibility
accessibility.write(text)           # insert text at cursor
accessibility.enter(action="send")  # "send" | "search" | "next" | "done" | "newline"
accessibility.key(name)             # "enter" | "back" | "home" | "tab" | "escape" | "up" | "down"
accessibility.field() -> dict       # { "text": "...", "cursor": 0, "selection": [0, 0] }
accessibility.tap(x, y)             # tap at pixel coordinates
accessibility.read_screen() -> str  # all visible text from screen

# Module: voice
voice.listen(lang="en", silence=5.0) -> str  # listen and return transcribed text
voice.partials(callback)                      # receive partial text while speaking
voice.stop()

# Module: overlay
overlay.show()
overlay.hide()
overlay.position(x, y)
overlay.button(icon="🎤", action="voice")

# Module: permissions
permissions.request("microphone")
permissions.request("overlay")
permissions.request("notifications")
permissions.status() -> dict

# Module: config
config.load("path/to/config.json")
config.get("voice.lang")
config.set("voice.lang", "en")
config.save()

# Module: telemetry
telemetry.send(type="event", message="...")
telemetry.logs() -> list[str]
```

### What makes an API easy to learn

1. **Consistency**: all functions follow the same pattern
2. **Discoverability**: `accessibility.` + TAB shows everything
3. **Zero imports**: everything comes from one namespace
4. **Predictable values**: `lang` accepts `"en"`, not `Locale`
5. **Errors that explain**: not `false` or `null`
6. **Max 3 nesting levels**: `accessibility.write("hello")` not `node.performAction(Bundle(ACTION_SET_TEXT, ...))`
7. **Docs that fit one page**: not 300 methods with 80 constants each

### Why existing frameworks do not solve this

| Framework | Hot reload | External config | Accessibility | Remote vision |
|-----------|-----------|----------------|--------------|--------------|
| Flutter | Yes | Not native | No | No |
| React Native | Fast refresh | Not native | No | No |
| Kotlin Multiplatform | Slow compile | Not native | No | No |
| Expo | OTA updates | Not native | No | No |
| **Proposed framework** | **Config reload** | **Native (JSON)** | **Unified wrapper** | **Built-in** |

No existing framework covers **accessibility cross-app** + **external configuration** + **remote vision/control**. That is the niche.

### What "from scratch" really means

Not a new language or operating system. A **specialized runtime** on top of Android:
- Script interpreter (Lua / Python / Kotlin scripting) — no compilation
- Unified accessibility API — wraps the opaque Android APIs
- Embedded web server — for remote screenshot, tap, logs
- Config loader — everything configurable via JSON, no recompile
- Everything else (UI, overlay, voice) are plugins loaded from config
