# Security Knowledge Base

> Central place for all security observations, recommendations, and remediation
> related to this system's API keys, credentials, and access control.

---

## Current State (as of 2026-04-29)

### ✅ Properly Managed: OpenCode Auth Store

OpenCode has a built-in credential store at `~/.local/share/opencode/auth.json`
with `chmod 600` (owner read/write only). Currently stores:

| Provider    | Type | Notes                        |
|-------------|------|------------------------------|
| Google      | API  | Shared with GEMINI_API_KEY   |
| Cerebras    | API  | AI inference                 |
| Z.AI Coding | API  | Coding plan                  |
| Chutes      | API  | TTS (shared with env)        |
| OpenCode Go | API  | OpenCode Go credits          |

**Recommendation:** Use `opencode auth add <provider>` instead of env vars when
possible. This keeps keys in a single encrypted-adjacent location with proper
file permissions.

### ✅ Properly Managed: Environment Variables

Keys set via shell RC files (`.zshrc` etc.) and inherited by processes.
These are **not** hardcoded in any opencode config files.

### ❌ Issues Found: Hardcoded Keys in `.env` Files

The following files contain plaintext API keys that could be committed to git.
(Actual key values redacted from this file — see the files directly if needed.)

1. **`/home/vuos/code/browser-use-web-ui/web-ui/.env`**
   - Contains `DEEPSEEK_API_KEY`
   - Risk: High. Repo may be pushed to GitHub.

2. **`/home/vuos/code/web9-agent/impls/old/19-agents-mine/.env`**
   - Contains `GEMINI_API_KEY`
   - Risk: High. Old project tracked in git.

3. **`/home/vuos/code/p3/s32/.env`**
   - Contains `OPENAI_API_KEY`
   - Risk: High if tracked in git.

**Recommended action:** Delete these `.env` files — they can be regenerated from
environment variables when needed. The keys should also be rotated at their
respective provider dashboards since they've been exposed in the filesystem.

### ✅ Properly Managed: OpenCode Config

`~/.config/opencode/opencode.json` has **no** hardcoded keys. MCP configs use
safe commands (`npx @playwright/mcp@latest --cdp-endpoint ...`) with no
embedded secrets.

### ⚠️ Note: CDP Browser MCP is Disabled

In `opencode.json`:
```json
"my-brave-browser": { "enabled": false }
```

The Playwright MCP connected to Chrome via CDP (port 9222) exists but is
disabled. If enabled, it would give opencode sessions direct browser control
via MCP — which is powerful but means every opencode session could browse
as the logged-in user. Consider enabling only for specific agents.

---

## Recommendations

### 1. Rotate and Cleanse Exposed Keys

For each `.env` file with hardcoded keys:
- Rotate the key at the provider's dashboard
- Replace the value with `$VAR_NAME` or leave blank with a comment
- Verify `.gitignore` includes `.env` and `.env.*` (not `.env.example`)

### 2. Prefer `opencode auth` Over Env Vars

For any new provider:
```bash
opencode auth add <provider-name> --type api --key <value>
```
Then reference in config as `$PROVIDER_NAME_API_KEY`.

### 3. .env File Hygiene

- Keep `.env.example` files with placeholder values in git
- Add `.env` and `.env.*` to `.gitignore` at the repo root
- Consider a single `.env` at `~/code/.env` sourced by all projects

### 4. Permission Awareness

The opencode agents have specific permission rules. Currently:
- `question` is `deny` in `build`, `compaction`, `summary`, `title` agents
- `question` is `allow` in `plan` agent
- `read *.env` requires explicit `ask` (good — it prompts before reading)

This is a reasonable setup. Only the `plan` agent can ask questions, which
means non-interactive agents (`build`, `summary`) can run autonomously.

### 5. Future: Credential Isolation

If a prepaid debit card is added for services:
- Keep those credentials in a separate env file sourced only when needed
- Never hardcode in git-tracked files
- Consider a dedicated `~/.secrets/` directory with tight permissions

---

## Security Scan Commands

```bash
# Find potential hardcoded keys in the workspace
find ~/code -name '.env' -not -path '*/node_modules/*' -not -path '*/.git/*' \
  -exec rg -l '(sk-[a-zA-Z0-9]{20,}|AIzaSy[A-Za-z0-9_-]{20,}|cpk_)' {} \;

# Check permissions on sensitive files
ls -la ~/.local/share/opencode/auth.json
ls -la ~/.config/opencode/

# List all opendcode-stored credentials
opencode auth list
```
