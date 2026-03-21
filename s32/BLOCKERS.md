# API Key Creation Blockers

## Working
| Service | Key Storage | Method |
|---------|------------|--------|
| Groq | .env | Fetch intercept, `exposed_secret_key` |
| OpenAI | .env | Fetch intercept, `key.sensitive_id` |

## Blocked

### Anthropic
- **Issue:** OAuth popup closes before CDP can detect it (popup polling too slow)
- **Fix:** Listen for `Page.windowOpen` event to capture popup URL, or use `Target.setDiscoverTargets` before clicking
- **Login page:** `https://console.anthropic.com/login` → "Continue with Google"

### Mistral
- **Issue:** No Google SSO on login page. Redirects to `auth.mistral.ai`
- **Fix:** Need email/password flow or detect Mistral's own OAuth button
- **Login page:** `https://console.mistral.ai/login`

### Cohere
- **Issue:** Not tested yet. Has "Continue with Google" button
- **Fix:** Login, inspect keys page, add selectors to CSV
- **Login page:** `https://dashboard.cohere.com/welcome/login`

### OpenRouter
- **Issue:** Not tested yet. Uses Clerk auth with Google SSO
- **Fix:** Login, inspect keys page. Has `intercept_fetch` endpoint configured
- **Login page:** `https://openrouter.ai/sign-in`

### AI21
- **Issue:** Logged in but keys page returned empty body (may need longer load)
- **Fix:** Increase sleep time, re-inspect page
- **Login page:** `https://studio.ai21.com/v2/login`

### DeepSeek
- **Issue:** Redirects to sign-in page despite previous login
- **Fix:** Fresh login needed
- **Login page:** `https://platform.deepseek.com/sign_in`

### HuggingFace
- **Issue:** Not tested yet. Has "New token" button text configured
- **Fix:** Login, inspect tokens page, verify selectors
- **Login page:** `https://huggingface.co/login`

### ElevenLabs
- **Issue:** Stuck on onboarding page, can't reach API keys page
- **Fix:** User must complete onboarding first at `https://elevenlabs.io/app/onboarding`
- **Login page:** `https://elevenlabs.io/app/sign-in`

### Google AI Studio
- **Issue:** Uses gRPC-web, not fetch. Fetch interceptor doesn't capture API responses
- **Fix:** Intercept `XMLHttpRequest` instead of `fetch`, or use clipboard copy approach (click "Copy" button, read clipboard)
- **Login page:** Direct Google auth at `https://aistudio.google.com/`
