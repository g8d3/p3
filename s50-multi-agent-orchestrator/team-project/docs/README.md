# Team Project — Parallel AI Agent Orchestration

A multi-agent system that launches **5 specialized AI agents in parallel** to build a complete Todo List web application, plus a **video production pipeline** with its own set of agents. Each agent owns a single piece of the project (HTML, CSS, JS, tests, docs) and works concurrently from an orchestrator.

## Overview

This project demonstrates an **agent-team workflow**: a shell orchestrator spawns multiple `pi` CLI instances, each focused on one responsibility. A real-time dashboard (web + terminal) tracks progress via a shared timeline file.

The result is a fully functional **Todo List App** with:
- Semantic HTML5 with ARIA accessibility
- Modern dark-theme CSS with responsive design and CSS variables
- Vanilla JS with localStorage persistence and filters
- Browser-based unit test suite (25 tests)
- Full documentation (this file + changelog)

## How to Run

### Prerequisites

- [Node.js](https://nodejs.org/) (for the dashboard server)
- [pi CLI](https://github.com/mariozechner/pi-coding-agent) installed and on `PATH`
- Bash 4+

### Launch the Agent Team

```bash
# Start all 5 agents in parallel
./launch.sh start

# Check agent status
./launch.sh status

# Stop all agents
./launch.sh stop

# Stop a single agent
./launch.sh stop-one css
```

### Monitor Progress

```bash
# Real-time terminal timeline (updates every second)
./timeline.sh

# Interactive monitor with ability to interrupt agents
./monitor.sh
```

### Web Dashboard

```bash
cd dashboard
node server.js
# → Open http://localhost:3456
```

The dashboard shows live agent states, a scrolling timeline, and buttons to launch/stop both the app and video pipelines.

### Run the Todo App

After all agents complete, serve the app directory:

```bash
cd html
# Any static file server works:
python3 -m http.server 8080
# or
npx serve .
```

Then open `http://localhost:8080` in a browser.

### Run the Tests

Open `tests/test.html` directly in a browser, or serve it:

```bash
cd tests
npx serve .
# Open http://localhost:5000/test.html
```

## Project Structure

```
team-project/
├── launch.sh              # Orchestrator — launches/stops agents
├── monitor.sh             # Interactive terminal monitor
├── timeline.sh            # Real-time timeline viewer
├── orchestrator-log.sh    # Helper to log orchestrator events
├── .timeline              # Shared timeline data file
├── .pids/                 # PID files for running agents
│   ├── html.pid
│   ├── css.pid
│   ├── js.pid
│   ├── tests.pid
│   └── docs.pid
├── .logs/                 # Agent output logs
│   ├── html.log
│   ├── css.log
│   ├── js.log
│   ├── tests.log
│   └── docs.log
│
├── html/                  # 🟧 HTML Agent output
│   └── index.html         #   Semantic HTML5 with ARIA labels
├── css/                   # 🟦 CSS Agent output
│   └── style.css          #   Dark theme, responsive, CSS variables
├── js/                    # 🟨 JS Agent output
│   └── app.js             #   Todo CRUD, filters, localStorage
├── tests/                 # 🟪 Test Agent output
│   └── test.html          #   Browser-based unit test runner
├── docs/                  # 🟩 Docs Agent output
│   ├── README.md          #   This file
│   └── CHANGELOG.md       #   Version history
│
├── dashboard/             # Web dashboard
│   └── server.js          #   Node.js SSE server (port 3456)
│
└── video/                 # Video production pipeline (separate agents)
    ├── launch-video.sh
    ├── script-es/         #   Spanish scripts
    ├── script-en/         #   English scripts
    ├── audio-es/          #   Spanish audio clips (MP3)
    ├── audio-en/          #   English audio clips (MP3)
    ├── sfx/               #   Sound effects
    ├── style-tiktok/      #   TikTok editing style
    ├── style-fireship/    #   Fireship editing style
    ├── style-networkchuck/#   NetworkChuck editing style
    ├── composer/          #   Final video composition
    ├── recordings/        #   Screen recordings
    └── output/            #   Final rendered videos
```

## Features

### Todo List App
- **Add tasks** — type and submit to create a new todo
- **Complete tasks** — click checkbox to toggle done/undone
- **Delete tasks** — click the ✕ button to remove a task
- **Filter view** — switch between All / Active / Completed
- **Persistent storage** — todos survive page reloads via `localStorage`
- **Accessible** — semantic HTML5, ARIA roles and labels, keyboard navigable
- **Responsive** — works on mobile, tablet, and desktop

### CSS Design System
- Dark theme with 60+ CSS custom properties (colors, spacing, typography, shadows)
- Gradient accents (purple-to-cyan primary, card backgrounds, glow effects)
- Hover effects, smooth transitions, and animated skeletons
- Responsive breakpoints at 1024px (tablet) and 640px (mobile)
- `prefers-reduced-motion` media query support
- Custom scrollbar styling and utility classes

### Agent Orchestration
- **Parallel execution** — 5 agents run simultaneously via background processes
- **Color-coded timeline** — each agent has a distinct color and emoji
- **Real-time monitoring** — terminal timeline (`timeline.sh`) updates every second
- **Interactive control** — stop individual agents or all at once
- **Web dashboard** — SSE-powered live dashboard with agent cards and timeline
- **Logging** — per-agent log files in `.logs/`

### Video Pipeline
- Multi-language script generation (Spanish + English)
- Text-to-speech audio generation
- Multiple editing style templates (TikTok, Fireship, NetworkChuck)
- Sound effects library
- Automated video composition
- Screen recording integration
