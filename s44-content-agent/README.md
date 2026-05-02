# Content Agent — Autonomous AI Content Creator

An LLM-driven pipeline that researches software, writes review scripts, records screen demos,
generates voiceover narration, and assembles polished videos with subtitles, sound effects,
and background music — all without video generation models.

**You (the LLM) are the creative director. The code is just your hands.**

---

## How It Works

```
TOPIC SELECTION → SCRIPT WRITING → SCREEN RECORDING → TTS VOICEOVER
                                                          ↓
SOCIAL POSTS ← POST PACKAGE ← SUBTITLES + SFX + MUSIC ← VIDEO ASSEMBLY
```

### Pipeline Stages

| Stage | What Happens | Tooling |
|---|---|---|
| **1. Topic** | Pick a tool/website to review (12+ built-in options) | `agent/script_gen.py` |
| **2. Script** | Generate review script with personality, hooks, humor | LLM-generated or template |
| **3. Record** | Capture screen interaction via Playwright | Testreel / raw Playwright |
| **4. Voiceover** | Generate narration audio from script | Kokoro TTS (Chutes API) or edge-tts |
| **5. Subtitles** | Create SRT captions from measured audio timing | `pipeline/captions.py` + ffprobe |
| **6. SFX** | Add impact sounds, whooshes, stings at key moments | `pipeline/sfx.py` — 11 pro-quality effects |
| **7. Music** | Background track with chord progression + percussion | `pipeline/music.py` — 5 structured tracks |
| **8. Assemble** | Combine all assets into final MP4 via ffmpeg | `pipeline/assemble.py` |
| **9. Post** | Generate platform-specific post text | Twitter, LinkedIn, TikTok, YouTube, Mastodon |

---

## Quick Start

```bash
# Setup
uv venv .venv && source .venv/bin/activate
uv pip install edge-tts moviepy Pillow pyyaml mutagen
npm install testreel playwright && npx playwright install chromium
export CHUTES_API_TOKEN="your_token"

# Generate assets
python pipeline/sfx.py          # 11 pro sound effects
python pipeline/music.py all    # 5 background music tracks

# Test
python run.py --dry-run         # Preview without executing
python run.py --no-record       # Full run with placeholder video
python run.py                   # Full run with screen recording

# Schedule autonomous runs (3x daily)
python agent/scheduler.py set-multi
```

---

## Project Structure

```
s44/
├── run.py                      # Main pipeline orchestrator
├── precise_assemble.py         # Timing-exact video assembly
├── setup.sh                    # One-command setup
├── agent/
│   ├── personality.py          # Viral personality profile + refinement loop
│   ├── script_gen.py           # Topic picker + script templates (12+ topics)
│   ├── scheduler.py            # Cron management (3x: 9am, 3pm, 9pm)
│   └── social.py               # Post text generation (5 platforms)
├── pipeline/
│   ├── tts.py                  # Voiceover (Kokoro API + edge-tts fallback)
│   ├── record.py               # Screen recording (Testreel + Playwright)
│   ├── captions.py             # SRT subtitle generation with timing
│   ├── assemble.py             # ffmpeg video assembly + SFX + memes
│   ├── sfx.py                  # 11 pro-quality synthesized SFX
│   └── music.py                # Chord-progression background music generator
├── config/
│   └── personality.yaml        # Tone, humor, viral tactics (LLM-refined)
├── assets/
│   ├── sfx/                    # 11 generated sound effects
│   └── music/                  # 5 generated background tracks
├── output/                     # Generated videos + post packages
└── tmp/                        # Working directory (no /tmp permission issues)
```

---

## Asset Libraries

### Sound Effects (11 pro-quality)
Generated via ffmpeg with noise shaping, bandpass sweeps, and envelope control:

| SFX | Type | Use Case |
|---|---|---|
| `impact.wav` | Sub boom + noise burst | Section transitions, emphasis |
| `whoosh.wav` | Pink noise sweep | Scene changes |
| `swoosh.wav` | Softer whoosh | Gentle transitions |
| `riser.wav` | Pitch sweep + noise | Tension building, reveals |
| `stinger.wav` | Quick rise + thump | Punctuating jokes |
| `boing.wav` | Cartoon spring | Funny moments |
| `laugh.wav` | Synthesized chuckle | After punchlines |
| `click.wav` | UI click | Interaction highlights |
| `type_key.wav` | Keyboard click | Code mentions |
| `drum_roll.wav` | Snare drum | Before big reveals |
| `applause.wav` | Crowd applause | Outro, big moments |

### Background Music (5 structured tracks)
Real chord progressions with bass lines and percussion:

| Track | BPM | Duration | Progression | Mood |
|---|---|---|---|---|
| `bgm_chill_60s` | 95 | 60s | Cmaj→Am7→Fmaj→G7 | Lo-fi chill |
| `bgm_pop_90s` | 100 | 90s | Cmaj→Gmaj→Am7→Fmaj7 | Upbeat pop |
| `bgm_energetic_120s` | 105 | 120s | Am7→Fmaj→Cmaj→G7 | High energy |
| `bgm_mellow_90s` | 90 | 90s | Cmaj→Fmaj→Am7→G7 | Mellow |
| `bgm_driving_60s` | 110 | 60s | Dmin→Am7→G7→Cmaj | Driving rhythm |

---

## Key Decisions

| Choice | Why |
|---|---|
| **No video generation models** | LLMs are cheaper and more controllable. Screen recording captures real software interaction. |
| **Kokoro TTS primary, edge-tts fallback** | Kokoro is more expressive; edge-tts is free and needs no API key. |
| **ffmpeg for assembly** | Faster and more capable than MoviePy for complex filter graphs. |
| **ffmpeg-synthesized SFX/music** | No licensing issues, no downloads, deterministic generation, 100% free. |
| **Local tmp/ instead of /tmp/** | Avoids permission prompts on systems with restricted /tmp. |
| **YAML personality profile** | Human-readable, version-controllable, can be updated by LLM or refinement loop. |

---

## Comparison Files

| File | Content |
|---|---|
| `oss_content_creation_pipeline_tools.csv` | 6 full-pipeline content tools compared |
| `oss_screen_recording_capture_tools.csv` | 4 screen recording tools compared |
| `oss_content_creation_master_table.csv` | Combined 10-tool master table |
| `FEEDBACK_VIDEO_001.md` | Scorecard + critical issues for first video |
| `TRENDING_ASSETS_GUIDE.md` | Asset sourcing comparison (stock footage, music, SFX, memes) |
| `TEXT_TO_IMAGE_MODELS.md` | Best-value text-to-image model comparison (Pareto analysis) |

---

## Dependencies

- **Python 3.10+**: edge-tts, moviepy, Pillow, pyyaml, mutagen
- **Node 18+**: testreel, playwright
- **System**: ffmpeg, ffprobe, curl
- **Optional**: `CHUTES_API_TOKEN` for Kokoro TTS (falls back to edge-tts)

---

## License

MIT — Do whatever you want with the code.
The generated content (videos, scripts, posts) is yours.
