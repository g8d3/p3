# TikTok Vertical Video Editor (ffmpeg)

Pure bash + ffmpeg pipeline that creates a **9:16 vertical video** with TikTok-style editing.

## Features

| Feature | Details |
|---|---|
| **Hook (first 2s)** | Flash + zoom + shake + bold "WAIT FOR IT" text |
| **Fast cuts** | Random 2–3 second segments from source clips |
| **Zoom / Ken Burns** | Alternating zoom-in / zoom-out per segment |
| **Flash transitions** | Brightness pulse at every cut point |
| **Text overlays** | Hook text, mid-roll accent, end CTA |
| **Sound effects** | Bass drop at start, pop at cuts, whoosh at midpoint |
| **Vertical crop** | Auto-scales and pads to 1080×1920 |

## Quick Start

```bash
# With your own clips
chmod +x tiktok-edit.sh
./tiktok-edit.sh clip1.mp4 clip2.mp4 clip3.mp4 -o my_video.mp4

# Demo mode (generates test clips automatically)
./tiktok-edit.sh --demo -o demo_output.mp4
```

## Options

| Flag | Default | Description |
|---|---|---|
| `--demo` | — | Generate colour test clips, no inputs needed |
| `-o <file>` | `output_tiktok.mp4` | Output filename |
| `-d <seconds>` | `15` | Total video duration |

## Customization

Edit the config block at the top of `tiktok-edit.sh`:

```bash
WIDTH=1080            # video width
HEIGHT=1920           # video height (9:16)
CUT_MIN=2.0           # min segment length
CUT_MAX=3.0           # max segment length
ZOOM_FACTOR=1.15      # zoom amplitude (1.0 = none)
HOOK_TEXT="WAIT FOR IT"   # first overlay text
MID_TEXT="NO WAY"         # mid-roll text
CTA_TEXT="FOLLOW FOR MORE" # end CTA
```

## Custom Sound Effects

Drop your own files into `./sfx/`:

```
sfx/
├── bass.mp3      # plays at t=0 (hook)
├── pop.mp3       # plays at each cut point
└── whoosh.mp3    # plays at mid-roll
```

If missing, the script generates placeholder tones.

## Requirements

- `ffmpeg` >= 5.0
- `ffprobe`
- `bc`
- A TrueType font at `/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`
  (or change the `fontfile=` path in the script)
