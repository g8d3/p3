# Content Sources & Ideas

> Central repository of all potential content sources, seeds, and ideas.
> This is the master list we draw from when generating content.

---

## Source Type A: Projects (p1/p2/p3)

**~60 subprojects** across 3 main directories. Each is a potential content piece:

### Content Angles per Project
1. **What it does** — explainer / showcase post
2. **How it was built** — devlog / build-in-public thread
3. **What went wrong** — postmortem / lessons learned
4. **Architecture deep-dive** — technical analysis
5. **Video demo** — narrated walkthrough (TTS + screenshots)

### Priority Projects to Cover First

#### p1 (older, foundational)
- `s1-fw` — Framework work
- `s2-web3-r` — Web3 research
- `s3-web3-w` — Web3 wallets
- `s4-trade` — Trading system
- `s5-coder` — AI coding experiments
- `s6-agents` — Multi-agent systems (has sub-projects: t1-reveng, t2-web-research)
- `s7-audir` — Audio/directory tool

#### p2 (smaller, single project)
- `s1` — Contains sub-projects (t4-use-loris etc.)

#### p3 (largest, most recent — 48 subprojects)
- `s1` — Has t1/t2/t3 sub-projects
- `s6` — Contains `cdp-master-playground` (browser automation!)
- `s7` — Appwrite experiments
- `s11` — Backend project
- `s18` — (has .env.example)
- `s31` — (has .env)
- `s32` — (has .env with OpenAI key)
- `s35` — `content_automation` (relevant!)
- `s45` — `OpenMontage` (media montage tool)
- `s46` — Current project (autonomy/content system)

---

## Source Type B: Browser Context

### B1. X.com Bookmarks (Browser)
- Curated bookmarks on x.com (saved via Chrome CDP browser session)
- Each bookmark is a content seed — read, synthesize, post about it
- Categories likely include: AI tools, dev resources, research papers
- You also have bookmarks.json files in some projects (e.g., s20 has one)

### B2. Gemini Conversations
- Multiple conversations on topics of interest
- Can extract: what questions were asked, what answers were found
- Content format: "Here's what Gemini and I discussed about X"
- Cross-reference with projects to show real application

### B3. Other Logged-In Accounts
- Chrome on CDP port 9222 has multiple accounts
- Potential sources: YouTube history, X.com feed, LinkedIn, GitHub

---

## Source Type C: The System Itself (Metacontent)

The most meta-content source is **the system we're building right now**.

### Content Ideas
1. **"I taught an AI to run itself on a schedule"** — documenting the opencode run setup
2. **"My AI agent setup: Chrome CDP + TTS + OpenCode Go"** — the full stack
3. **"Why I split my monorepo into p1/p2/p3"** — repo organization story
4. **"Security audit of my own AI workspace"** — the SECURITY.md story
5. **"Giving an AI a prepaid debit card — what happened"** — future content
6. **"How to make an AI content creator from scratch"** — tutorial series
7. **"DeepSeek v4 Flash vs other models: real usage stats"** — from opencode stats

---

## Source Type D: External Research

### D1. TTS + Audio
- Create narrated versions of technical content
- Short audio clips for X.com / podcast snippets
- Full narrated walkthroughs of projects

### D2. Web Research via Browser
- Read technical articles → synthesize opinion → post
- Compare approaches across sources
- Curate "best of" lists from bookmarks/research

### D3. API-Leveraged Content
- Use Gemini API + OpenAI API to generate content
- Compare outputs from different models
- "I asked 3 AIs the same question" type posts

---

## Content Format Playbook

| Format | Tools Needed | Platform | Effort |
|--------|-------------|----------|--------|
| X.com thread (text) | Browser (logged in) | X.com | Low |
| X.com thread + audio | Browser + TTS | X.com + podcast | Medium |
| Blog post | write tool | Any | Low |
| Narration (podcast) | TTS | Audio hosting | Medium |
| Short video | TTS + screenshots + ffmpeg | X.com / YT Shorts | High |
| Full video | Needs Runway/Pika | YouTube | Very High |
| Code tutorial | write tool | GitHub/X.com | Medium |
| Security advisory | write tool | Blog/X.com | Low |

---

## Content Queue (to be prioritized)

- [ ] Project index: "Map of 60 AI experiments" — thread + audio
- [ ] OpenCode autonomy: "How I made myself run on a schedule" — thread + code
- [ ] Security audit: "I found my own exposed API keys" — thread
- [ ] TTS demo: "AI-generated narration of an AI project" — audio post
- [ ] Browser research: "Exploring my x.com bookmarks with browser control" — thread
- [ ] Gemini conversation summary: "My AI chat history as content" — thread
