# Tools & Capabilities Inventory

> Everything we have available right now, and what each enables.

---

## Core AI

| Tool | Status | How to Use | Cost |
|------|--------|-----------|------|
| **OpenCode Go** (DeepSeek v4 Flash) | ✅ Active | `opencode run <message>` | Prepaid credits |
| **Gemini API** | ✅ Key set | `GEMINI_API_KEY` env var | Free tier / usage |
| **OpenAI API** | ✅ Key set | `OPENAI_API_KEY` env var | Usage-based |
| **OpenCode auth store** | ✅ 5 providers | `opencode auth list` | N/A |
| **Cerebras** | ✅ In auth store | Via opencode | Unknown |
| **Z.AI Coding Plan** | ✅ In auth store | Via opencode | Unknown |

### OpenCode Stats (lifetime)
- 289 sessions, 11,568 messages, 237 days
- Total cost: $29.68 ($0.13/day avg)
- 91M input tokens, 3.3M output tokens
- Most-used tools: bash (41%), edit (19%), read (14%)

---

## Browser & Web

| Tool | Status | How to Use |
|------|--------|-----------|
| **Chrome** (CDP port 9222) | ✅ Running | `ws://localhost:9222/devtools/browser/...` |
| **agent-browser** CLI | ✅ Installed | `agent-browser open/navigate/snapshot/click/fill` |
| **Playwright MCP** (CDP) | ⚠️ Disabled in opencode | Enable in `opencode.json` |
| **npx playwright MCP** | ✅ Available | `npx @playwright/mcp@latest --cdp-endpoint http://localhost:9222` |

### Logged-In Accounts (via Chrome CDP)
- Gemini (conversations accessible)
- X.com (bookmarks accessible)
- Multiple other accounts

### Capabilities
- Navigate any URL ✅
- Extract text/content ✅
- Fill forms, click buttons ✅
- Take screenshots ✅
- Save/load auth state ✅
- PDF export ✅
- Parallel sessions ✅
- Semantic locators (find by text, role, label) ✅

---

## Audio / Speech

| Tool | Status | How to Use |
|------|--------|-----------|
| **TTS (Chutes Kokoro)** | ✅ Active | `tts-speak "text" --output file.mp3` |
| **FFmpeg** | ✅ Installed | Audio conversion, processing |
| **Voices available** | 8 | af_heart, af_bella, af_nicole, am_adam, am_michael, bf_emma, bm_george |

### Capabilities
- Text-to-speech generation ✅
- Save to MP3/WAV ✅
- Voice selection (7 voices) ✅
- Speed control (0.5x-2.0x) ✅
- Pipe to ffmpeg for processing ✅
- Multi-segment narration ✅

### Limitations
- No long-form (>5 min) tested
- Single speaker only (no multi-voice dialog)
- No emotion/sentiment control beyond voice choice

---

## Video / Media

| Tool | Status | Notes |
|------|--------|-------|
| **FFmpeg** | ✅ | Can assemble audio + images into video |
| **TTS** | ✅ | Voiceover for videos |
| **Screenshots** | ✅ (via browser) | Can capture frames |
| **AI Video Gen** | ❌ Needs Runway/Pika/Kling | Requires payment |
| **Stock Media** | ❌ Needs Envato/Epidemic | Requires payment |
| **Music/SFX** | ❌ | Requires subscription |

### Current Video Capabilities
- Slideshow video (images + TTS narration) ✅
- Screen recording via browser? (needs testing) ⚠️
- Real AI video generation ❌

---

## Infrastructure

| Capability | Status | Notes |
|-----------|--------|-------|
| **Node.js** | v24.14.0 | Latest, can run any JS |
| **Python** | 3.12.3 | Can run scripts |
| **npm/npx** | ✅ | Package ecosystem |
| **Bash scripting** | ✅ | Full shell access |
| **Cron** | ✅ Available | `crontab -e` for scheduling |
| **Git** | ✅ | Version control |
| **Home internet** | ✅ | Assuming connectivity |

---

## What We're Missing — Research-Backed Alternatives

> Research conducted April 2026 across official pricing pages, docs, and
> community sources. Includes USA, EU, and China-based options.
>
> See also: `p3/s44/TEXT_TO_IMAGE_MODELS.md` for the original pareto frontier
> analysis of image models, and `p3/s44/TRENDING_ASSETS_GUIDE.md` for stock
> media comparisons.

### TTS / Voice

