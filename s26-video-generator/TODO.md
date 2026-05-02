# TODO - Autonomous Video Generator

## Core Philosophy
**User does ONE thing:** talks/gives instructions

**System does EVERYTHING else:**
- Create API keys automatically (via scripts → programs)
- Set up OAuth credentials automatically
- Copy browser profiles automatically
- Generate videos automatically
- Upload to YouTube automatically
- Schedule posting automatically

**LLM role:** Builds scripts → Scripts become programs → Human just runs programs

---

## Priority 1: Zero-Wizard Setup
- [ ] **OAuth via Browser** - User clicks once, system handles the rest
- [ ] **API Keys via Chat** - User gives key once, system stores and manages
- [ ] **No Manual Console** - All Google Cloud/Provider setup via API calls

## Priority 2: Auto-Setup Scripts (LLM-written, then automated)
- [ ] **Create Google Cloud Project** - Script calls Cloud Resource Manager API
- [ ] **Enable YouTube API** - Script calls Cloud AI Platform API  
- [ ] **Create OAuth Credentials** - Script calls OAuth2 API
- [ ] **Create TTS Provider Account** - Script navigates provider APIs
- [ ] **Copy CDP Browser Profile** - Script copies browser data directory

## Priority 3: Programmatic Core
- [ ] **Secrets Manager** - Encrypted storage for all API keys/OAuth
- [ ] **Video Pipeline** - End-to-end generate → upload → schedule
- [ ] **CDP Browser Manager** - Auto-launch with user profile

## Priority 4: TTS Providers
- [ ] **Inworld** - Already working
- [ ] **OpenAI TTS** - Add support
- [ ] **ElevenLabs** - Add support

## Priority 5: Polish
- [ ] **Subtitles** - Auto-generate SRT/VTT
- [ ] **Better Slides** - Multiple templates
- [ ] **Background Music** - Royalty-free ambient

---

## What NOT to build (Wizard Anti-pattern)
❌ Interactive setup wizard with questions
❌ User entering values manually
❌ User navigating provider consoles
❌ User copying secrets between apps

## What TO build (Zero-Wizard)
✅ User gives consent once (OAuth/API key)
✅ System handles ALL setup
✅ User just talks: "make a video about X"
✅ Video appears on YouTube
