# Post to X

Automated scripts to post tweets and threads on X (Twitter) using Puppeteer with Chrome DevTools Protocol (CDP).

## Prerequisites

- Chrome/Chromium running with remote debugging enabled:
  ```
  google-chrome --remote-debugging-port=9222
  ```
- Logged into X in that browser session

## Setup

```bash
npm install
```

## Usage

### Post a single tweet

```bash
node post-x.js "Hello from CDP!"           # post
node post-x.js "Hello from CDP!" --dry-run  # preview with screenshot
```

### Minimal single tweet

```bash
node post-x-min.js "Hello!"           # dry run (screenshot)
node post-x-min.js "Hello!" --post    # actually post
```

### Post a thread

```bash
node post-x-thread.js "Tweet 1" "Tweet 2" "Tweet 3"           # dry run
node post-x-thread.js "Tweet 1" "Tweet 2" "Tweet 3" --post    # actually post
```

## How It Works

The scripts connect to a running Chrome instance via CDP (`localhost:9222`), navigate to X, interact with the compose UI using `data-testid` selectors, and type/post using keyboard events.