| Service | Price | Quality vs Free | Country |
|---------|-------|----------------|---------|
| **Edge-TTS** (current fallback) | **$0** | Good, 400+ voices | 🇺🇸 Microsoft |
| **Kokoro** (current) | **$0** (via Chutes) | Good, 8 voices | 🌍 OSS |
| **Alibaba Qwen3-TTS** | **$0** (1M chars/mo free) | Very good, 49 voices, 48kHz | 🇨🇳 China |
| **Inworld TTS** | $5-10/1M chars | Excellent, best Elo rating | 🇺🇸 USA |
| **Fish Audio** | $11-75/mo | Voice cloning, 2M+ voices | 🇺🇸 USA |
| **ElevenLabs** | $5-99/mo | Best quality, voice cloning | 🇺🇸 USA |

**Verdict:** Inworld TTS > ElevenLabs for cost. Alibaba Qwen3-TTS is free
for 1M chars/mo. Edge-TTS is already free and available. Kokoro via Chutes
is free and already integrated in s44 pipeline.

### Image Generation

| Service | Price/Image | Quality | Country |
|---------|------------|---------|---------|
| **Flux Schnell** (OSS) | **$0** (self-host) | 6/10 | 🇩🇪 Germany |
| **SiliconFlow** (FLUX Schnell) | **$0.0014** | 6/10 | 🇨🇳 China |
| **SiliconFlow** (Z-Image-Turbo) | **$0.005** | 7/10 | 🇨🇳 China |
| **Luma Photon Flash** | $0.004 (720p) | 7/10 | 🇺🇸 USA |
| **Luma Photon 1080p** ← Pareto | **$0.016** | **9/10** | 🇺🇸 USA |
| **FLUX.2 Pro** (SiliconFlow) | $0.03 | 9/10 | 🇨🇳 China |
| **Midjourney Basic** | $10/mo (unlimited relax) | 10/10 | 🇺🇸 USA |

**Verdict:** From s44's pareto analysis — **Luma Photon 1080p at $0.016/image
is the sweet spot** (90% of max quality for 10-20% of cost). For budget,
**SiliconFlow's $0.0014/image** for FLUX Schnell is unmatched.
**Midjourney Basic** ($10/mo) for unlimited generation if you want aesthetics.

### AI Video Generation

| Service | Price | Quality | Country |
|---------|-------|---------|---------|
| **Stable Video Diffusion** (OSS) | **$0** (needs GPU) | 5/10, short clips | 🌍 OSS |
| **Kling AI** | **$6.99/mo** (660 credits) | 8/10, 4K/60fps | 🇨🇳 China |
| **MiniMax/Hailuo** | $9.99/mo (1K credits) | 8/10, cinematic | 🇨🇳 China |
| **Runway Gen-4** | $12/mo (625 credits) | 9/10, best US-side | 🇺🇸 USA |
| **Pika** | $8-10/mo | 7/10 | 🇺🇸 USA |
| **Luma Dream Machine** | $9.99/mo (3.2K cr) | 8/10 | 🇺🇸 USA |
| **MiniMax Unlimited** | $94.99/mo | Unlimited gen | 🇨🇳 China |

**Verdict:** **Kling AI at $6.99/mo** is the best cost/benefit — China-based,
great quality, 4K, huge user base. For US-side, Runway $12/mo.

### Social Media Posting

| Service | Price | Capabilities | Country |
|---------|-------|-------------|---------|
| **Buffer Free** | **$0** | 3 channels, 10 posts/channel | 🇺🇸 USA |
| **Typefully Creator** | **$12.50/mo** | X + LinkedIn scheduling, AI writing | 🇺🇸 USA |
| **n8n self-hosted** | **$0** (+ Hetzner $3.79) | Unlimited automation, 400+ nodes | 🇩🇪 Germany |
| **X API Basic** | $200/mo | Direct API access | 🇺🇸 USA |
| **Hootsuite** | $99/mo | 20+ platforms | 🇨🇦 Canada |

**Verdict:** **Typefully at $12.50/mo** is vastly cheaper than X API ($200/mo)
and handles scheduling + AI writing. For full automation, **n8n self-hosted
on Hetzner** ($3.79/mo VPS) replaces Make.com and most social tools.

### Hosting & Infrastructure

| Service | Price | Use Case | Country |
|---------|-------|----------|---------|
| **Vercel Hobby** | **$0** | Frontend/static sites | 🇺🇸 USA |
| **Hetzner VPS** | **€3.79/mo** (2vCPU, 4GB) | Backend, bots, databases | 🇩🇪 Germany |
| **Railway** | $5-20/mo | Full-stack apps | 🇺🇸 USA |
| **Fly.io** | ~$2/mo (tiny) | Edge compute | 🇺🇸 USA |

