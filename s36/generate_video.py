#!/usr/bin/env python3
"""
Generate frames for a 42-second viral TikTok-style video.
Split-screen format: top = animated visuals, bottom = terminal/code.
"""

import os
import math
import random
from PIL import Image, ImageDraw, ImageFont

# ─── Config ───────────────────────────────────────────────────────────────
WIDTH = 1080
HEIGHT = 1920  # 9:16 TikTok format
FPS = 30
TOTAL_DURATION = 42  # seconds
TOTAL_FRAMES = TOTAL_DURATION * FPS
HALF_H = HEIGHT // 2

OUT_DIR = "video_frames"
os.makedirs(OUT_DIR, exist_ok=True)

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
NEON_GREEN = (0, 255, 65)
NEON_BLUE = (0, 170, 255)
NEON_PINK = (255, 0, 128)
NEON_YELLOW = (255, 255, 0)
DARK_BG = (10, 10, 15)
TERMINAL_BG = (15, 15, 20)
TERMINAL_GREEN = (0, 220, 50)
ACCENT_ORANGE = (255, 140, 0)

# Scenes: (start_frame, end_frame, scene_name)
SCENES = [
    (0, 90, "hook"),           # 0-3s
    (90, 240, "cdp_fix"),      # 4-8s
    (240, 450, "simple_post"), # 9-15s
    (450, 720, "thread_build"),# 16-24s
    (720, 990, "media_upload"),# 25-33s
    (990, 1170, "montage"),    # 34-39s
    (1170, 1260, "outro"),     # 40-42s
]

# Subtitles per scene (word, start_frame_offset, end_frame_offset)
SUBTITLES = {
    "hook": [
        ("STOP", 0, 15),
        ("wasting time", 15, 45),
        ("writing MANUAL", 45, 75),
        ("automations!", 75, 90),
    ],
    "cdp_fix": [
        ("I used FREE AI", 0, 45),
        ("to build a", 45, 90),
        ("Twitter BEAST", 90, 150),
    ],
    "simple_post": [
        ("Step 1:", 0, 30),
        ("Simple posts?", 30, 90),
        ("INSTANT.", 90, 210),
    ],
    "thread_build": [
        ("But THREADS?", 0, 45),
        ("That's where CDP", 45, 120),
        ("logic gets BRUTAL", 120, 270),
    ],
    "media_upload": [
        ("Solved media uploads", 0, 90),
        ("with ZERO", 90, 150),
        ("paid API costs!", 150, 270),
    ],
    "montage": [
        ("OpenRouter + Zen", 0, 60),
        ("+ Chutes.", 60, 120),
        ("The agentic stack", 120, 180),
        ("is HERE.", 180, 270),
    ],
    "outro": [
        ("Follow the build.", 0, 45),
        ("We're just", 45, 60),
        ("getting STARTED.", 60, 90),
    ],
}

