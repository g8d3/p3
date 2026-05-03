# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] — 2026-05-03

Initial release — built by 5 parallel AI agents via the orchestration system.

### HTML — `html/index.html`

- Semantic HTML5 document with `<header>`, `<nav>`, `<main>`, `<footer>` landmarks.
- Add-todo form (`#add-todo-form`) with labeled text input and submit button.
- Todo list container (`#todo-list`) with `role="list"`.
- Navigation links for All / Active / Completed filters with `aria-current="page"`.
- ARIA attributes throughout: `aria-required`, `aria-label`, `role` landmarks.
- Footer with copyright notice.

### CSS — `css/style.css`

- Full design token system via CSS custom properties (colors, spacing, typography, radii, shadows, transitions).
- Deep dark theme with `#0f0f0f` primary background and purple-to-cyan gradient accents.
- Component styles: navbar, cards (hover lift with shadow), buttons (primary/ghost), forms (focus rings with accent glow), todo items with checkbox and delete button.
- Custom scrollbar styling (webkit).
- Keyframe animations: `fadeIn`, `slideUp`, `slideDown`, `pulse`, `spin`, `skeleton`.
- Responsive breakpoints at 1024px (tablet) and 640px (mobile) with grid collapse and full-width buttons.
- `prefers-reduced-motion` media query to disable all animations/transitions.
- Utility classes: `.sr-only`, `.container`, `.grid-*`, `.flex-*`, `.text-*`, `.mt-*`, `.mb-*`, `.animate-*`.

### JavaScript — `js/app.js`

- IIFE module pattern (no globals).
- Todo CRUD: `add(text)`, `toggle(id)`, `remove(id)`, `clearCompleted()`.
- Filtering with `filter` state variable (`all`, `active`, `completed`) via `setFilter()`.
- `localStorage` persistence under key `"todos"` with `save()` helper.
- Unique ID generation using `Date.now().toString()`.
- Dynamic DOM rendering via `render()` — rebuilds list on every state change.
- Event listeners on form submit (`#add-todo-form`), filter buttons (`[data-filter]`), and clear-completed (`#clear-completed`).

### Tests — `tests/test.html`

- Self-contained HTML file with built-in test runner (no external dependencies).
- Minimal DOM fixture replicating the elements `app.js` expects (`#todo-form`, `#todo-input`, `#todo-list`, `#todo-count`, `[data-filter]`, `#clear-completed`).
- Loads `../js/app.js` dynamically via script injection, then runs all tests.
- Test groups: **ADD**, **TOGGLE**, **DELETE**, **FILTER**, **LOCALSTORAGE**.
- Pass/fail summary with color-coded results.
- Document title updates to `ALL PASS` or `FAIL (n)` for quick visual check.

### Docs — `docs/`

- `README.md` — Overview, how to run, project structure, features.
- `CHANGELOG.md` — This file with per-module version history.

### Orchestration

- `launch.sh` — Start, stop, stop-one, and status commands for managing 5 parallel `pi` agents. Writes lifecycle events to `.timeline` with millisecond timestamps. Color-coded agent identifiers (🟧 html, 🟦 css, 🟨 js, 🟪 tests, 🟩 docs).
- `monitor.sh` — Interactive terminal dashboard showing per-agent status with log tailing; supports interrupting agents by name or stopping all via keyboard input.
- `timeline.sh` — Real-time timeline view with animated progress bars per agent, elapsed time tracking, and completion summary.
- `orchestrator-log.sh` — Helper script to append orchestrator events to the shared timeline.
- `dashboard/server.js` — Node.js HTTP server on port 3456 with SSE (Server-Sent Events) for live browser dashboard. Covers both the app and video pipelines. API endpoints: `/api/state`, `/api/start-app`, `/api/start-video`, `/api/stop`, `/api/stop/:name`.
- `.pids/` — PID files for tracking running agent processes.
- `.logs/` — Per-agent log files for output capture.

### Video Pipeline

- `video/launch-video.sh` — Orchestrator for video production agents.
- Spanish and English script generation (`script-es/`, `script-en/`).
- TTS audio generation in both languages (`audio-es/`, `audio-en/`).
- Multiple editing style templates: TikTok, Fireship, NetworkChuck (`style-*/`).
- Sound effects library with WAV/MP3 variants (`sfx/`).
- Automated video composition (`composer/`).
- Screen recording integration (`recordings/`).
- Final rendered outputs (`output/`).
