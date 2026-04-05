# Post to X

Automated scripts to post tweets and threads on X (Twitter) using Puppeteer with Chrome DevTools Protocol (CDP).

## Prerequisites

- Chrome/Chromium running with remote debugging enabled:
  ```bash
  google-chrome --remote-debugging-port=9222
  ```
- Logged into X in that browser session

## Setup

```bash
npm install
```

## Scripts

| Script | Purpose |
|--------|---------|
| `post-x.js` | Single tweet with robust timing |
| `post-x-min.js` | Minimal single tweet (fastest) |
| `post-x-thread.js` | Threads with per-tweet media |

## Usage

### Single Tweet

```bash
# Dry run (screenshot, no posting)
node post-x.js "Hello from CDP!" --dry-run

# Actually post
node post-x.js "Hello from CDP!"

# Minimal version (faster)
node post-x-min.js "Hello!"           # dry run
node post-x-min.js "Hello!" --post    # actually post
```

### Thread with Per-Tweet Media

```bash
# Basic thread (text only)
node post-x-thread.js \
  --tweet "First tweet" \
  --tweet "Second tweet" \
  --tweet "Third tweet"

# Thread with media on specific tweets
node post-x-thread.js \
  --tweet "Check this out" --media screenshot.png \
  --tweet "Here's another angle" --media photo1.jpg photo2.jpg \
  --tweet "No media here, just text" \
  --tweet "Final thought" --media chart.png

# Multiple media on one tweet
node post-x-thread.js \
  --tweet "Photo dump" --media img1.png img2.jpg img3.webp

# Mix of everything
node post-x-thread.js \
  --tweet "Thread start" --media cover.png \
  --tweet "Point 1" \
  --tweet "Point 2" --media diagram.svg \
  --tweet "Point 3" \
  --tweet "Conclusion" --media summary.png

# Actually post the thread
node post-x-thread.js \
  --tweet "Hello" --media image.png \
  --tweet "World" \
  --post
```

### Flags

| Flag | Description |
|------|-------------|
| `--tweet "text"` | Start a new tweet with text |
| `--media file.ext` | Attach media to current tweet (multiple allowed) |
| `--post` | Actually post (default: dry run with screenshot) |
| `--reuse` | Reuse existing X.com tab (faster iteration) |
| `--dry-run` | Preview without posting (post-x.js only) |

### Supported Media

Images: `jpg`, `jpeg`, `png`, `gif`, `webp`
Videos: `mp4`, `mov`, `webm`

### Links

Just include URLs in tweet text — X auto-detects them:

```bash
node post-x-thread.js \
  --tweet "Read more: https://example.com" \
  --tweet "Also see: https://docs.example.com"
```

### Fast Iteration

Use `--reuse` during development to skip navigation:

```bash
# First run: opens new tab
node post-x-thread.js --tweet "Test" --media img.png

# Subsequent runs: reuses existing X.com tab (much faster)
node post-x-thread.js --tweet "Test 2" --reuse
```

## How It Works

The scripts connect to a running Chrome instance via CDP (`localhost:9222`), navigate to X, interact with the compose UI using `data-testid` selectors, and type/post using keyboard events.

- **No API keys needed** — uses your existing browser session
- **Bot-detection friendly** — uses real browser with natural typing delays
- **Dry-run by default** — safe to test repeatedly without posting
