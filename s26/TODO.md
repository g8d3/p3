# TODO - Autonomous Video Generator

## Priority 1: Core Functionality
- [ ] **YouTube Upload** - Already fixed (OAuth client secret re-downloaded)
- [ ] **Test YouTube Upload** - Verify it works with new credentials

## Priority 2: Secrets Management
- [ ] **Password Manager Integration** - Use Bitwarden/1Password CLI to store/retrieve API keys
- [ ] **Auto OAuth Flow** - No manual Google Cloud Console setup required

## Priority 3: Ultra Easy Onboarding (One-liner)
- [ ] **Magic Install Script** - `curl | bash` installs everything, user just talks
- [ ] **Auto API Key Creation** - LLM creates Inworld/OpenAI/11Labs keys from user account
- [ ] **Auto Google Cloud Setup** - Program creates OAuth credentials automatically via API
- [ ] **Auto CDP Browser Setup** - Copy user browser profile data automatically
- [ ] **Wizard Mode** - First run guides through all setup automatically

## Priority 4: Video/Audio Quality
- [ ] **More TTS Providers** - Add OpenAI TTS, ElevenLabs support
- [ ] **Subtitles Generation** - Auto-generate SRT/VTT from audio
- [ ] **Better Slide Templates** - Multiple visual styles, backgrounds

## Priority 5: Heavy Lifting in Code
- [ ] **Profiling** - Optimize code to minimize LLM calls
- [ ] **Config-driven Defaults** - Smart defaults reduce LLM interaction
- [ ] **Template System** - Pre-built templates for common video types

## Priority 6: Automation
- [ ] **Local Scheduling** - Cron-style scheduling for automatic uploads
- [ ] **Webhook Triggers** - Generate video on external events
- [ ] **Batch Processing** - Generate multiple videos from list

## Ideas for Later
- [ ] Voice cloning support
- [ ] Multi-language support
- [ ] Background music/ambient audio
- [ ] Transition animations
- [ ] Analytics tracking (views, engagement)
- [ ] Social media auto-posting

---

## Philosophy

**User does ONE thing:** talks/gives instructions

**System does EVERYTHING else:**
- Create API keys automatically
- Set up OAuth credentials
- Copy browser profiles
- Generate videos
- Upload to YouTube
- Schedule posting

**LLM does only creative work:**
- Script writing
- Style decisions
- NOT: technical setup, credentials, infrastructure
