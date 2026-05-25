# Unified API Design — Mobile Framework

## Philosophy

Every Android API call should feel like telling a human what to do.
Not like filling out a customs form.

## Comparison

### TODAY (Android)

```kotlin
// Insert text into focused field
val node = findFocusedNode()
val args = Bundle().apply {
    putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, "hello")
}
node?.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)

// Enter / submit
val args = Bundle()
args.putInt("android.view.accessibility.action.ARGUMENT_IME_ACTION_ID", EditorInfo.IME_ACTION_DONE)
focused.performAction(0x10001000, args)

// Voice recognition
val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, LANGUAGE_MODEL_FREE_FORM)
    putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
}
speechRecognizer.startListening(intent)
```

Every line requires looking up docs. Names are cryptic, IDs are magic numbers, arguments are strings that look like filesystem paths.

### TOMORROW (Unified API)

```python
accessibility.write("hello")
accessibility.enter()           # auto-chooses: IME, keyboard button, clipboard
voice.listen(lang="en")         # returns text when done
```

Three lines. No imports. No Bundle. No magic numbers. No remembering which extra goes with which intent.

## Design principles

### 1. FEW TOKENS (less to remember)

Rule: max 2 words per action.

| Android (5-8 words) | New API (1-2 words) |
|------------------------|------------------------|
| `AccessibilityNodeInfo.ACTION_SET_TEXT` | `accessibility.write()` |
| `RecognizerIntent.EXTRA_LANGUAGE` | `voice.listen(lang=)` |
| `WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY` | `overlay.show()` |
| `Settings.ACTION_MANAGE_OVERLAY_PERMISSION` | `permissions.request("overlay")` |
| `AccessibilityNodeInfo.AccessibilityAction.ACTION_CLICK` | `accessibility.tap(x, y)` |

### 2. SIMPLE VALUES

| Android | New API |
|---------|----------|
| `EditorInfo.IME_ACTION_DONE` (int 6) | `"send"`, `"search"`, `"next"`, `"done"` |
| `SpeechRecognizer.ERROR_NETWORK` (int 2) | `"network"`, `"permission"`, `"no speech"`, `"language"` |
| `MotionEvent.ACTION_DOWN` (int 0) | handled internally by the framework |
| `KeyEvent.KEYCODE_ENTER` (int 66) | `"enter"`, `"back"`, `"home"`, `"tab"` |
| `AccessibilityNodeInfo.ACTION_ARGUMENT_IME_ACTION_ID` | handled internally |

### 3. AUTOMATIC FALLBACKS

```python
accessibility.enter()
# Internally tries in order:
# 1. IME action DONE/SEND/SEARCH/GO/NEXT
# 2. Find "Send/Go/Search" button in keyboard IME window
# 3. Clipboard + paste of newline
# 4. If all fail → clear error: "could not simulate Enter on this field"
```

### 4. READABLE ERRORS

```python
# Today:
performAction(0x10001000, args)  # → true/false. No explanation.

# New API:
accessibility.enter()
# → "Enter sent via IME action (DONE)"
# → "Enter sent via IME keyboard button 'Send'"
# → Error: "no focused field found to write into"
```

### 5. AUTOMATIC LOGGING

Every action is logged automatically with timestamp, fallback path used, duration.
No need to manually call `addLog()`.

## API skeleton

```python
# Module: accessibility
accessibility.write(text: str)                # insert text into focused field
accessibility.enter(action="send")            # "send"|"search"|"next"|"done"|"newline"
accessibility.key(key: str)                   # "enter"|"back"|"home"|"tab"|"escape"|"up"|"down"
accessibility.field() -> dict                 # {text, cursor, selection}
accessibility.tap(x, y)                       # tap at coordinates
accessibility.read_screen() -> str            # get all visible text

# Module: voice
voice.listen(lang="en", silence=5.0)          # listen and return text
voice.partials(callback)                      # receive text while speaking
voice.stop()

# Module: overlay
overlay.show()
overlay.hide()
overlay.position(x, y)
overlay.button(icon="🎤", action="voice")

# Module: permissions
permissions.request("overlay")
permissions.request("microphone")
permissions.request("notifications")
permissions.status()  # → dict with all permissions and their state

# Module: config
config.load("path/to/file.json")
config.set("voice.lang", "en")
config.save()

# Module: telemetry
telemetry.send(type="event", message="...")
telemetry.logs()       # → log buffer
```

## Simple values vs Android constants

| Concept | New API | Android |
|----------|-----------|---------|
| Language | `"en"`, `"es"`, `"fr"` | `Locale("en", "US")` |
| Enter action | `"send"`, `"search"`, `"next"` | `EditorInfo.IME_ACTION_SEND` (int 4) |
| Click type | `"tap"`, `"long"` | `GestureDetector` + `MotionEvent` |
| Permission | `"microphone"`, `"overlay"`, `"notifications"` | Each has its own intent + code path |
| Voice error | `"network"`, `"permission"`, `"no speech"`, `"language"` | `SpeechRecognizer.ERROR_NETWORK` (int 2) |
| Key | `"enter"`, `"back"`, `"home"`, `"tab"` | `KeyEvent.KEYCODE_ENTER` (int 66) |

## What makes an API "easy to learn"

1. **Consistency**: all functions follow the same pattern
2. **Discoverability**: `accessibility.` + TAB shows everything available
3. **Zero imports**: everything comes from the same namespace
4. **Predictable values**: if a param is `lang`, it accepts `"en"`, you don't have to remember `Locale`
5. **Errors that explain**: not `false` or `null`
6. **Max 3 levels of nesting**: `accessibility.write("hello")` not `node.performAction(Bundle(ACTION_SET_TEXT, ...))`
7. **Docs that fit on one page**: not 300 methods with 80 constants each

## Conclusion

> An API should feel like giving instructions to an assistant, not programming a microcontroller.

If every common action is expressed in 1-2 words with simple English values, the framework is learnable in an afternoon. That's the standard.