**Verdict:** **Hetzner at €3.79/mo** is 10-12× cheaper than AWS for VPS.
Vercel Hobby is generous for frontends.

### GPU Compute

| Service | Price | Use Case | Country |
|---------|-------|----------|---------|
| **RunPod** | $0.39/hr (RTX 4090) | All-purpose GPU | 🇺🇸 USA |
| **SiliconFlow** | $0.0014/image | Image inference only | 🇨🇳 China |
| **Together AI** | $0.06-7/M tokens | LLM inference | 🇺🇸 USA |
| **Nebius** | $2.00/hr (H100 commit) | Training, free egress | 🇳🇱 Netherlands |

**Verdict:** **RunPod** for general GPU (RTX 4090 at $0.39/hr).
**SiliconFlow** for inference (cheapest globally for many models).

### Stock Media

| Service | Price | Assets | Country |
|---------|-------|--------|---------|
| **Pixabay** | **$0** | 4M+ photos, 2M+ videos, 220K+ music | 🇩🇪 Germany |
| **Epidemic Sound** | $9.99/mo | 55K tracks, 250K SFX | 🇸🇪 Sweden |
| **Envato Elements** | $16.50/mo | 27M assets (video, photo, audio, templates) | 🇦🇺 Australia |
| **Artlist** | $9.99/mo | 60K tracks, 180K video clips | 🇺🇸 USA |

**Verdict:** **Pixabay is free** and sufficient for most needs.
**Epidemic Sound ($9.99/mo)** for monetization-safe music.

---

### Minimum Viable Video Pipeline (Researched)

**Research process at s44** (see `s44/README.md` and `s44/TEXT_TO_IMAGE_MODELS.md`):

The s44 Content Agent already has a full pipeline that generates:
- Screen recordings (via Playwright/Testreel) — **$0**
- TTS narration (Kokoro via Chutes, with edge-tts fallback) — **$0**
- Sound effects (11 pro-quality, ffmpeg-synthesized) — **$0**
- Background music (5 tracks, algorithmic chord progressions) — **$0**
- Subtitles (SRT from ffprobe timing) — **$0**
- Video assembly (ffmpeg filter graphs) — **$0**

**s44 already has a $0 pipeline** that produces polished videos.
What external services add is variety and quality:

| Paid Addition | Cost | Improvement Over Free |
|--------------|------|---------------------|
| **Better TTS** (Inworld $5-10/1M chars) | ~$5/mo at low volume | More expressive, multi-voice |
| **AI Images** (Luma Photon $0.016/img) | ~$5-10/mo | Replace screenshots with generated visuals |
| **Stock music** (Pixabay free → Epidemic $10) | $10/mo | More track variety |
| **AI video clips** (Kling $6.99) | $7/mo | Real text-to-video b-roll |

**So for ~$15-25/mo total**, you can upgrade the free s44 pipeline to include:
- Inworld TTS narration ($5)
- Luma Photon images as visual b-roll ($5-10)
- Epidemic Sound background music ($10)
- Kling AI for short video clips ($7)

**For $0/mo**, s44 already produces: narrated screen recordings with SFX,
music, subtitles, and social posts. This is the starting point.

### Research Sources in This Workspace

Previous comparative research lives in these files — they should be indexed
and referenced for future content:

| File | Content |
|------|---------|
| `p3/s44/TEXT_TO_IMAGE_MODELS.md` | Pareto frontier: 12+ image models with cost/quality |
| `p3/s44/TRENDING_ASSETS_GUIDE.md` | Stock video, music, SFX, meme comparisons |
| `p3/s44/oss_content_creation_master_table.csv` | 10 full-pipeline content creation tools compared |
| `p3/s44/oss_content_creation_pipeline_tools.csv` | 7 pipeline tools |
| `p3/s44/oss_screen_recording_capture_tools.csv` | 5 screen recording tools |
| `p3/s26/README.md` | TTS provider comparison (Inworld, OpenAI, ElevenLabs) |
| `p3/s26/archive/PROJECT_METRICS.md` | Real cost tracking with TTS usage |
| `p3/s32/ai-services.csv` | 12 AI services with API endpoints, key patterns |
| `p3/s44/FEEDBACK_VIDEO_001.md` | Video quality scorecard |
| `p3/s44/CONTENT_AGENT_MASTER_PROMPT.md` | Full tool stack comparison |
