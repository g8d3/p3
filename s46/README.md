# s46 — Autonomous Content System

AI agent infrastructure that generates content, narrates it via TTS, reviews
it with multiple AI models, publishes to social media, and fixes its own tools
— all on a schedule.

**Size:** 47MB (17 scripts, 8 crontab jobs, 3 posts, 3 audio narrations)

---

## System Architecture

```
s46/
├── README.md                         ← This file
├── ROADMAP.md                        ← Content production schedule
├── SECURITY.md                       ← Security audit & recommendations
│
├── knowledge-base/                   ← The AI's reference library
│   ├── PROJECT-INDEX.md              ← All 60+ projects indexed
│   ├── CONTENT-SOURCES.md            ← Content ideas & seeds
│   ├── TOOLS.md                      ← Tool inventory + research
│   └── AUTONOMY.md                   ← How opencode run works
│   └── runs/                         ← Saved agent run logs
│
├── content/                          ← Generated output
│   ├── posts/                        ← Written posts (.txt, 3 so far)
│   ├── audio/                        ← TTS narrations (.mp3, ~20MB)
│   └── reviews/                      ← Editor reviews & council reports
│
├── scheduler/                        ← The autonomy engine
│   ├── run-task.sh                   ← Cron-compatible task runner
│   ├── run-one.sh                    ← Single-agent runner (nohup-safe)
│   ├── parallel-launch.sh            ← Burst mode (2-3 parallel agents)
│   ├── overseer.sh                   ← Resource + content monitoring
│   ├── logs/                         ← All execution logs
│   └── tasks/                        ← 7 task scripts
│       ├── 01-project-spotlight      ← Random project deep-dive
│       ├── 02-browser-bookmarks      ← CDP browser exploration
│       ├── 03-system-story           ← System metacontent
│       ├── 04-research-burst         ← Tool comparison research
│       ├── 05-overseer-report        ← System status report
│       ├── 06-fixer-agent            ← Tool improvement scan
│       └── 07-editor-review          ← Content quality review
│
└── system/                           ← Quality-of-life agents
    ├── tts-safe.sh                   ← TTS wrapper (Python, handles JSON escaping)
    ├── event-monitor.sh              ← Threshold-triggered resource watchdog
    ├── fixer-agent.sh                ← Scans logs, fixes tool bugs automatically
    ├── editor-agent.sh               ← Content review (Gemini council, 2 models)
    ├── _gemini_call.py               ← Python helper for safe Gemini API calls
    └── dashboard/                    ← Live HTML dashboard
        ├── index.html                ← Auto-refreshing dashboard
        ├── current-state.json        ← Live system state data
        └── generate-dashboard.sh     ← Updates state, serves dashboard
```

---

## How It Works

### Content Creation Pipeline
```
1. Cron (or manual) picks a task script
2. Task script sets TASK_PROMPT with specific mission
3. opencode run executes the prompt autonomously
4. Agent explores, writes, generates TTS audio
5. Output saved to content/posts/ and content/audio/
6. Editor agent reviews quality (Gemini 3 flash → 2.5 flash)
7. Fixer agent scans logs for tool issues, applies fixes
8. [Future] Browser posts approved content to x.com
```

### The Agents

| Agent | Triggers | What It Does |
|-------|----------|-------------|
| **Content Creator** | Every 4h cron | `opencode run` with task prompt, generates post + TTS |
| **Parallel Burst** | Weekly Sunday | Spawns 2-3 creators at once with `nice -n 19` |
| **Overseer** | Every hour | Checks CPU/memory/disk, detects content overlap |
| **Event Monitor** | @reboot daemon | Silent threshold watcher — only logs when resources are critical |
| **Fixer** | Daily 3am | Scans logs for known error patterns, auto-applies fixes |
| **Editor** | Daily 6am | Reviews content via Gemini council (fast + deep models) |
| **Dashboard** | Every 15min | Generates `current-state.json` for the HTML dashboard |

### Review Process
```
Post written → Editor (gemini-3-flash-preview) → scores 1-5 on 6 criteria
                                                  ↓
                                            score >= 20/30?
                                           /                \
                                        YES                 NO
                                         ↓                   ↓
                                   APPROVED            Send to deep model
                                    + .approved        (gemini-2.5-flash)
                                                         ↓
                                                   score >= 20/30?
                                                  /                \
                                               YES                 NO
                                                ↓                   ↓
                                          APPROVED              REVISE/REJECT
                                    (council consensus)     (log feedback)
```

---

## Current Content (All Approved)

| Post | Words | Audio | Editor Score | Model |
|------|-------|-------|-------------|-------|
| Content Agent spotlight | 545 | 17MB af_nicole | 29/30 | gemini-2.5-flash (old) |
| System story | ~400 | 1.2MB am_michael | 27/30 | gemini-3-flash-preview |
| Research comparison | ~350 | 1.7MB af_nicole | 25+28/30 | council (2 models) |

---

## Live Crontab

```
Every 4h      → Content generation
Every hour    → Overseer resource check
Every 15min   → Dashboard data refresh
Daily 3am     → Fixer agent (tool bug detection)
Daily 6am     → Editor agent (content review)
Daily 8am     → Full overseer report
@reboot       → Event monitor daemon
Sunday 10am   → Parallel burst (3 agents)
```

---

## Quick Start

```bash
# Watch the dashboard
./system/dashboard/generate-dashboard.sh --serve
# → Open http://localhost:9090/system/dashboard/

# Run a content task
./scheduler/run-task.sh --once 01-project-spotlight.sh

# List available tasks
./scheduler/run-task.sh --list

# Review latest content
./system/editor-agent.sh

# Council review (2 models)
./system/editor-agent.sh --council --all

# Check system resources
./system/event-monitor.sh --status

# Scan and fix tool issues
./system/fixer-agent.sh

# Launch parallel agents
./scheduler/parallel-launch.sh 2

# Speak text safely (handles special characters)
echo "Text with 'quotes' and -- dashes" | ./system/tts-safe.sh --voice af_nicole --output output.mp3
```

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **No image gen yet** | Text + audio is the starting point. Images add ~$5-10/mo (Luma Photon or SiliconFlow) |
| **No scheduled posting** | Content accumulates on disk until human review pipeline is trusted |
| **Multi-model review** | Gemini 3 flash (fast) + 2.5 flash (deep) provide independent scores |
| **File-based API calls** | Avoids bash variable mangling of JSON responses |
| **TMPDIR = local tmp/** | Prevents `/tmp/` permission prompts during autonomous runs |
| **nice -n 19** | Content agents yield to user processes, never crash the PC |
| **Event-based monitoring** | Silent when healthy, noisy only when thresholds are exceeded |

---

## Security

See `SECURITY.md`. API keys are stored in `~/.local/share/opencode/auth.json`
(chmod 600) and environment variables. No keys are hardcoded in any config
files. Three `.env` files with exposed keys have been deleted.

---

## Roadmap

See `ROADMAP.md` for the full production schedule:

- **Short term (now)**: Text + audio, 1 post/day
- **Mid term (week 1-2)**: + AI images, x.com posting
- **Long term (week 2-4)**: + Video pipeline via s44, multi-platform
