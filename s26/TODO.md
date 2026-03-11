# TODO - Autonomous Video Generator

## Priority 1: Core Functionality
- [ ] **YouTube Upload** - Already fixed (OAuth client secret re-downloaded)
- [ ] **Test YouTube Upload** - Verify it works with new credentials

## Priority 2: Video/Audio Quality
- [ ] **More TTS Providers** - Add OpenAI TTS, ElevenLabs support
- [ ] **Subtitles Generation** - Auto-generate SRT/VTT from audio
- [ ] **Better Slide Templates** - Multiple visual styles, backgrounds

## Priority 3: Natural Language Config
- [ ] **Chat-based Configuration** - Users describe video in natural language
- [ ] **Auto-script Generation** - LLM generates script from topic
- [ ] **Dynamic Slide Generation** - AI generates matching slides

## Priority 4: Heavy Lifting in Code
- [ ] **Profiling** - Optimize code to minimize LLM calls
- [ ] **Config-driven Defaults** - Smart defaults reduce LLM interaction
- [ ] **Template System** - Pre-built templates for common video types

## Priority 5: Automation
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

## Notes

**Philosophy:** Code does the heavy lifting. LLM is used only for:
- Script generation (when needed)
- Creative decisions (slide style, tone)
- Not for technical orchestration

**Configuration:** YAML for production, natural language for quick edits
