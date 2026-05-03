# 🔥 HTMX in 100 Seconds

> **Format:** Fireship-style rapid-fire explainer
> **Total runtime:** ~100 seconds
> **Tone:** Dry humor, code-dense, zero fluff

---

## TIMESTAMPS & BEATS

### [0:00–0:04] HOOK — The Problem

**VISUAL:** VS Code with a React component tree 12 levels deep. Camera zooms out to reveal node_modules: 1.2GB.

**TEXT OVERLAY:**
```
React app: 1.2GB
To render: a todo list
```

**NARRATION (deadpan):**
> "You installed 1,200 megabytes of node_modules to render a form. HTMX looked at your package.json and said: 'No.'"

---

### [0:04–0:12] WHAT IS HTMX

**VISUAL:** HTMX logo → simple diagram: HTML attributes → HTTP requests → DOM updates. No build step. No virtual DOM. No framework.

**TEXT OVERLAY:**
```
HTMX = HTML attributes that make HTTP requests
       That's it. That's the library.
       14KB. Gzipped.
```

**NARRATION:**
> "HTMX is a library that extends HTML with attributes for making HTTP requests. It's 14 kilobytes. Gzipped. Your React app's node_modules just felt personally attacked."

---

### [0:12–0:22] THE CORE IDEA — Code Block #1

**VISUAL:** Two code blocks side by side. Left: React. Right: HTMX. Both do the same thing — load content on click.

**React way:**
```jsx
const [data, setData] = useState(null);

useEffect(() => {
  fetch("/api/items")
    .then(res => res.json())
    .then(setData);
}, []);

return <button onClick={loadMore}>Load</button>;
```

**HTMX way:**
```html
<button hx-get="/api/items" hx-target="#list" hx-swap="innerHTML">
  Load
</button>
```

**TEXT OVERLAY (mid-screen):**
```
15 lines vs 1 line
Same result. No JavaScript.
```

**NARRATION:**
> "Same feature. Fifteen lines of React, or one line of HTML. hx-get makes the request. hx-target says where to put the response. hx-swap says how. Your server returns HTML, not JSON. The browser does the rest. No useState. No useEffect. No useRef, useMemo, useCallback, or whatever hook drops next Tuesday."

---

### [0:22–0:38] SERVER-SIDE RENDERING — Code Block #2

**VISUAL:** Terminal + Express server code. Show the server returning HTML fragments.

```js
// server.js — Express + HTMX
app.get("/api/items", (req, res) => {
  const items = db.getItems();

  // Return HTML, not JSON
  res.send(`
    <ul>
      ${items.map(i => `<li>${i.name}</li>`).join("")}
    </ul>
  `);
});
```

```html
<!-- Frontend -->
<div id="list">
  <!-- Server content gets injected here -->
</div>
<button hx-get="/api/items" hx-target="#list" hx-swap="innerHTML">
  Load Items
</button>
```

**TEXT OVERLAY:**
```
Server returns HTML fragments.
Browser swaps them in. No client-side rendering.
```

**NARRATION:**
> "Your server returns HTML fragments. HTMX swaps them into the DOM. That's the whole architecture. You can use Python, Go, Rust, PHP — whatever. The server does the thinking. The browser does the displaying. Like the web was designed to work. Revolutionary concept, apparently."

---

### [0:38–0:50] TRIGGERS & SWAPS — Code Block #3

**VISUAL:** Code examples flying in, each with a one-liner explanation.

```html
<!-- Trigger on keyup, wait 500ms -->
<input hx-get="/search" hx-trigger="keyup delay:500ms" hx-target="#results">

<!-- Poll every 2 seconds -->
<div hx-get="/status" hx-trigger="every 2s">Loading...</div>

<!-- Confirm before delete -->
<button hx-delete="/api/items/1" hx-confirm="You sure?">Delete</button>

<!-- Swap after settle -->
<div hx-get="/data" hx-swap="outerHTML settle:500ms">...</div>
```

**TEXT OVERLAY:**
```
Declarative interactivity
No event listeners. No state management.
```

**NARRATION:**
> "htmx-trigger lets you fire requests on any DOM event — keyup, click, custom events, even polling. htmx-confirm adds a confirmation dialog. You're writing HTML, but it's doing JavaScript things. It's like giving HTML steroids and a gym membership."

---

### [0:50–1:02] THE ANTI-FRAMEWORK ARGUMENT

**VISUAL:** Meme format — the bell curve meme. Left (simple): "Just use jQuery." Middle (complex): "React + Next + Zustand + React Query + Framer Motion." Right (enlightened): "Just use HTMX."

