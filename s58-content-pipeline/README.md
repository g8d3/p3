# Weekly Content Pipeline

Replicates the Liu Wei approach: **1 topic → OpenCode Go → TTS → 1 long video → 12 shorts → YouTube/TikTok/Instagram** in ~138 lines of Python.

## How it works

```
topic ──→ OpenCode Go (OpenAI API) ──→ script ──→ edge-tts ──→ audio
                                                         │
                                                   ffmpeg build_video() ──→ long video (9:16, captioned)
                                                                                   │
                                                                             split_shorts() → 12 shorts
                                                                                   │
                            ┌──────────────────────────────────────────────────────┼──────────────────────┐
                            ▼                                                      ▼                      ▼
                       YouTube API                                           TikTok (Playwright)    Instagram (Playwright)
```

## Setup

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Configure API key (already set in environment)
export OPENCODE_GO_API_KEY=sk-...   # or set in .env
export YT_CLIENT_SECRET=/path/to/client_secret.json  # optional, for YouTube upload
```

## Usage

```bash
# Full pipeline (generates script + video + 12 shorts)
python pipeline.py --topic "Your video topic here"

# Use a default topic
python pipeline.py

# Skip uploads (just generate video locally)
python pipeline.py --topic "topic" --skip-upload

# Custom number of shorts
python pipeline.py --shorts 8

# Use a different OpenCode Go model
export OPENCODE_GO_MODEL=glm-5
```

## Pipeline stages

| Stage | Component | Description |
|-------|-----------|-------------|
| 1/5 | `generate_script()` | OpenCode Go (OpenAI-compatible API) writes 5-8min script with INTRO/HOOK/BODY/OUTRO/CTA sections |
| 2/5 | `generate_tts()` | edge-tts (free, Microsoft neural voices) converts script to MP3 |
| 3/5 | `generate_srt()` | Estimates word timing, generates SRT subtitle file |
| 4/5 | `build_video()` | ffmpeg creates 9:16 vertical video with gradient bg + subtitles + narration |
| 5/5 | `split_shorts()` | Cuts long video into N equal segments |
| Upload | `upload_yt()` | Google YouTube API v3 (OAuth, resumable upload) |
| Upload | `upload_social()` | Playwright browser automation for TikTok & Instagram |

## Files

- `pipeline.py` — Main pipeline (~138 lines)
- `requirements.txt` — Python dependencies
- `.env.example` — API key configuration template

## Modelos disponibles (OpenCode Go)

| Modelo | ID |
|--------|-----|
| DeepSeek V4 Flash | `deepseek-v4-flash` |
| DeepSeek V4 Pro | `deepseek-v4-pro` |
| GLM-5 | `glm-5` |
| GLM-5.1 | `glm-5.1` |
| Kimi K2.5 | `kimi-k2.5` |
| Kimi K2.6 | `kimi-k2.6` |
| MiMo V2.5 | `mimo-v2.5` |
| Qwen3.6 Plus | `qwen3.6-plus` |
| MiniMax M2.7 | `minimax-m2.7` (Anthropic format)
