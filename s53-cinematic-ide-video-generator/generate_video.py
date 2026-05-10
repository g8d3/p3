#!/usr/bin/env python3
"""
Cinematic Programming Interface Video Generator
Premium, minimal, tech-oriented video with synchronized audio.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageChops
import math
import random
import logging

from moviepy import VideoClip, AudioClip

logging.getLogger('moviepy').setLevel(logging.WARNING)

# ============================================================
# CONFIGURATION
# ============================================================
WIDTH, HEIGHT = 1920, 1080
FPS = 30
DURATION = 36  # seconds
SAMPLE_RATE = 44100

# Colors
BG_DARK = (8, 8, 14)
BG_MID = (12, 14, 22)
GRID_COLOR = (20, 25, 38)
ACCENT_BLUE = (80, 160, 255)
ACCENT_CYAN = (100, 220, 240)
ACCENT_PURPLE = (180, 130, 255)
ACCENT_GREEN = (120, 220, 150)
ACCENT_GOLD = (255, 210, 100)
ACCENT_ORANGE = (255, 160, 60)
TEXT_PRIMARY = (200, 215, 235)
TEXT_SECONDARY = (120, 140, 165)
TEXT_DIM = (70, 85, 105)
COMMENT_COLOR = (100, 120, 140)
KEYWORD_COLOR = (120, 180, 255)
STRING_COLOR = (150, 220, 150)
CURSOR_COLOR = (180, 200, 220)

# Fonts
FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ============================================================
# UTILITY
# ============================================================

def load_font(size):
    try:
        return ImageFont.truetype(FONT_MONO, size)
    except Exception:
        return ImageFont.load_default()

def load_sans(size):
    try:
        return ImageFont.truetype(FONT_SANS, size)
    except Exception:
        return ImageFont.load_default()

def ts(text, font):
    """Text size."""
    try:
        bbox = font.getbbox(text)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    except:
        return font.getsize(text)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def ease_io(t):
    t = clamp(t, 0, 1)
    return t * t * (3 - 2 * t)

def fade_opacity(t, fi_start, fi_end, fo_start, fo_end):
    if t < fi_start:
        return 0.0
    if t < fi_end:
        return ease_io((t - fi_start) / (fi_end - fi_start))
    if t < fo_start:
        return 1.0
    if t < fo_end:
        return 1.0 - ease_io((t - fo_start) / (fo_end - fo_start))
    return 0.0

def alpha_color(color, a):
    return tuple(int(c * a) for c in color)

# ============================================================
# BACKGROUND
# ============================================================

def make_base_frame(w, h, t):
    """Create base background with subtle animation."""
    img = Image.new('RGB', (w, h), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Grid
    spacing = 50
    for x in range(0, w, spacing):
        draw.line([(x, 0), (x, h)], fill=GRID_COLOR, width=1)
    for y in range(0, h, spacing):
        draw.line([(0, y), (w, y)], fill=GRID_COLOR, width=1)

    # Vignette
    for i in range(120):
        a = int(2 * (1 - i / 120))
        if a <= 0:
            break
        draw.rectangle([0, i, w, i + 1], fill=(0, 0, 0))
        draw.rectangle([0, h - i - 1, w, h - i], fill=(0, 0, 0))
        draw.rectangle([i, 0, i + 1, h], fill=(0, 0, 0))
        draw.rectangle([w - i - 1, 0, w - i, h], fill=(0, 0, 0))

    # Subtle glow
    glow = 0.015 + 0.008 * math.sin(t * 0.3)
    glow_overlay = Image.new('RGB', (w, h), (0, 0, 0))
    gdraw = ImageDraw.Draw(glow_overlay)
    for i in range(min(w, h) // 3):
        a = int(80 * (1 - i / (min(w, h) // 3)) * glow * 10)
        if a <= 0:
            break
        gdraw.ellipse([w - i - 100, h - i - 100, w, h], fill=(*ACCENT_BLUE, a))
        cx1, cy1 = max(0, i - 100), max(0, i - 100)
        cx2, cy2 = min(w, 200), min(h, 200)
        if cx2 > cx1 and cy2 > cy1:
            gdraw.ellipse([cx1, cy1, cx2, cy2], fill=(*ACCENT_PURPLE, a // 3))
    img = ImageChops.add(img, glow_overlay)

    # Scanlines
    sdraw = ImageDraw.Draw(img)
    for y in range(0, h, 3):
        sdraw.rectangle([0, y, w, y], fill=(0, 0, 0, 6))

    return img

# ============================================================
# CONTENT DATA
# ============================================================

CODE_LINES = [
    [("// ", COMMENT_COLOR), ("Neural Interface Core v3.2", COMMENT_COLOR)],
    [("", None)],
    [("async function ", KEYWORD_COLOR), ("initNeuralInterface", ACCENT_PURPLE), ("(", TEXT_PRIMARY), (")", TEXT_PRIMARY), (" {", TEXT_PRIMARY)],
    [("  const ", KEYWORD_COLOR), ("model", TEXT_PRIMARY), (" = await ", KEYWORD_COLOR), ("loadModel", ACCENT_PURPLE), ("(", TEXT_PRIMARY), ("\"neural-core-latest\"", STRING_COLOR), (")", TEXT_PRIMARY), (";", TEXT_PRIMARY)],
    [("  const ", KEYWORD_COLOR), ("config", TEXT_PRIMARY), (" = {", TEXT_PRIMARY)],
    [("    precision: ", ACCENT_GOLD), ("\"float32\"", STRING_COLOR), (",", TEXT_PRIMARY)],
    [("    inferenceMode: ", ACCENT_GOLD), ("\"stream\"", STRING_COLOR), (",", TEXT_PRIMARY)],
    [("    quantization: ", ACCENT_GOLD), ("\"int8\"", STRING_COLOR), (",", TEXT_PRIMARY)],
    [("    device: ", ACCENT_GOLD), ("\"cuda:0\"", STRING_COLOR), ("", TEXT_PRIMARY)],
    [("  };", TEXT_PRIMARY)],
    [("", None)],
    [("  const ", KEYWORD_COLOR), ("pipeline", TEXT_PRIMARY), (" = new ", KEYWORD_COLOR), ("InferencePipeline", ACCENT_PURPLE), ("(", TEXT_PRIMARY), ("model", TEXT_PRIMARY), (", ", TEXT_PRIMARY), ("config", TEXT_PRIMARY), (");", TEXT_PRIMARY)],
    [("  ", TEXT_PRIMARY), ("await ", KEYWORD_COLOR), ("pipeline.initialize", ACCENT_PURPLE), ("(", TEXT_PRIMARY), (");", TEXT_PRIMARY)],
    [("  return ", KEYWORD_COLOR), ("pipeline", TEXT_PRIMARY), (";", TEXT_PRIMARY)],
    [("}", TEXT_PRIMARY)],
]

SYSTEM_INFO = [
    ("KERNEL", "6.8.0-neural-x64"),
    ("HOST", "neural-interface-01"),
    ("GPU", "NVIDIA H200 × 4"),
    ("MEM", "1.2 TB / 2.0 TB"),
    ("MODEL", "neural-core-v3.2.1"),
    ("TEMP", "42.3 °C"),
    ("UPTIME", "14d 7h 32m"),
    ("THROUGHPUT", "847.2 GFLOPS"),
]

TERMINAL_LINES = [
    "> Initializing neural interface...",
    "> Loading model: neural-core-v3.2.1",
    "> Configuring inference pipeline...",
    "> Quantizing weights: int8",
    "> Starting streaming inference...",
    "> Pipeline ready: throughput 847.2 GFLOPS",
    "> All systems nominal.",
]

# ============================================================
# SCENE DEFINITIONS
# ============================================================

SCENES = [
    ("intro", 0, 5),
    ("system", 5, 13),
    ("code", 13, 23),
    ("viz", 23, 30),
    ("outro", 30, 36),
]

def get_scene(t):
    for name, start, end in SCENES:
        if start <= t < end:
            return name, start, end
    return None, 0, 0

# ============================================================
# FRAME GENERATORS
# ============================================================

def scene_intro(t, lt, dur):
    img = make_base_frame(WIDTH, HEIGHT, t)
    draw = ImageDraw.Draw(img)

    op = fade_opacity(lt, 0, 0.8, dur - 0.5, dur)
    if op <= 0:
        return np.array(img)

    font_big = load_font(64)
    font_small = load_font(26)

    title = ">>> NEURAL INTERFACE"
    w, h = ts(title, font_big)
    draw.text(((WIDTH - w) // 2, HEIGHT // 2 - 60), title,
              font=font_big, fill=alpha_color(ACCENT_BLUE, op))

    sub = "initializing core systems..."
    w2, h2 = ts(sub, font_small)
    draw.text(((WIDTH - w2) // 2, HEIGHT // 2 + 10), sub,
              font=font_small, fill=alpha_color(TEXT_SECONDARY, op))

    # Cursor blink
    blink = 1.0 if int(t * 4) % 2 == 0 else 0.3
    ca = int(200 * blink * op)
    if ca > 5:
        draw.text(((WIDTH - w2) // 2 + w2 + 8, HEIGHT // 2 + 10), "▌",
                  font=font_small, fill=(*CURSOR_COLOR, ca))

    return np.array(img)


def scene_system(t, lt, dur):
    img = make_base_frame(WIDTH, HEIGHT, t)
    draw = ImageDraw.Draw(img)

    font_lbl = load_font(22)
    font_val = load_font(26)
    font_title = load_sans(48)
    font_code = load_font(26)

    # Title
    top = fade_opacity(lt, 0, 0.4, dur - 0.3, dur)
    if top > 0:
        draw.text((60, 40), "SYSTEM STATUS",
                  font=font_title, fill=alpha_color(ACCENT_CYAN, top))
        draw.line([(60, 85), (400, 85)],
                  fill=alpha_color(ACCENT_CYAN, top * 0.5), width=1)

    # Info grid
    sx, sy = 100, 140
    cw, rh = 400, 50

    for i, (label, value) in enumerate(SYSTEM_INFO):
        et = 0.3 + i * 0.15
        eop = fade_opacity(lt, et, et + 0.3, dur - 0.3, dur)
        if eop <= 0:
            continue

        col = i % 2
        row = i // 2
        x = sx + col * cw
        y = sy + int(row * rh * 1.8)

        a = int(255 * eop)
        draw.text((x, y), f"{label}:",
                  font=font_lbl, fill=(*TEXT_DIM, a))
        draw.text((x + 120, y), value,
                  font=font_val, fill=(*TEXT_PRIMARY, a))

        # Dot indicator
        phase = (t + i * 0.5) % 2
        bright = 1.0 if phase < 1.5 else 0.2
        da = int(180 * eop * bright)
        draw.ellipse([x - 20, y + 5, x - 10, y + 15],
                     fill=(*ACCENT_GREEN, da))

    # Decorative neural nodes
    nop = fade_opacity(lt, 1.5, 2.0, dur - 0.3, dur)
    if nop > 0:
        a = int(60 * nop)
        nodes = [(1400, 200), (1600, 300), (1500, 450),
                 (1750, 350), (1650, 500), (1450, 550)]
        for i, (nx, ny) in enumerate(nodes):
            draw.ellipse([nx - 4, ny - 4, nx + 4, ny + 4],
                         fill=(*ACCENT_PURPLE, a))
            for j, (nx2, ny2) in enumerate(nodes[i + 1:], i + 1):
                if random.random() > 0.4:
                    draw.line([(nx, ny), (nx2, ny2)],
                              fill=(*ACCENT_PURPLE, int(a * 0.3)), width=1)

    # Bottom bars
    bop = fade_opacity(lt, 1.0, 1.5, dur - 0.3, dur)
    if bop > 0:
        a = int(150 * bop)
        by = HEIGHT - 80
        labels = ["CPU", "GPU", "MEM", "NET"]
        colors = [ACCENT_BLUE, ACCENT_PURPLE, ACCENT_GREEN, ACCENT_CYAN]
        values = [0.72, 0.88, 0.55, 0.43]
        for i, (lb, col, val) in enumerate(zip(labels, colors, values)):
            bx = 100 + i * 250
            bw, bh = 180, 6
            wobble = 0.02 * math.sin(t * 2 + i * 1.5)
            dv = clamp(val + wobble, 0, 1)
            draw.text((bx, by - 20), lb,
                      font=font_code, fill=(*TEXT_DIM, a))
            draw.rectangle([bx, by, bx + bw, by + bh],
                           fill=(30, 35, 50))
            if dv > 0:
                fw = int(bw * dv)
                draw.rectangle([bx, by, bx + fw, by + bh], fill=(*col, a))
            pct = f"{int(dv * 100)}%"
            pw, _ = ts(pct, font_code)
            draw.text((bx + bw + 8, by - 6), pct,
                      font=font_code, fill=(*col, a))

    return np.array(img)


def scene_code(t, lt, dur):
    img = make_base_frame(WIDTH, HEIGHT, t)
    draw = ImageDraw.Draw(img)

    font_code = load_font(26)
    font_small = load_font(20)
    font_title = load_sans(48)

    wop = fade_opacity(lt, 0, 0.8, dur - 0.5, dur)
    if wop <= 0:
        return np.array(img)

    a = int(200 * wop)

    wx, wy = 80, 60
    ww, wh = 1100, 700

    # Window bg
    draw.rectangle([wx, wy, wx + ww, wy + wh], fill=(*BG_MID, a))
    draw.rectangle([wx, wy, wx + ww, wy + wh], outline=(*GRID_COLOR, a), width=1)

    # Title bar
    draw.rectangle([wx, wy, wx + ww, wy + 36], fill=(*BG_MID, a))
    draw.line([(wx, wy + 36), (wx + ww, wy + 36)],
              fill=(*GRID_COLOR, a), width=1)

    # Window dots
    for i, dc in enumerate([(255, 95, 87), (255, 189, 46), (39, 201, 63)]):
        draw.ellipse([wx + 14 + i * 22, wy + 12, wx + 24 + i * 22, wy + 22],
                     fill=dc)

    draw.text((wx + 100, wy + 8), "neural_interface.ts — VS Code",
              font=font_small, fill=(*TEXT_DIM, a))

    # Code content
    txt_x = wx + 80
    line_h = 34
    txt_y0 = wy + 55

    # Calculate line y positions
    line_ys = {}
    cy = txt_y0
    for idx, tokens in enumerate(CODE_LINES):
        line_ys[idx] = cy
        if not tokens or all(t[0] == '' for t in tokens):
            cy += line_h
        else:
            max_h = 0
            for text, _ in tokens:
                _, h = ts(text, font_code) if text else (0, 0)
                max_h = max(max_h, h)
            cy += max_h + 6

    # Typing progress
    chars_per_sec = 16
    total_chars = int(max(0, (lt - 0.5) * chars_per_sec)) if lt > 0.5 else 0

    # Flat char list
    flat = []
    for li, tokens in enumerate(CODE_LINES):
        for text, col in tokens:
            for ch in text:
                flat.append((li, ch, col if col else TEXT_PRIMARY))

    # Draw code
    chars_drawn = 0
    for li, tokens in enumerate(CODE_LINES):
        y = line_ys[li]
        # Line number
        ln_text = f"{li + 1:2d}"
        draw.text((wx + 60, y), ln_text,
                  font=font_code, fill=(*TEXT_DIM, int(80 * wop)))

        x = txt_x
        for text, col in tokens:
            if not text:
                continue
            actual_color = col if col else TEXT_PRIMARY
            n = 0
            for ci, ch in enumerate(text):
                gi = chars_drawn + ci
                if gi < total_chars:
                    n += 1
                else:
                    break
            if n > 0:
                part = text[:n]
                draw.text((x, y), part,
                          font=font_code, fill=actual_color)
                pw, _ = ts(part, font_code)
                x += pw
            else:
                pw, _ = ts(text, font_code)
                x += pw
            chars_drawn += len(text)

    # Cursor
    if lt > 0.5 and lt < dur - 0.5:
        blink = 1.0 if int(t * 6) % 2 == 0 else 0.3
        ca = int(200 * wop * blink)
        if ca > 5 and total_chars < len(flat):
            cx = txt_x
            for fi in range(total_chars):
                _, ch, _ = flat[fi]
                cw, _ = ts(ch, font_code)
                cx += cw
            draw.text((cx, line_ys[flat[total_chars][0]]), "▌",
                      font=font_code, fill=(*CURSOR_COLOR, ca))

    return np.array(img)


def scene_viz(t, lt, dur):
    img = make_base_frame(WIDTH, HEIGHT, t)
    draw = ImageDraw.Draw(img)

    font_code = load_font(26)
    font_small = load_font(20)
    font_title = load_sans(48)

    # Terminal
    top = fade_opacity(lt, 0, 0.6, dur - 0.5, dur)
    if top > 0:
        a = int(200 * top)
        tx, ty = 80, 60
        tw, th = 1000, 350

        draw.rectangle([tx, ty, tx + tw, ty + th], fill=(*BG_MID, a))
        draw.rectangle([tx, ty, tx + tw, ty + th], outline=(*GRID_COLOR, a), width=1)
        draw.rectangle([tx, ty, tx + tw, ty + 32], fill=(5, 5, 10))
        draw.text((tx + 14, ty + 6), "TERMINAL",
                  font=font_small, fill=(*TEXT_DIM, a))

        for i, line in enumerate(TERMINAL_LINES):
            lt2 = 0.3 + i * 0.25
            lop = fade_opacity(lt, lt2, lt2 + 0.15, dur - 0.3, dur)
            if lop > 0:
                la = int(255 * lop * top)
                draw.text((tx + 20, ty + 50 + i * 32), ">",
                          font=font_code, fill=(*ACCENT_GREEN, la))
                draw.text((tx + 36, ty + 50 + i * 32), line[2:],
                          font=font_code, fill=(*TEXT_PRIMARY, la))

        # Blinking cursor
        if lt > 1.0 and lt < dur - 0.5:
            bl = 1.0 if int(t * 5) % 2 == 0 else 0.2
            ca = int(200 * top * bl)
            ly = ty + 50 + len(TERMINAL_LINES) * 32
            draw.text((tx + 20, ly), "▌",
                      font=font_code, fill=(*ACCENT_GREEN, ca))

    # Visualization panel
    vop = fade_opacity(lt, 1.0, 1.5, dur - 0.3, dur)
    if vop > 0:
        a = int(180 * vop)
        vx, vy = 1120, 60
        vw, vh = 350, 350

        draw.rectangle([vx, vy, vx + vw, vy + vh], fill=(*BG_MID, a))
        draw.rectangle([vx, vy, vx + vw, vy + vh], outline=(*GRID_COLOR, a), width=1)
        draw.text((vx + 14, vy + 10), "INFERENCE",
                  font=font_small, fill=(*TEXT_DIM, a))

        # Waveform
        wc_y = vy + 80
        pts = []
        for px in range(vx + 20, vx + vw - 20, 4):
            rx = (px - vx) / vw
            wv = (math.sin(rx * 8 + t * 3) * 0.5 +
                  math.sin(rx * 13 + t * 2.1) * 0.3 +
                  math.sin(rx * 21 + t * 1.7) * 0.2)
            pts.append((px, wc_y + wv * 40))

        for i in range(len(pts) - 1):
            fr = i / len(pts)
            r = int(ACCENT_BLUE[0] * (1 - fr) + ACCENT_PURPLE[0] * fr)
            g = int(ACCENT_BLUE[1] * (1 - fr) + ACCENT_PURPLE[1] * fr)
            b = int(ACCENT_BLUE[2] * (1 - fr) + ACCENT_PURPLE[2] * fr)
            draw.line([pts[i], pts[i + 1]], fill=(r, g, b, int(180 * vop)), width=2)

        # Activity bars
        by0 = vy + 150
        blabels = ["L1", "L2", "L3", "L4"]
        bvals = [0.6, 0.85, 0.4, 0.7]
        for i, (bl, bv) in enumerate(zip(blabels, bvals)):
            bx = vx + 25 + i * 80
            bw, bh = 50, 100
            wobble = 0.1 * math.sin(t * 2.5 + i * 1.2)
            dv = clamp(bv + wobble, 0.05, 1)
            bh2 = int(bh * dv)
            draw.rectangle([bx, by0, bx + bw, by0 + bh], fill=(30, 35, 50))
            bar_color = (int(120 + 80 * dv), int(180 + 40 * dv), 255)
            draw.rectangle([bx, by0 + bh - bh2, bx + bw, by0 + bh], fill=bar_color)
            draw.text((bx + 15, by0 + bh + 8), bl,
                      font=font_small, fill=(*TEXT_DIM, a))

        # Status
        st = "ACTIVE  |  thpt: 847.2 GFLOPS  |  latency: 2.3ms"
        draw.text((vx + 14, vy + vh - 40), st,
                  font=font_small, fill=(*TEXT_SECONDARY, a))

    return np.array(img)


def scene_outro(t, lt, dur):
    img = make_base_frame(WIDTH, HEIGHT, t)
    draw = ImageDraw.Draw(img)

    font_big = load_font(64)
    font_code = load_font(26)
    font_small = load_font(20)

    # Fade over the last 4 seconds, and also overall fade
    overall = 1.0 if lt < 2 else max(0, 1 - (lt - 2) / 4)
    final_fade = fade_opacity(lt, dur - 1.5, dur - 0.3, dur - 0.3, dur)

    op = overall * final_fade
    if op <= 0:
        return np.array(img)

    a = int(255 * op)

    title = "SYSTEM READY"
    w, h = ts(title, font_big)
    draw.text(((WIDTH - w) // 2, HEIGHT // 2 - 40), title,
              font=font_big, fill=(*ACCENT_GREEN, a))

    sub = "all systems nominal · neural pipeline active"
    w2, h2 = ts(sub, font_code)
    draw.text(((WIDTH - w2) // 2, HEIGHT // 2 + 20), sub,
              font=font_code, fill=(*TEXT_SECONDARY, int(a * 0.7)))

    draw.line([(WIDTH // 2 - 100, HEIGHT // 2 + 55),
               (WIDTH // 2 + 100, HEIGHT // 2 + 55)],
              fill=(*ACCENT_GREEN, int(a * 0.4)), width=1)

    ver = "v3.2.1 — neural interface core"
    draw.text((WIDTH - 350, HEIGHT - 60), ver,
              font=font_small, fill=(*TEXT_DIM, int(a * 0.5)))

    return np.array(img)


# ============================================================
# MASTER FRAME FUNCTION
# ============================================================

def make_frame(t):
    scene_name, s_start, s_end = get_scene(t)
    if scene_name is None:
        return np.array(make_base_frame(WIDTH, HEIGHT, t))

    lt = t - s_start
    dur = s_end - s_start

    if scene_name == "intro":
        return scene_intro(t, lt, dur)
    elif scene_name == "system":
        return scene_system(t, lt, dur)
    elif scene_name == "code":
        return scene_code(t, lt, dur)
    elif scene_name == "viz":
        return scene_viz(t, lt, dur)
    elif scene_name == "outro":
        return scene_outro(t, lt, dur)

    return np.array(make_base_frame(WIDTH, HEIGHT, t))


# ============================================================
# AUDIO GENERATION
# ============================================================

def make_audio(t):
    """
    Generate all audio layers.
    t: float or numpy array of time values (seconds)
    returns: numpy array of samples
    """
    if isinstance(t, (int, float)):
        t = np.array([t])
    n = len(t)
    audio = np.zeros(n)

    # --- 1. Ambient drone ---
    f1 = 55.0
    l1 = 0.25 * np.sin(2 * np.pi * f1 * t)
    l1 += 0.12 * np.sin(2 * np.pi * f1 * 2 * t)

    f2 = 110.0
    l2 = 0.18 * np.sin(2 * np.pi * f2 * t + 0.3)
    l2 += 0.10 * np.sin(2 * np.pi * f2 * 1.5 * t + 0.7)

    f3 = 220.0
    l3 = 0.08 * np.sin(2 * np.pi * f3 * t + 1.2)
    l3 += 0.04 * np.sin(2 * np.pi * f3 * 2.01 * t + 2.1)

    am = 0.5 + 0.5 * np.sin(2 * np.pi * 0.1 * t)
    am2 = 0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t + 1.0)

    ambient = l1 * am + l2 * (0.5 + 0.3 * am2) + l3 * 0.7
    ambient = np.tanh(ambient * 1.5) * 0.5
    audio += ambient

    # --- 2. Subtle texture/noise floor ---
    noise = np.random.normal(0, 1, n)
    window = int(0.01 * SAMPLE_RATE)
    if window > 1 and n > window:
        kernel = np.ones(window) / window
        noise = np.convolve(noise, kernel, mode='same')
    noise *= (0.5 + 0.5 * np.sin(2 * np.pi * 0.05 * t))
    audio += noise * 0.06

    # --- 3. Bass pulses ---
    pulse_times = [1.0, 4.5, 7.0, 12.0, 16.5, 22.0, 25.5, 30.0, 34.0]
    for pt in pulse_times:
        delta = t - pt
        pulse = np.exp(-((delta * 10) ** 2))
        thump = np.sin(2 * np.pi * 80 * delta) * pulse
        thump += 0.5 * np.sin(2 * np.pi * 55 * delta) * pulse
        audio += thump * 0.25

    # --- 4. Keyboard clicks ---
    click_data = [
        # Intro
        (0.8, 0.30), (1.2, 0.25), (1.8, 0.35), (2.5, 0.30), (3.2, 0.40),
        (3.8, 0.35), (4.2, 0.30),
        # System
        (5.5, 0.35), (5.85, 0.30), (6.2, 0.25), (6.6, 0.35), (7.0, 0.30),
        (7.5, 0.40), (8.0, 0.30), (8.5, 0.35), (9.0, 0.25), (9.5, 0.40),
        (10.0, 0.30),
        # Code typing
        (13.5, 0.45), (13.7, 0.30), (14.0, 0.50), (14.15, 0.35),
        (14.3, 0.40), (14.5, 0.45), (14.65, 0.30), (14.8, 0.40),
        (15.0, 0.55), (15.2, 0.30), (15.4, 0.45), (15.6, 0.35),
        (15.8, 0.50), (16.0, 0.40), (16.2, 0.55), (16.4, 0.35),
        (16.6, 0.50), (16.8, 0.30), (17.0, 0.60), (17.2, 0.35),
        (17.4, 0.45), (17.6, 0.30), (17.8, 0.50), (18.0, 0.40),
        (18.2, 0.35), (18.4, 0.55), (18.6, 0.30), (18.8, 0.45),
        (19.0, 0.50), (19.2, 0.35), (19.4, 0.40), (19.6, 0.30),
        (19.8, 0.50), (20.0, 0.40), (20.3, 0.35), (20.6, 0.45),
        (21.0, 0.50), (21.4, 0.30),
        # Terminal
        (23.2, 0.35), (23.5, 0.30), (23.8, 0.40), (24.1, 0.35),
        (24.4, 0.30), (24.7, 0.40), (25.0, 0.35), (25.3, 0.30),
        (25.6, 0.40), (25.9, 0.35),
        # Outro
        (30.5, 0.35), (31.0, 0.30), (31.8, 0.40), (32.5, 0.35),
        (33.2, 0.30), (33.8, 0.25),
    ]

    for ct, intensity in click_data:
        delta = t - ct
        # Asymmetric envelope: fast attack, medium decay
        env = np.exp(-((delta * (1 + 5 * (delta > 0))) ** 2) / (2 * 0.002 ** 2))
        # Mechanical key sound
        noise_burst = np.random.normal(0, 1, n)
        key = noise_burst * 0.3 + np.sin(2 * np.pi * 2000 * delta + noise_burst * 0.5) * 0.4
        key += np.sin(2 * np.pi * 4000 * delta) * 0.2
        key *= env * intensity * 0.7
        audio += key

    # --- Global fade in/out ---
    fade_in = np.clip(t / 1.5, 0, 1)
    fade_out = np.clip((DURATION - t) / 2.0, 0, 1)
    audio *= fade_in * fade_out

    # Master volume boost
    audio *= 1.3

    # Soft limit
    max_v = np.max(np.abs(audio))
    if max_v > 0.95:
        audio *= 0.95 / max_v

    return audio


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  CINEMATIC PROGRAMMING INTERFACE VIDEO GENERATOR")
    print("=" * 60)
    print(f"\n  Resolution: {WIDTH}x{HEIGHT}")
    print(f"  Duration:   {DURATION}s")
    print(f"  FPS:        {FPS}")
    print(f"  Audio:      {SAMPLE_RATE} Hz")
    print()

    print("  Creating video clip...")
    video = VideoClip(make_frame, duration=DURATION)

    print("  Creating audio clip...")
    audio = AudioClip(make_audio, duration=DURATION, fps=SAMPLE_RATE)

    print("  Attaching audio...")
    final = video.with_audio(audio)

    output = "/home/vuos/code/p3/s53/cinematic_interface.mp4"
    print(f"\n  Rendering to: {output}")
    print()

    final.write_videofile(
        output,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        bitrate="8000k",
        audio_bitrate="320k",
        threads=4,
        logger="bar"
    )

    print(f"\n  ✅ Done! Video saved to: {output}")
    print()


if __name__ == "__main__":
    main()
