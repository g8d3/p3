# Content Roadmap

> Production schedule for the autonomous content system.
> Short-term = now to 1 week. Mid-term = 1-2 weeks. Long-term = 2-4 weeks.

---

## Short Term (Now — Week 1)

**Format:** Text posts + TTS narration audio (no video)
**Frequency:** 1 piece/day via cron, bursts on weekends
**Review:** Editor agent (Gemini 3.1 flash-lite fast pass + 3.1 pro deep council on Sundays)

### Scheduled Content

| Day | Task | Topic | Format |
|-----|------|-------|--------|
| Mon | 01-project-spotlight | One p3 project deep-dive | Thread + audio |
| Tue | 03-system-story | The autonomy system itself | Thread + audio |
| Wed | 04-research-burst | Tool comparisons / pareto analysis | Thread + audio |
| Thu | 02-browser-bookmarks | x.com bookmark exploration | Post + audio |
| Fri | 01-project-spotlight | Another project | Thread + audio |
| Sat | 03-system-story | Security / infrastructure story | Thread + audio |
| Sun | **Burst (3 agents)** | Any 3 tasks, parallel | Multi-thread + audio |

### Release Criteria (for auto-post)
- [ ] Editor agent approves (score >= 20/30)
- [ ] Council review on Sundays for batch approval
- [ ] Human reviews at least 3 posts to calibrate editor scoring
- [ ] TTS file > 100KB (valid audio)
- [ ] Post has thread format (`1/` style)

### Pipeline State
```
Input: knowledge-base + browser research
  → Agent generates post (opencode run)
  → Saves to content/posts/
  → Generates TTS narration → content/audio/
  → Editor reviews → content/reviews/
  → Fixer checks logs for tool issues
  → [Future] Browser posts to x.com
```

---

## Mid Term (Week 1-2)

**Format additions:** Posts with AI-generated images + x.com posting
**Frequency:** 2-3 pieces/day (parallel agents)
**Review:** Council review (2 models) for all posts before posting

### New Capabilities Needed

| Capability | Current Status | Path |
|-----------|---------------|------|
| **AI images for posts** | ❌ Missing | Add Luma Photon API (pareto best at $0.016/img) or SiliconFlow ($0.0014/img) |
| **x.com auto-post** | ⚠️ s36 has browser posting scripts | Test s36 post-x.js with CDP browser |
| **Multi-model council** | ✅ Editor agent supports it | Run `--council --all` daily |
| **Image-to-post pipeline** | ❌ Missing | Task script that: writes post → generates image → saves both |

### Content Types
- **Project spotlight + hero image** — 1 image per post
- **Research comparison + chart image** — data visualization
- **System update + screenshot** — dashboard or log screenshots
- **Bookmark review + link preview** — browser-captured images

### Approval Flow
```
Content → Editor (fast) → passes? → Editor (deep) → passes? → APPROVED
                              ↓                           ↓
                          Revise                     Reject (log reason)
```

---

## Long Term (Week 2-4)

**Format additions:** Video content via s44 pipeline
**Frequency:** 1-2 videos/week + daily posts
**Review:** Multi-model council + human spot-check

### New Capabilities Needed

| Capability | Current Status | Path | Cost |
|-----------|---------------|------|------|
| **Screen recording** | ✅ In s44 pipeline | Adapt `pipeline/record.py` | $0 |
| **Music + SFX** | ✅ In s44 pipeline | ffmpeg-generated | $0 |
| **Full video assembly** | ✅ In s44 pipeline | `pipeline/assemble.py` | $0 |
| **Better TTS voice** | ❌ Missing | Inworld TTS or Alibaba Qwen3-TTS ($0-5/mo) | ~$5/mo |
| **Post to multi-platform** | ❌ Missing | Typefully ($12.50/mo) or n8n self-hosted ($0) | $0-12/mo |
| **Video→x.com posting** | ❌ Missing | s36 post-x.js + video upload | $0 |
| **YouTube posting** | ⚠️ youtube-uploader-mcp exists | Need to test and configure | $0 |

### Content Types
- **Full video review** — narrated screen demo of a project (5-10 min)
- **Tool comparison video** — side-by-side with screen recording
- **"How it works" explainer** — animated walkthrough
- **Weekly roundup** — summary of the week's content with TTS

### Milestone: Full Autonomy
```
No human needed for routine content:

1. Schedule picks topic
2. Agent researches + writes + generates assets
3. Editor reviews (council if borderline)
4. Fixer monitors for tool issues
5. Dashboard tracks everything
6. Posts to x.com automatically
7. Human reviews weekly batch, adjusts direction
```

---

## Current Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| TTS has JSON escaping issues | Some narrations fail | Fixed: tts-safe.sh now handles this |
| Chrome bookmarks not always accessible | Task 02 may fall back | Agent auto-falls back to knowledge-base |
| Disk at 89% | May hit capacity in 2-3 weeks | Clean up old audio/logs, move to external storage |
| No image gen capability | Text-only posts | Can add SiliconFlow ($0.0014/img) |
| No scheduled posting | Content sits on disk | Add Typefully or s36 browser posting |
| Editor model may be old | Review quality degrades | Update GEMINI_MODEL env var periodically |
| Parallel agents share CDP browser | Browser conflicts | Limit browser tasks to 1 at a time (done in parallel-launch.sh) |

---

## Success Metrics

| Metric | Current | Short-term Goal | Long-term Goal |
|--------|---------|----------------|----------------|
| Posts/week | 3 | 7 | 14+ |
| Audio files/week | 3 | 7 | 10+ |
| Videos/week | 0 | 0 | 2 |
| Approval rate | 100% (1/1) | >80% | >90% |
| Council agreement rate | N/A | >70% | >85% |
| OpenCode credits used/day | ~3-5 sessions | 6-10 | 15-20 |
