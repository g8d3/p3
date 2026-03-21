# LEARNINGS.md

Context handoff for new sessions. These are non-obvious discoveries that took
significant trial-and-error to find. A new AI session needs these to avoid
re-discovering them.

## Chrome CDP

- **Popup blocker:** `Runtime.evaluate("el.click()")` is blocked by Chrome's popup
  blocker. Must use `Input.dispatchMouseEvent` (real mouse events) AND
  `Browser.grantPermissions({permissions: ["windowManagement"], origin})` before clicking.
- **Session detach:** When a page navigates cross-origin (e.g., Google → Firebase handler),
  the CDP session detaches. Wrap all popup interaction in try/catch.
- **Firebase Auth flow:** Sites using Firebase Auth (ElevenLabs) open a popup to
  `/__/auth/handler` which then redirects to Google. The handler needs `window.opener`
  to send the auth result back. If you navigate the same tab instead of opening a popup,
  there's no opener and auth hangs forever.
- **Tab cleanup:** Orphan tabs accumulate and eventually crash Chrome. Always close tabs
  in finally blocks. Chrome crashes manifest as silent death — no crash log, CDP port
  just stops responding.
- **Page hydration:** Next.js pages need time to hydrate. Poll for button existence
  instead of fixed sleep. Some pages (AI21) need 8+ seconds.
- **Popup vs redirect:** Some sites (Mistral) redirect the current tab to Google instead
  of opening a popup. The script must handle both: race new-target detection against
  same-tab URL change.
- **Image-only buttons:** Many sites (Mistral, Cohere) have Google SSO buttons with no
  text — just an `<img alt="Google">`. Text search must also check for images with
  "google" in alt/src inside clickable elements.
- **Vision LLM fallback:** When text + image search fails, take a screenshot via
  `Page.captureScreenshot` and send to a vision LLM. Ask for button coordinates.
  Works universally regardless of DOM structure. Requires `--llm-base-url`,
  `--llm-api-key`, `--llm-model` flags.

## CSV Format

- **Standard CSV with quoting:** Regex patterns like `{20,}` contain commas. Must use
  RFC 4180 parser that handles `"^[A-Za-z0-9]{20,}$"` correctly. Don't use pipe
  delimiter — Rainbow CSV and other tools don't support it.
- **Parser implementation:** Simple split-on-comma fails. Need state machine that tracks
  quote boundaries. See `parseCSVLine()` in create-api-key.js.

## Service-Specific

- **Groq:** Has undocumented REST API for key creation. Intercept `fetch` to
  `api.groq.com/platform/v1/organizations/.../api_keys`. Response has
  `exposed_secret_key` (full key) and `secret_key` (masked).
- **OpenAI:** Key creation response has nested field `key.sensitive_id`, not top-level
  `key`. The fetch interceptor must handle dot-notation paths.
- **Google AI Studio:** Uses gRPC-web, not fetch. Need to intercept `XMLHttpRequest`
  or use clipboard copy approach.
- **ElevenLabs:** Uses Firebase Auth popup. User must complete onboarding before
  accessing API keys page.
- **Mistral:** No Google SSO. Redirects to `auth.mistral.ai` with its own flow.

## Architecture Decisions

- **Hybrid LLM+CSV:** CSV caches selectors (fast, free). LLM discovers new selectors
  on cache miss (slow, flexible). LLM writes back to CSV. Best of both worlds.
- **Fetch intercept > DOM scraping:** Intercepting API responses is more reliable than
  reading keys from DOM. Keys are often shown once in a toast that auto-dismisses.
- **Text-based button fallback:** Not all sites have `data-testid`. CSV has both
  `create_btn_selector` (CSS) and `create_btn_text` (text content match).
  `clickButton()` tries CSS first, falls back to text.
- **Key storage:** Support .env (default), .zshrc, and Bitwarden CLI. One key per
  service, overwrite on re-creation.

## File Structure

```
s32/
  ai-services.csv       # Single source of truth: URLs, selectors, endpoints, status
  create-api-key.js     # Main script: login → navigate → create → save
  google-sso-login.js   # Google SSO via CDP: popup permission + mouse events
  logout-app.js         # Clear cookies/storage for clean test cycles
  BLOCKERS.md           # Per-service issues and proposed fixes
  LEARNINGS.md          # This file: non-obvious discoveries
  .env                  # Generated: API keys (gitignored)
  api-keys.csv          # Generated: key creation log (gitignored)
```