# Terminal text per scene
TERMINAL_TEXT = {
    "hook": [
        "$ opencode --context twitter-bot",
        "> Loading 47,293 tokens...",
        "> Analyzing session history...",
        "> Building automation pipeline...",
        "✓ Context loaded successfully",
        "✓ 12 tasks identified",
        "✓ Ready to execute",
    ],
    "cdp_fix": [
        "$ cd twitter-bot && opencode run",
        "> Attempting to connect via CDP...",
        "✗ Error: Selector '#tweet-btn' not found",
        "> Retrying with dynamic selector...",
        "> Found: button[data-testid='tweetButton']",
        "✓ CDP connection established",
        "✓ Selector resolved automatically",
    ],
    "simple_post": [
        "$ opencode run --task 'post tweet'",
        "> Generating content...",
        "> Opening browser via CDP...",
        "> Navigating to twitter.com/compose",
        "> Typing: 'AI automation is wild 🤖'",
        "> Clicking Post...",
        "✓ Tweet published successfully!",
        "✓ Engagement tracking enabled",
    ],
    "thread_build": [
        "$ opencode run --task 'create thread'",
        "> Analyzing thread structure...",
        "> Post 1/4: Hook generated ✓",
        "> Post 2/4: Value prop ✓",
        "> Post 3/4: Proof points ✓",
        "> Post 4/4: CTA ✓",
        "> Publishing thread sequentially...",
        "✓ Thread live! 4/4 posts published",
    ],
    "media_upload": [
        "$ opencode run --task 'thread with media'",
        "> Detecting media attachments...",
        "> Uploading image_01.png via CDP...",
        "> Handling multipart form data...",
        "> Bypassing API rate limits...",
        "> Attaching to thread post 2/4...",
        "✓ Media uploaded - ZERO API costs!",
        "✓ Thread with images published!",
    ],
    "montage": [
        "$ opencode status",
        "┌─────────────────────────────┐",
        "│  Tasks Completed: 47        │",
        "│  Success Rate: 98.2%        │",
        "│  API Cost: $0.00            │",
        "│  Models: Free tier only     │",
        "│  Stack: OpenRouter + Zen    │",
        "│         + Chutes.ai         │",
        "└─────────────────────────────┘",
    ],
    "outro": [
        "$ opencode --version",
        "OpenCode v2.1.0",
        "",
        "Follow: @novaisabuilder",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "The agentic stack is here.",
        "We're just getting started.",
    ],
}


def get_font(size=40):
    """Get a font, falling back to default if needed."""
    for font_path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf",
    ]:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
    return ImageFont.load_default()


FONT_BOLD = get_font(48)
FONT_BOLD_LARGE = get_font(64)
FONT_MONO = get_font(28)
FONT_MONO_SMALL = get_font(22)
FONT_SUBTITLE = get_font(56)
FONT_SUBTITLE_SMALL = get_font(42)
FONT_HANDLE = get_font(52)