**TEXT OVERLAY:**
```
Most web apps: forms, tables, buttons
HTMX: perfect for 80% of them
The other 20%: use whatever you want
```

**NARRATION:**
> "Here's the thing nobody wants to admit: most web apps are forms that talk to a server. You don't need a virtual DOM for a dashboard. You don't need Redux for a CRUD app. HTMX handles 80% of web development with zero build step, zero bundler, and zero existential dread about which state management library to pick this quarter."

---

### [1:02–1:15] THE TRADEOFFS — Honest Segment

**VISUAL:** Text on dark background, no frills.

**TEXT OVERLAY (typed out, line by line):**
```
❌ Not for highly interactive UIs (games, editors)
❌ Server round-trips on every interaction
❌ HTML responses ≠ JSON APIs (team must agree)
✅ No build step. No bundle. No node_modules.
✅ Works with any backend language
✅ 14KB. That's it. Go home.
```

**NARRATION:**
> "Honesty hour. HTMX isn't building Google Docs. If you need real-time canvas rendering or a collaborative editor — use a framework. Every interaction is a server round-trip, so latency matters. And your team has to buy into the HTML-response paradigm. But for dashboards, admin panels, and most CRUD apps? You'll ship faster and your bundle will be smaller than your favicon."

---

### [1:15–1:28] THE ECOSYSTEM & ADOPTION

**VISUAL:** Quick logos flying in — each with a one-liner.

**TEXT OVERLAY:**
```
✅ Django + HTMX: the "boring tech" stack
✅ Laravel + HTMX: PHP devs eating good
✅ Go + HTMX: fast backend, fast frontend
✅ 36k GitHub stars. Growing faster than React did.
```

**NARRATION:**
> "HTMX is blowing up in the Django and Laravel communities — turns out server-rendered developers were just waiting for HTML to get better. Go developers love it because Go servers return HTML faster than most JS frameworks can hydrate. Thirty-six thousand GitHub stars. The movement is real."

---

### [1:28–1:37] WHO SHOULD USE THIS

**VISUAL:** Quick icons flying in — each with a one-liner.

**TEXT OVERLAY:**
```
✅ You: building dashboards, admin panels, CRUD apps
✅ You: want to ship fast without a build pipeline
✅ You: think "just use jQuery" but want something modern

❌ Not you: building a collaborative Figma clone
❌ Not you: allergic to server-side code
```

**NARRATION:**
> "If you build internal tools, SaaS dashboards, or anything with a database and some buttons — HTMX is ridiculously productive. If you're building the next Figma... maybe bring a bigger framework. But if your app is 80% forms and tables, ask yourself: do you really need a 200-kilobyte client-side router?"

---

### [1:37–1:40] OUTRO CTA

**VISUAL:** Fireship-style subscribe animation.

**TEXT OVERLAY:**
```
🔥 htmx.org
⭐ Star the repo
👊 Like & subscribe
```

**NARRATION:**
> "Link in the description. Star the repo. Like and subscribe. Or don't. I'm a script, not a cop."

---

## PRODUCTION NOTES

### Visual Style
- **Font:** JetBrains Mono for code, Inter for overlays
- **Colors:** Dark bg (#0a0a0a), accent blue (#1E90FF → #4FC3F7 gradient), code syntax: One Dark Pro
- **Transitions:** Hard cuts, no dissolves. Zoom-ins on key code lines.
- **Code blocks:** Typing animation, ~40 chars/sec, syntax highlighted
- **HTMX branding:** Use HTMX's blue (#1E90FF) as accent where relevant

### Audio
- **Music:** Lo-fi synth, low volume, subtle — think Fireship's background tracks
- **SFX:** Subtle "whoosh" on transitions, "click" on code highlights, "ding" on comparisons
- **Voice:** Fast but clear. Dry delivery. No hype voice. Let the code speak.

### Text Overlay Rules
- Max 2 lines visible at once
- Appear synced with narration
- Key numbers/statistics: **bold + larger font**
- Code snippets: monospace, syntax-highlighted, ~60% screen width
- Comparisons: animate side-by-side, highlight the winner

### Pacing Checklist
- [ ] No segment exceeds 15 seconds
- [ ] At least one code block every 12 seconds
- [ ] Every claim backed by a number or visual proof
- [ ] One honest "here's the catch" moment
- [ ] Ends with a punchline, not a plea

---

## SCRIPT STATS

| Metric | Value |
|---|---|
| Word count | ~540 |
| Estimated read time | ~98 sec |
| Code blocks | 5 |
| Text overlays | 15 |
| Jokes | 5 |
| Times React dunked on | 4 |