def draw_matrix_rain(draw, frame_offset, alpha=180):
    """Draw matrix-style falling characters in a region."""
    chars = "01アイウエオカキクケコ{}[]<>/\\"
    col_width = 24
    num_cols = WIDTH // col_width
    random.seed(42 + frame_offset // 5)  # Deterministic per scene

    for col in range(num_cols):
        x = col * col_width
        # Multiple drops per column
        for drop in range(3):
            seed = col * 100 + drop + frame_offset // 8
            random.seed(seed)
            speed = random.randint(2, 6)
            y_start = (frame_offset * speed) % (HALF_H + 200) - 200

            for i in range(12):
                y = y_start - i * 22
                if 0 <= y < HALF_H:
                    char = random.choice(chars)
                    brightness = max(0, 255 - i * 22)
                    color = (0, min(255, brightness), max(0, brightness // 3))
                    draw.text((x + random.randint(-2, 2), y), char,
                              fill=color, font=FONT_MONO_SMALL)


def draw_glitch_effect(draw, frame_offset, region_top=0, region_bottom=None):
    """Draw horizontal glitch lines."""
    if region_bottom is None:
        region_bottom = HALF_H

    random.seed(frame_offset * 7)
    if random.random() < 0.3:  # 30% chance of glitch
        num_lines = random.randint(2, 8)
        for _ in range(num_lines):
            y = random.randint(region_top, region_bottom)
            height = random.randint(1, 4)
            offset = random.randint(-15, 15)
            color = random.choice([NEON_PINK, NEON_BLUE, NEON_GREEN, WHITE])
            # Draw displaced rectangle
            draw.rectangle([offset, y, WIDTH + offset, y + height], fill=color)


def draw_terminal(draw, lines, frame_offset, total_lines, y_offset=HALF_H + 40):
    """Draw terminal-style text with typing effect."""
    # Terminal background
    draw.rectangle([20, y_offset - 30, WIDTH - 20, HEIGHT - 20], fill=TERMINAL_BG)
    # Terminal border
    draw.rectangle([20, y_offset - 30, WIDTH - 20, HEIGHT - 20], outline=NEON_GREEN, width=2)

    # Terminal header
    draw.rectangle([20, y_offset - 30, WIDTH - 20, y_offset], fill=(30, 30, 35))
    draw.text((40, y_offset - 26), "● ● ●", fill=(255, 95, 86), font=FONT_MONO_SMALL)
    draw.text((WIDTH // 2 - 60, y_offset - 26), "opencode — twitter-bot",
              fill=(150, 150, 150), font=FONT_MONO_SMALL)

    # Calculate visible lines based on frame progress
    progress = min(1.0, frame_offset / max(1, total_lines * 8))
    visible_count = int(progress * len(lines))
    partial_chars = 0
    if visible_count < len(lines):
        partial_chars = int(((progress * len(lines)) - visible_count) * 30)

    current_y = y_offset + 10
    for i, line in enumerate(lines[:visible_count]):
        color = TERMINAL_GREEN
        if line.startswith("✗"):
            color = (255, 80, 80)
        elif line.startswith("✓"):
            color = NEON_GREEN
        elif line.startswith(">"):
            color = (180, 180, 200)
        elif line.startswith("$"):
            color = NEON_BLUE

        draw.text((40, current_y), line, fill=color, font=FONT_MONO)
        current_y += 32

    # Partial line (typing effect)
    if visible_count < len(lines):
        line = lines[visible_count]
        partial = line[:partial_chars]
        draw.text((40, current_y), partial, fill=TERMINAL_GREEN, font=FONT_MONO)
        # Blinking cursor
        if (frame_offset // 10) % 2 == 0:
            cursor_x = 40 + FONT_MONO.getlength(partial)
            draw.rectangle([cursor_x, current_y, cursor_x + 12, current_y + 26],
                           fill=TERMINAL_GREEN)


def draw_subtitle(draw, text, frame_offset, scene_name):
    """Draw Alex Hormozi-style subtitle in center of screen."""
    if not text:
        return

    # Subtitle background
    bbox = FONT_SUBTITLE.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    padding = 20
    bg_x = (WIDTH - text_width) // 2 - padding
    bg_y = HALF_H - text_height // 2 - padding
    bg_w = text_width + padding * 2
    bg_h = text_height + padding * 2

    # Animated background
    draw.rounded_rectangle([bg_x, bg_y, bg_x + bg_w, bg_y + bg_h],
                           radius=12, fill=(0, 0, 0, 200))

    # Word highlighting - make key words pop
    words = text.split()
    current_x = (WIDTH - text_width) // 2

    for word in words:
        word_upper = word.upper()
        is_emphasis = word_upper in ["STOP", "MANUAL", "FREE", "BEAST",
                                      "INSTANT", "THREADS", "BRUTAL",
                                      "ZERO", "HERE", "STARTED"]

        color = NEON_YELLOW if is_emphasis else WHITE
        if is_emphasis:
            # Draw emphasis word with outline
            draw.text((current_x, HALF_H - text_height // 2), word,
                      fill=color, font=FONT_SUBTITLE)
        else:
            draw.text((current_x, HALF_H - text_height // 2), word,
                      fill=color, font=FONT_SUBTITLE)

        current_x += FONT_SUBTITLE.getlength(word + " ")


def draw_energy_bars(draw, frame_offset, scene_name):
    """Draw animated energy/progress bars on the top half."""
    bar_count = 5
    bar_width = 8
    bar_max_height = 60
    spacing = 20
    start_x = WIDTH // 2 - (bar_count * (bar_width + spacing)) // 2
    y = 30

    for i in range(bar_count):
        random.seed(frame_offset + i)
        height = random.randint(10, bar_max_height)
        color = random.choice([NEON_GREEN, NEON_BLUE, NEON_PINK])
        x = start_x + i * (bar_width + spacing)
        draw.rectangle([x, y + bar_max_height - height, x + bar_width, y + bar_max_height],
                       fill=color)


def draw_scene_hook(draw, frame_offset):
    """Scene 1: Hook - massive context window scroll."""
    # Top half: Matrix rain + energy bars
    draw_matrix_rain(draw, frame_offset)
    draw_energy_bars(draw, frame_offset, "hook")

    # Big text overlay
    if frame_offset < 30:
        alpha = min(255, frame_offset * 10)
        draw.text((WIDTH // 2 - 200, 100), "47,293 TOKENS",
                  fill=NEON_BLUE, font=FONT_BOLD_LARGE)
    elif frame_offset < 60:
        draw.text((WIDTH // 2 - 180, 100), "ANALYZING...",
                  fill=NEON_PINK, font=FONT_BOLD_LARGE)
    else:
        draw.text((WIDTH // 2 - 150, 100), "READY ✓",
                  fill=NEON_GREEN, font=FONT_BOLD_LARGE)

    draw_glitch_effect(draw, frame_offset)


def draw_scene_cdp_fix(draw, frame_offset):
    """Scene 2: CDP selector fix."""
    # Top half: Code diff visualization
    draw.rectangle([0, 0, WIDTH, HALF_H], fill=(8, 8, 12))

    # "Before" - red
    draw.rectangle([30, 40, WIDTH - 30, 120], fill=(40, 10, 10))
    draw.text((50, 50), "✗ Selector '#tweet-btn' not found",
              fill=(255, 80, 80), font=FONT_MONO)
    draw.text((50, 85), "CDP Error: ElementMissing",
              fill=(200, 60, 60), font=FONT_MONO_SMALL)

    # Arrow
    if frame_offset > 30:
        draw.text((WIDTH // 2 - 30, 140), "↓ AI FIX ↓",
                  fill=NEON_YELLOW, font=FONT_BOLD)

    # "After" - green
    if frame_offset > 60:
        draw.rectangle([30, 200, WIDTH - 30, 300], fill=(10, 40, 10))
        draw.text((50, 210), "✓ button[data-testid='tweetButton']",
                  fill=NEON_GREEN, font=FONT_MONO)
        draw.text((50, 245), "CDP Connected — Auto-resolved",
                  fill=NEON_GREEN, font=FONT_MONO_SMALL)

    draw_glitch_effect(draw, frame_offset, 0, HALF_H)


def draw_scene_simple_post(draw, frame_offset):
    """Scene 3: Simple post - browser automation."""
    # Top half: Simulated browser window
    draw.rectangle([0, 0, WIDTH, HALF_H], fill=(20, 20, 25))

    # Browser chrome
    draw.rectangle([30, 30, WIDTH - 30, 70], fill=(40, 40, 45))
    draw.text((50, 38), "twitter.com/compose/tweet", fill=(150, 150, 150), font=FONT_MONO_SMALL)

    # Tweet compose area
    draw.rectangle([50, 90, WIDTH - 50, 250], fill=(30, 30, 35))
    draw.rectangle([50, 90, WIDTH - 50, 250], outline=(60, 60, 65), width=2)

    # Typing animation
    tweet_text = "AI automation is wild 🤖"
    chars_visible = min(len(tweet_text), frame_offset // 3)
    draw.text((70, 110), tweet_text[:chars_visible], fill=WHITE, font=FONT_BOLD)

    # Post button
    if frame_offset > 100:
        btn_color = NEON_BLUE if frame_offset < 150 else (0, 120, 200)
        draw.rounded_rectangle([WIDTH - 200, 260, WIDTH - 60, 310], radius=20, fill=btn_color)
        draw.text((WIDTH - 170, 270), "Post", fill=WHITE, font=FONT_BOLD)

    # Success animation
    if frame_offset > 160:
        draw.text((WIDTH // 2 - 100, 350), "✓ PUBLISHED!",
                  fill=NEON_GREEN, font=FONT_BOLD_LARGE)

    draw_glitch_effect(draw, frame_offset, 0, HALF_H)


def draw_scene_thread_build(draw, frame_offset):
    """Scene 4: Thread building."""
    # Top half: Thread posts appearing one by one
    draw.rectangle([0, 0, WIDTH, HALF_H], fill=(12, 12, 16))

    draw.text((WIDTH // 2 - 120, 20), "THREAD BUILDER",
              fill=NEON_PINK, font=FONT_BOLD)

    posts = [
        ("1/4", "🧵 AI agents are replacing manual work"),
        ("2/4", "Here's how I built a Twitter beast"),
        ("3/4", "Zero API costs. 100% free models."),
        ("4/4", "Follow @novaisabuilder for more"),
    ]

    for i, (num, text) in enumerate(posts):
        post_start = i * 50
        if frame_offset > post_start:
            y = 80 + i * 90
            alpha = min(255, (frame_offset - post_start) * 10)

            # Post card
            draw.rounded_rectangle([40, y, WIDTH - 40, y + 70], radius=12,
                                   fill=(30, 30, 35))
            draw.rounded_rectangle([40, y, WIDTH - 40, y + 70], radius=12,
                                   outline=NEON_PINK if i == 3 else (60, 60, 65), width=2)

            # Post number
            draw.text((60, y + 10), num, fill=NEON_PINK, font=FONT_BOLD)

            # Post text
            chars = min(len(text), (frame_offset - post_start) // 2)
            draw.text((60, y + 35), text[:chars], fill=WHITE, font=FONT_MONO)

    draw_glitch_effect(draw, frame_offset, 0, HALF_H)


def draw_scene_media_upload(draw, frame_offset):
    """Scene 5: Media upload with images."""
    # Top half: Image upload visualization
    draw.rectangle([0, 0, WIDTH, HALF_H], fill=(10, 10, 14))

    draw.text((WIDTH // 2 - 140, 20), "MEDIA UPLOAD",
              fill=NEON_YELLOW, font=FONT_BOLD)

    # Upload progress
    if frame_offset < 100:
        progress = frame_offset / 100
        bar_width = int((WIDTH - 100) * progress)
        draw.rectangle([50, 100, WIDTH - 50, 120], fill=(40, 40, 45))
        draw.rectangle([50, 100, 50 + bar_width, 120], fill=NEON_YELLOW)
        draw.text((WIDTH // 2 - 80, 130), f"Uploading... {int(progress * 100)}%",
                  fill=WHITE, font=FONT_MONO)
    elif frame_offset < 180:
        # Image preview grid
        for i in range(4):
            x = 60 + (i % 2) * 260
            y = 100 + (i // 2) * 140
            draw.rounded_rectangle([x, y, x + 230, y + 120], radius=8,
                                   fill=(35, 35, 40))
            # Simulated image placeholder
            draw.rectangle([x + 10, y + 10, x + 220, y + 80], fill=(50, 50, 55))
            draw.text((x + 60, y + 90), f"image_0{i+1}.png", fill=NEON_GREEN, font=FONT_MONO_SMALL)
    else:
        # Success
        draw.text((WIDTH // 2 - 180, 150), "✓ MEDIA ATTACHED",
                  fill=NEON_GREEN, font=FONT_BOLD_LARGE)
        draw.text((WIDTH // 2 - 150, 230), "$0.00 API COST",
                  fill=NEON_YELLOW, font=FONT_BOLD)

    draw_glitch_effect(draw, frame_offset, 0, HALF_H)


def draw_scene_montage(draw, frame_offset):
    """Scene 6: Fast montage of completed posts."""
    # Top half: Stats dashboard
    draw.rectangle([0, 0, WIDTH, HALF_H], fill=(8, 8, 12))

    # Animated stats
    stats = [
        ("Tasks Done", "47", NEON_GREEN),
        ("Success Rate", "98.2%", NEON_BLUE),
        ("API Cost", "$0.00", NEON_YELLOW),
        ("Models Used", "FREE", NEON_PINK),
    ]

    for i, (label, value, color) in enumerate(stats):
        y = 40 + i * 100
        if frame_offset > i * 30:
            # Stat card
            draw.rounded_rectangle([40, y, WIDTH - 40, y + 80], radius=12,
                                   fill=(25, 25, 30))
            draw.text((60, y + 10), label, fill=(150, 150, 150), font=FONT_MONO)
            draw.text((60, y + 40), value, fill=color, font=FONT_BOLD_LARGE)

    draw_glitch_effect(draw, frame_offset, 0, HALF_H)


def draw_scene_outro(draw, frame_offset):
    """Scene 7: Outro with handle."""
    # Top half: Big handle + CTA
    draw.rectangle([0, 0, WIDTH, HALF_H], fill=(5, 5, 8))

    # Animated background particles
    random.seed(frame_offset)
    for _ in range(30):
        x = random.randint(0, WIDTH)
        y = random.randint(0, HALF_H)
        size = random.randint(1, 4)
        color = random.choice([NEON_GREEN, NEON_BLUE, NEON_PINK, WHITE])
        draw.ellipse([x, y, x + size, y + size], fill=color)

    # Handle
    scale = min(1.0, frame_offset / 30)
    draw.text((WIDTH // 2 - 200, 120), "@novaisabuilder",
              fill=NEON_GREEN, font=FONT_BOLD_LARGE)

    # CTA
    if frame_offset > 30:
        draw.text((WIDTH // 2 - 150, 220), "FOLLOW THE BUILD",
                  fill=WHITE, font=FONT_BOLD)

    if frame_offset > 50:
        draw.text((WIDTH // 2 - 180, 300), "We're just getting started.",
                  fill=NEON_BLUE, font=FONT_MONO)

    # Animated border
    border_progress = (frame_offset % 60) / 60
    border_length = int(WIDTH * border_progress)
    draw.line([(0, 0), (border_length, 0)], fill=NEON_GREEN, width=4)
    draw.line([(0, 0), (0, HALF_H)], fill=NEON_GREEN, width=4)


SCENE_DRAWERS = {
    "hook": draw_scene_hook,
    "cdp_fix": draw_scene_cdp_fix,
    "simple_post": draw_scene_simple_post,
    "thread_build": draw_scene_thread_build,
    "media_upload": draw_scene_media_upload,
    "montage": draw_scene_montage,
    "outro": draw_scene_outro,
}


def generate_frame(frame_num):
    """Generate a single frame."""
    img = Image.new('RGB', (WIDTH, HEIGHT), BLACK)
    draw = ImageDraw.Draw(img)

    # Determine current scene
    scene_name = None
    scene_frame_offset = 0
    for start, end, name in SCENES:
        if start <= frame_num < end:
            scene_name = name
            scene_frame_offset = frame_num - start
            break

    if scene_name is None:
        return img

    # Draw top half (animated visuals)
    SCENE_DRAWERS[scene_name](draw, scene_frame_offset)

    # Draw bottom half (terminal)
    terminal_lines = TERMINAL_TEXT[scene_name]
    draw_terminal(draw, terminal_lines, scene_frame_offset, len(terminal_lines))

    # Draw subtitle
    subs = SUBTITLES.get(scene_name, [])
    current_sub = ""
    for text, start, end in subs:
        if start <= scene_frame_offset < end:
            current_sub = text
            break
    draw_subtitle(draw, current_sub, scene_frame_offset, scene_name)

    # Scene transition effect
    for start, end, name in SCENES:
        if frame_num == start and start > 0:
            # Flash effect
            draw.rectangle([0, 0, WIDTH, HEIGHT], fill=(255, 255, 255))

    return img


def main():
    print(f"Generating {TOTAL_FRAMES} frames at {FPS}fps ({TOTAL_DURATION}s)...")

    for frame_num in range(TOTAL_FRAMES):
        if frame_num % 30 == 0:
            print(f"  Frame {frame_num}/{TOTAL_FRAMES} ({frame_num/FPS:.1f}s)")

        img = generate_frame(frame_num)
        frame_path = os.path.join(OUT_DIR, f"frame_{frame_num:06d}.png")
        img.save(frame_path, "PNG")

    print(f"\n✓ Generated {TOTAL_FRAMES} frames in {OUT_DIR}/")
    print("\nTo compile video, run:")
    print(f"  ffmpeg -framerate {FPS} -i {OUT_DIR}/frame_%06d.png "
          f"-c:v libx264 -pix_fmt yuv420p -crf 18 output.mp4")


if __name__ == "__main__":
    main()
