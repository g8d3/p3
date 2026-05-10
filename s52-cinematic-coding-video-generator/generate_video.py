#!/usr/bin/env python3
"""
Premium Cinematic Coding Interface Video Generator v2
Generates a short film-style demo of a terminal/coding session.
"""

import os, sys, math, numpy as np, wave
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ─── CONFIG ────────────────────────────────────────────────────────────────

WIDTH, HEIGHT = 800, 450
FPS = 30
DURATION = 20
TOTAL_FRAMES = DURATION * FPS

OUTPUT_DIR = "/home/vuos/code/p3/s52/generated_frames"
FINAL_VIDEO = "/home/vuos/code/p3/s52/cinematic_demo.mp4"
FINAL_AUDIO = "/home/vuos/code/p3/s52/cinematic_audio.wav"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ─── COLORS ────────────────────────────────────────────────────────────────

BG_DARK       = (12, 16, 32)
BG_MID        = (16, 22, 42)
BG_TOP        = (14, 18, 34)
BG_BOTTOM     = (28, 38, 68)
TEXT_PRIMARY  = (215, 225, 240)   # bright white-blue
TEXT_DIM      = (140, 160, 195)
TEXT_PROMPT   = (40, 230, 255)     # brighter cyan
TEXT_CMD      = (255, 215, 120)   # warm gold
TEXT_RESULT   = (40, 255, 150)     # bright green
ACCENT_CYAN   = (40, 230, 255)
ACCENT_GREEN  = (40, 255, 150)
CURSOR_COLOR  = (40, 230, 255)

# ─── FONTS ─────────────────────────────────────────────────────────────────

FONT_PATHS = [
    "/usr/share/fonts/truetype/hack/Hack-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/ubuntu/UbuntuMono-Regular.ttf",
]
FONT_PATH = None
for p in FONT_PATHS:
    if os.path.exists(p): FONT_PATH = p; break

def get_font(size=16):
    return ImageFont.truetype(FONT_PATH, size) if FONT_PATH else ImageFont.load_default()

FONT_SM   = get_font(14)
FONT_MD   = get_font(17)
FONT_LG   = get_font(22)
FONT_XL   = get_font(30)
FONT_XXL  = get_font(38)

# ─── HELPERS ────────────────────────────────────────────────────────────────

def make_gradient(w, h, top, bottom):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(h):
        t = y / h
        arr[y] = [int(top[i]*(1-t)+bottom[i]*t) for i in range(3)]
    return Image.fromarray(arr)

def overlay_composite(base, overlay):
    """Composite overlay (RGBA) onto base (RGB)."""
    if base.mode != 'RGBA': base = base.convert('RGBA')
    return Image.alpha_composite(base, overlay).convert('RGB')

def make_grid(w, h, spacing=50, color=(30, 36, 72)):
    img = Image.new("RGBA", (w, h), (0,0,0,0))
    d = ImageDraw.Draw(img)
    for x in range(0, w, spacing): d.line([(x,0),(x,h)], fill=color+(30,), width=1)
    for y in range(0, h, spacing): d.line([(0,y),(w,y)], fill=color+(20,), width=1)
    return img

def vignette(w, h, strength=0.35):
    img = Image.new("RGBA", (w, h), (0,0,0,0))
    d = ImageDraw.Draw(img)
    cx, cy = w//2, h//2
    max_r = max(w, h)//2
    for r in range(max_r, 0, -1):
        a = int(255 * strength * (1 - r/max_r))
        if a > 0: d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(0,0,0,a), width=2)
    return img

def scanlines(w, h, opacity=0.025):
    img = Image.new("RGBA", (w, h), (0,0,0,0))
    d = ImageDraw.Draw(img)
    for y in range(0, h, 3):
        d.line([(0,y),(w,y)], fill=(0,0,0,int(255*opacity)))
    return img

def corner_accents(w, h, color=ACCENT_CYAN, alpha=30, size=20):
    img = Image.new("RGBA", (w, h), (0,0,0,0))
    d = ImageDraw.Draw(img)
    pts = [(15,15), (15+size,15), (15,15+size)]
    d.line([pts[0], pts[1]], fill=color+(alpha,), width=2)
    d.line([pts[0], pts[2]], fill=color+(alpha,), width=2)
    pts = [(w-15,h-15), (w-15-size,h-15), (w-15,h-15-size)]
    d.line([pts[0], pts[1]], fill=color+(alpha,), width=2)
    d.line([pts[0], pts[2]], fill=color+(alpha,), width=2)
    return img

def status_bar(w, h, text_left="NORMAL", text_right="main.ts"):
    img = Image.new("RGBA", (w, h), (0,0,0,0))
    d = ImageDraw.Draw(img)
    d.rectangle([(0,0),(w,24)], fill=BG_MID+(180,))
    d.rectangle([(0,24),(w,25)], fill=ACCENT_CYAN+(50,))
    d.text((10, 4), text_left, font=FONT_SM, fill=TEXT_DIM+(220,))
    d.text((w-10, 4), text_right, font=FONT_SM, fill=TEXT_DIM+(200,), anchor="ra")
    return img

def terminal_box(w, h, x, y, bw, bh, title="", color=ACCENT_CYAN):
    """Draw terminal-style window."""
    img = Image.new("RGBA", (w, h), (0,0,0,0))
    d = ImageDraw.Draw(img)
    # Glass background
    d.rectangle([(x,y),(x+bw,y+bh)], fill=(8,16,38,140))
    # Border
    d.rectangle([(x,y),(x+bw,y+bh)], outline=color+(35,), width=1)
    # Title bar
    d.rectangle([(x+1,y+1),(x+bw-1,y+22)], fill=(10,16,40,200))
    if title:
        d.text((x+8, y+4), title, font=FONT_SM, fill=TEXT_DIM+(220,))
    # Traffic light dots
    for i, c in enumerate([(255,80,80),(255,180,50),(50,200,80)]):
        d.ellipse([(x+bw-22+i*8, y+6), (x+bw-18+i*8, y+10)], fill=c+(200,))
    return img

def text_overlay(w, h, text, x, y, color=TEXT_PRIMARY, font=FONT_MD, anchor="la", alpha=255):
    img = Image.new("RGBA", (w, h), (0,0,0,0))
    d = ImageDraw.Draw(img)
    d.text((x, y), text, font=font, fill=color+(alpha,), anchor=anchor)
    return img

# ─── FRAME GENERATOR ───────────────────────────────────────────────────────

class FrameGenerator:
    def __init__(self):
        self.fn = 0
        self.t = 0.0
        self._bg_image = None

    def _base_frame(self):
        """Create the base dark gradient frame with grid, vignette, scanlines, corners."""
        img = make_gradient(WIDTH, HEIGHT, BG_TOP, BG_BOTTOM)
        img = overlay_composite(img, make_grid(WIDTH, HEIGHT))
        img = overlay_composite(img, vignette(WIDTH, HEIGHT, 0.30))
        img = overlay_composite(img, scanlines(WIDTH, HEIGHT, 0.02))
        img = overlay_composite(img, corner_accents(WIDTH, HEIGHT, alpha=25))
        return img

    def _status(self, left, right):
        return status_bar(WIDTH, HEIGHT, left, right)

    def generate(self, fn):
        self.fn = fn
        self.t = fn / FPS
        t = self.t
        img = self._base_frame()

        if t < 1.8:
            img = self._scene_intro(img)
        elif t < 5.5:
            img = self._scene_old_cmd(img)
        elif t < 7.0:
            img = self._scene_exec_old(img)
        elif t < 8.5:
            img = self._scene_clear(img)
        elif t < 10.8:
            img = self._scene_new_cmd(img)
        elif t < 14.5:
            img = self._scene_ai_process(img)
        elif t < 16.0:
            img = self._scene_result(img)
        elif t < 19.0:
            img = self._scene_final(img)
        else:
            img = self._scene_outro(img)

        return img

    # ─── SCENES ─────────────────────────────────────────────────────────

    def _scene_intro(self, img):
        t = self.t
        fade = min(t / 1.5, 1.0)
        img = overlay_composite(img, self._status("INICIALIZANDO", "pi-agent  ●  v0.1.0"))

        # Center content
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
        d = ImageDraw.Draw(overlay)

        a = int(255 * fade)
        # Big "PI"
        d.text((WIDTH//2, HEIGHT//2 - 50), "PI",
               font=get_font(52), fill=ACCENT_CYAN+(a,), anchor="mm")

        # Animated subtitle
        subtitle = "CODING AGENT"
        n = min(int(t * 10), len(subtitle))
        if n > 0:
            d.text((WIDTH//2, HEIGHT//2 + 15), subtitle[:n],
                   font=FONT_XL, fill=TEXT_PRIMARY+(a,), anchor="mm")
            if n < len(subtitle) and (self.fn % 12) < 6:
                x = WIDTH//2 + len(subtitle[:n])*9 + 25
                d.text((x, HEIGHT//2 + 12), "▌", font=FONT_XL, fill=ACCENT_CYAN+(a,), anchor="mm")

        # Accent line that grows
        progress = min(t * 2, 1.0)
        line_len = int(150 * progress)
        d.line([(WIDTH//2-line_len, HEIGHT//2-20), (WIDTH//2+line_len, HEIGHT//2-20)],
               fill=ACCENT_CYAN+(50,), width=1)

        if t > 1.2:
            d.text((WIDTH//2, HEIGHT-60), "SISTEMA DE ANÁLISIS INTELIGENTE",
                   font=FONT_SM, fill=TEXT_DIM+(int(120*(t-1.2)*3),), anchor="mm")

        return overlay_composite(img, overlay)

    def _draw_terminal(self, img, box_x, box_y, box_w, box_h, title, label_text,
                      prompt, cmd_text, cmd_progress, extra_lines=None):
        """Draw terminal with prompt and command at given progress."""
        img = overlay_composite(img, terminal_box(WIDTH, HEIGHT, box_x, box_y, box_w, box_h, title))
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
        d = ImageDraw.Draw(overlay)

        # Prompt
        d.text((box_x+15, box_y+30), prompt, font=FONT_MD, fill=TEXT_PROMPT+(240,))

        # Command text
        if cmd_text and cmd_progress > 0:
            n = min(cmd_progress, len(cmd_text))
            d.text((box_x+15+len(prompt)*8, box_y+30), cmd_text[:n],
                   font=FONT_MD, fill=TEXT_PRIMARY+(240,))
            if n < len(cmd_text) and (self.fn % 14) < 7:
                cx = box_x+15+len(prompt)*8 + n*8
                d.text((cx, box_y+28), "▌", font=FONT_MD, fill=ACCENT_CYAN+(220,))

        # Extra output lines
        if extra_lines:
            for start_t, y_offset, text, color, alpha_f in extra_lines:
                if self.t >= start_t:
                    a = int(alpha_f * min((self.t-start_t)*4, 1.0))
                    d.text((box_x+20, box_y+y_offset), text, font=FONT_SM, fill=color+(a,))

        # Bottom label
        d.text((WIDTH//2, box_y+box_h+10), label_text,
               font=FONT_SM, fill=TEXT_DIM+(80,), anchor="ma")

        return overlay_composite(img, overlay)

    def _scene_old_cmd(self, img):
        t = self.t
        img = overlay_composite(img, self._status("COMANDO", "bash  ●  tradicional"))

        cmd = 'find . -name "*.ts" -not -path "*/node_modules/*" | xargs wc -l'
        typing_speed = 14
        progress = max(0, int((t - 2.2) * typing_speed))

        extra = []
        if t > 4.8:
            results = [
                (4.8, 58, "  1248  src/components/App.ts", TEXT_PRIMARY, 200),
                (5.1, 78, "  356   src/utils/parser.ts", TEXT_PRIMARY, 200),
                (5.4, 98, "  892   src/services/api.ts", TEXT_PRIMARY, 200),
                (5.7, 118, "  ─────────────────────", TEXT_DIM, 150),
                (6.0, 138, "  2496  total", TEXT_RESULT, 220),
            ]
            extra = [(rt, ry, rt2, rc, ra) for rt, ry, rt2, rc, ra in results]

        return self._draw_terminal(img, 30, 50, WIDTH-60, HEIGHT-110,
            "pi@workspace:~/p3/s52", "MÉTODO TRADICIONAL  •  SHELL",
            "~/workspace $ ", cmd, progress, extra)

    def _scene_exec_old(self, img):
        t = self.t
        img = overlay_composite(img, self._status("PROCESANDO", "bash  ●  ejecutando"))

        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
        d = ImageDraw.Draw(overlay)

        d.text((WIDTH//2, HEIGHT//2 - 40), "PROCESANDO",
               font=FONT_XL, fill=ACCENT_CYAN+(220,), anchor="mm")

        # Spinner
        sp = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        d.text((WIDTH//2-60, HEIGHT//2+5), sp[(self.fn//4)%len(sp)],
               font=FONT_XL, fill=ACCENT_GREEN+(180,), anchor="mm")

        # Progress bar
        prog = min((t-6.5)*2, 1.0)
        bx, by, bw = 200, HEIGHT//2+50, 400
        d.rectangle([(bx,by),(bx+bw,by+4)], fill=(255,255,255,20))
        if prog > 0:
            d.rectangle([(bx,by),(bx+int(bw*prog),by+4)], fill=ACCENT_CYAN+(130,))

        # Scanning line
        sy = int((t-6.5)*100) % HEIGHT
        d.line([(0,sy),(WIDTH,sy)], fill=ACCENT_CYAN+(15,), width=1)

        return overlay_composite(img, overlay)

    def _scene_clear(self, img):
        """Transition: clear screen with visual interest."""
        t = self.t
        img = overlay_composite(img, self._status("LIMPIANDO", "pi-agent  ●  reset"))

        # Much lighter fade - max 80 alpha so never fully black
        fade_progress = min((t-7.0)*2, 1.0)
        fade_alpha = int(80 * fade_progress)  # max 80, not 180
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0, fade_alpha))

        # Show clear command fading out
        if t < 8.0:
            cmd_alpha = int(200 * (1 - fade_progress * 0.7))
            img2 = text_overlay(WIDTH, HEIGHT, "~/workspace $ clear",
                                40, HEIGHT//2-30, TEXT_DIM, FONT_MD, "la", cmd_alpha)
            overlay = Image.alpha_composite(overlay, img2)

        # Spinning indicator
        sp = "◐◓◑◒"
        spinner_alpha = int(150 * (1 - fade_progress * 0.5))
        if spinner_alpha > 0:
            img3 = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
            d3 = ImageDraw.Draw(img3)
            d3.text((WIDTH//2, HEIGHT//2+10), sp[(self.fn//6)%len(sp)],
                    font=FONT_XL, fill=ACCENT_CYAN+(spinner_alpha,), anchor="mm")
            d3.text((WIDTH//2, HEIGHT//2+50), "preparando entorno...",
                    font=FONT_SM, fill=TEXT_DIM+(spinner_alpha,), anchor="mm")
            overlay = Image.alpha_composite(overlay, img3)

        # Horizontal scan line for visual interest
        sy = int(t*50) % HEIGHT
        line = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
        ld = ImageDraw.Draw(line)
        ld.line([(0,sy),(WIDTH,sy)], fill=ACCENT_CYAN+(int(15*(1-fade_progress)),), width=1)
        overlay = Image.alpha_composite(overlay, line)

        return overlay_composite(img, overlay)

    def _scene_new_cmd(self, img):
        t = self.t
        img = overlay_composite(img, self._status("PI ASISTENTE", "pi-agent  ●  online"))

        cmd = 'pi ask "cuántas líneas de TypeScript hay"'
        typing_start = 9.2
        speed = 11
        progress = max(0, int((t - typing_start) * speed))

        return self._draw_terminal(img, 30, 50, WIDTH-60, HEIGHT-110,
            "pi-agent@workspace:~/p3/s52", "MÉTODO PI  •  LENGUAJE NATURAL",
            "~/workspace $ ", cmd, progress, [])

    def _scene_ai_process(self, img):
        t = self.t
        img = overlay_composite(img, self._status("PI ANALIZANDO", "pi-agent  ●  procesando"))

        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
        d = ImageDraw.Draw(overlay)

        box_x, box_y, box_w, box_h = 60, 60, WIDTH-120, HEIGHT-130
        overlay2 = terminal_box(WIDTH, HEIGHT, box_x, box_y, box_w, box_h, "pi-agent  —  análisis")
        overlay = Image.alpha_composite(overlay, overlay2)

        # AI processing lines
        lines_data = [
            (10.8, 38, "●  Conectando con motor de análisis...", TEXT_DIM, 180),
            (11.3, 62, "●  Escaneando estructura del proyecto...", TEXT_DIM, 180),
            (11.8, 86, "●  Analizando dependencias TypeScript...", TEXT_DIM, 180),
            (12.3, 110, "●  Compilando resultados...", TEXT_DIM, 180),
        ]

        for start_t, y_off, text, color, max_a in lines_data:
            if t >= start_t:
                a = int(max_a * min((t-start_t)*3, 1.0))
                d.text((box_x+20, box_y+y_off), text, font=FONT_SM, fill=color+(a,))

        # Show status indicator
        if t > 12.8:
            result_a = int(220 * min((t-12.8)*3, 1.0))
            d.text((box_x+20, box_y+145), "──────────────────────────────",
                   font=FONT_SM, fill=TEXT_DIM+(result_a//2,))
            d.text((box_x+20, box_y+168), "📊  Total: 2,496 líneas TypeScript",
                   font=FONT_MD, fill=TEXT_RESULT+(result_a,))
            d.text((box_x+20, box_y+192), "    Archivos: 47 *.ts",
                   font=FONT_SM, fill=TEXT_PRIMARY+(result_a,))
            d.text((box_x+20, box_y+212), "    Node modules excluidos: ✓",
                   font=FONT_SM, fill=TEXT_PRIMARY+(result_a,))

        # Animated dots on last active line
        if t < 12.8:
            dots = "." * ((self.fn//6) % 4)
            d.text((box_x+360, box_y+110), dots,
                   font=FONT_SM, fill=ACCENT_CYAN+(180,))

        return overlay_composite(img, overlay)

    def _scene_result(self, img):
        t = self.t
        img = overlay_composite(img, self._status("COMPLETADO", "pi-agent  ●  success"))

        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
        d = ImageDraw.Draw(overlay)

        # Large result card
        cx, cy, cw, ch = 100, 50, WIDTH-200, HEIGHT-100
        d.rectangle([(cx,cy),(cx+cw,cy+ch)], fill=(5,12,36,170))
        for i in range(2):
            d.rectangle([(cx-i,cy-i),(cx+cw+i,cy+ch+i)],
                       outline=ACCENT_CYAN+(30-i*10,), width=1)

        # Success checkmark
        sa = int(255 * min((t-14.5)*3, 1.0))
        d.ellipse([(WIDTH//2-18, cy+20), (WIDTH//2+18, cy+56)],
                  outline=ACCENT_GREEN+(sa,), width=2)
        d.text((WIDTH//2, cy+38), "✓", font=FONT_XL, fill=ACCENT_GREEN+(sa,), anchor="mm")

        # Stats
        stats = [("2,496", "líneas"), ("47", "archivos"), ("0", "errores"), ("67%", "eficiencia")]
        sw = (cw-40)//4
        for i, (val, label) in enumerate(stats):
            a = int(255 * min((t-14.8+i*0.12)*4, 1.0))
            sx = cx+20+i*sw
            d.text((sx+sw//2, cy+85), val, font=FONT_XXL, fill=ACCENT_CYAN+(a,), anchor="ma")
            d.text((sx+sw//2, cy+125), label, font=FONT_SM, fill=TEXT_DIM+(a,), anchor="ma")

        # Bottom message
        if t > 15.5:
            a = int(150 * min((t-15.5)*3, 1.0))
            d.text((WIDTH//2, cy+ch-20), "●  Análisis completado  ●",
                   font=FONT_MD, fill=ACCENT_GREEN+(a,), anchor="mm")

        return overlay_composite(img, overlay)

    def _scene_final(self, img):
        t = self.t
        img = overlay_composite(img, self._status("PI TERMINAL", "finale  ●  complete"))

        cmd = 'pi stats --format=json'
        progress = max(0, int((t-16.8) * 12))

        extra_lines = []
        if t > 18.0:
            json_out = [
                (18.0, 60, "  {", TEXT_PRIMARY, 200),
                (18.3, 82, '    "status": "completado",', TEXT_PRIMARY, 200),
                (18.6, 104, '    "proyecto": "p3/s52",', TEXT_PRIMARY, 200),
                (18.9, 126, '    "eficiencia": "+67%"', ACCENT_GREEN, 220),
                (19.2, 148, "  }", TEXT_PRIMARY, 200),
            ]
            extra_lines = [(st, yo, tx, co, al) for st, yo, tx, co, al in json_out]

        return self._draw_terminal(img, 30, 50, WIDTH-60, HEIGHT-110,
            "pi-agent@workspace:~/p3/s52", "RESUMEN  •  JSON",
            "~/workspace $ ", cmd, progress, extra_lines)

    def _scene_outro(self, img):
        t = self.t
        remain = 20.0 - t
        fade = min(remain * 2, 1.0)

        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,0))
        d = ImageDraw.Draw(overlay)

        a = int(200 * fade)
        d.text((WIDTH//2, HEIGHT//2-25), "●  FIN  ●",
               font=FONT_XL, fill=ACCENT_CYAN+(a,), anchor="mm")
        d.text((WIDTH//2, HEIGHT//2+15), "PI CODING AGENT",
               font=FONT_MD, fill=TEXT_PRIMARY+(a//2,), anchor="mm")
        d.text((WIDTH//2, HEIGHT//2+45), "cinematic demo",
               font=FONT_SM, fill=TEXT_DIM+(a//3,), anchor="mm")

        # Fade to black
        ba = int(255 * (1-fade))
        if ba > 0:
            black = Image.new("RGBA", (WIDTH, HEIGHT), (0,0,0,ba))
            overlay = Image.alpha_composite(overlay, black)

        return overlay_composite(img, overlay)


# ─── RENDER ─────────────────────────────────────────────────────────────────

def render_frames():
    print("🎬 Generating frames...")
    gen = FrameGenerator()
    for i in range(TOTAL_FRAMES):
        img = gen.generate(i)
        img.save(os.path.join(OUTPUT_DIR, f"frame_{i:05d}.png"), optimize=True)
        if i % 60 == 0:
            print(f"   {100*i//TOTAL_FRAMES}% ({i}/{TOTAL_FRAMES})")
    print(f"✅ {TOTAL_FRAMES} frames")


# ─── AUDIO ──────────────────────────────────────────────────────────────────

def generate_audio():
    print("🎵 Generating audio...")
    SR = 44100
    N = int(DURATION * SR)
    t = np.arange(N) / SR

    ambient = np.zeros(N, dtype=np.float64)
    foley = np.zeros(N, dtype=np.float64)

    # ─── AMBIENT PAD ────────────────────────────────────────────────────
    # Rich evolving pad
    freqs_bass = [55.0, 65.41, 82.41, 98.0, 110.0, 130.81, 164.81, 196.0]
    lfo = 0.6 + 0.4 * np.sin(2*np.pi*0.06*t)
    lfo2 = 0.7 + 0.3 * np.sin(2*np.pi*0.14*t + 1.0)

    for i, f in enumerate(freqs_bass):
        det = 1.0 + np.random.uniform(-0.003, 0.003)
        amp = 0.025 / (1 + i*0.12)
        wob = 1.0 + 0.002 * np.sin(2*np.pi*0.08*t*(1+i*0.1))
        ambient += np.sin(2*np.pi*f*det*wob*t + np.random.uniform(0,2*np.pi)) * amp * lfo

    # Upper harmonics
    ambient += np.sin(2*np.pi*220*t)*0.01*lfo2
    ambient += np.sin(2*np.pi*329.63*t)*0.008*lfo2
    ambient += np.sin(2*np.pi*440*t)*0.006*lfo
    ambient += np.sin(2*np.pi*523.25*t)*0.004*lfo

    # Noise texture (always present)
    noise = np.random.randn(N)
    box = np.ones(200)/200
    noise_lp = np.convolve(noise, box, mode='same') * 0.02
    ambient += noise_lp + noise * 0.004

    # ─── SCENE EVOLUTION ────────────────────────────────────────────────
    # Build tension in mid section
    mid_env = np.clip((t-6)/3, 0, 1) * np.clip((14-t)/3, 0, 1)
    ambient += mid_env * (np.sin(2*np.pi*130.81*t)*0.02 + np.sin(2*np.pi*261.63*t)*0.012)

    # Resolution in final section
    end_env = np.clip((t-13)/2, 0, 1) * np.clip((20-t)/2, 0, 1)
    ambient += end_env * (np.sin(2*np.pi*392*t)*0.015 + np.sin(2*np.pi*523.25*t)*0.01)

    # Subtle pulse
    pulse = (0.5+0.5*np.sin(2*np.pi*0.5*t))**4
    ambient += pulse * 0.006 * (np.sin(2*np.pi*60*t)*0.5 + np.random.randn(N)*0.3)

    # Room tone and hum
    room = np.convolve(np.random.randn(N), np.ones(80)/80, mode='same') * 0.005
    ambient += room + np.sin(2*np.pi*60*t)*0.004 + np.sin(2*np.pi*120*t)*0.002

    # ─── KEYBOARD FOLEY ─────────────────────────────────────────────────
    def make_click(sr, dur=0.035, intensity=1.0):
        n = int(sr*dur)
        env = np.exp(-np.arange(n)*60/n)
        click = np.random.randn(n)*env*intensity*0.5
        thump = np.sin(2*np.pi*1200*np.arange(n)/sr)*env*intensity*0.35
        bottom = np.sin(2*np.pi*200*np.arange(n)/sr)*env*intensity*0.25
        return click+thump+bottom

    def make_enter(sr, dur=0.15, intensity=1.0):
        n = int(sr*dur)
        env = np.exp(-np.arange(n)*20/n)
        click = np.random.randn(n)*env*intensity*0.3
        thump = np.sin(2*np.pi*350*np.arange(n)/sr)*env*intensity*0.6
        deep = np.sin(2*np.pi*55*np.arange(n)/sr)*env*intensity*0.4
        slide = np.sin(2*np.pi*(800+600*np.arange(n)/n)*np.arange(n)/sr)*env*intensity*0.25
        return click+thump+deep+slide

    def add_typing(cmd, start, speed=10, ir=(0.4, 0.85)):
        events = []
        for i, ch in enumerate(cmd):
            ct = start + i/speed + np.random.uniform(-0.01, 0.02)
            intensity = ir[0] + (ir[1]-ir[0])*np.random.random()
            if ch.isupper() or ch in '$@!#%^&*()': intensity = min(intensity*1.3, 1.0)
            if ch in '.,;:': intensity *= 0.7
            events.append((ct, 'click', intensity))
        return events

    events = []
    events += add_typing('find . -name "*.ts" -not -path "*/node_modules/*" | xargs wc -l 2>/dev/null', 2.5, 12, (0.5, 0.9))
    events += [(5.0, 'enter', 0.85)]
    events += add_typing('clear', 7.5, 8, (0.3, 0.6))
    events += [(7.9, 'enter', 0.6)]
    events += add_typing('pi ask "cuántas líneas de TypeScript hay"', 9.2, 11, (0.4, 0.85))
    events += [(10.7, 'enter', 0.85)]
    events += add_typing('pi stats --format=json', 16.8, 12, (0.4, 0.8))
    events += [(18.3, 'enter', 0.8)]

    for ct, ctype, intensity in events:
        if ct < 0 or ct > DURATION: continue
        si = int(ct*SR)
        if si >= N: continue
        snd = make_enter(SR, 0.15, intensity) if ctype == 'enter' else make_click(SR, 0.03+0.02*intensity, intensity)
        ei = min(si+len(snd), N)
        foley[si:ei] += snd[:ei-si]

    # ─── MIX ─────────────────────────────────────────────────────────────
    # Normalize
    ar = np.sqrt(np.mean(ambient**2))
    if ar > 0: ambient *= 0.10 / ar
    fr = np.sqrt(np.mean(foley**2))
    if fr > 0: foley *= 0.06 / fr

    master = ambient + foley
    mx = np.max(np.abs(master))
    if mx > 0.9: master *= 0.9/mx
    master = np.clip(master, -1.0, 1.0)

    # Fade
    fl = int(SR*1.0)
    master[:fl] *= np.linspace(0,1,fl)
    master[-fl:] *= np.linspace(1,0,fl)

    # Write
    data = (master * 30000).astype(np.int16)
    stereo = np.column_stack([data, data]).flatten().astype(np.int16)
    with wave.open(FINAL_AUDIO, 'w') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())
    print(f"✅ Audio: {FINAL_AUDIO}")
    return FINAL_AUDIO


# ─── ASSEMBLE ───────────────────────────────────────────────────────────────

def assemble_video():
    print("🎬 Assembling video...")
    from moviepy import ImageSequenceClip, AudioFileClip

    frames = [os.path.join(OUTPUT_DIR, f"frame_{i:05d}.png") for i in range(TOTAL_FRAMES)]
    clip = ImageSequenceClip(frames, fps=FPS)
    clip = clip.with_audio(AudioFileClip(FINAL_AUDIO))

    clip.write_videofile(FINAL_VIDEO, codec="libx264", audio_codec="aac",
                         fps=FPS, preset="medium", bitrate="6000k",
                         audio_bitrate="192k", threads=4,
                         ffmpeg_params=["-pix_fmt","yuv420p","-profile:v","high"],
                         logger="bar")
    print(f"✅ Video: {FINAL_VIDEO}")


if __name__ == "__main__":
    print("=" * 55)
    print("  PREMIUM CINEMATIC CODING INTERFACE VIDEO")
    print("  Generator v2.0")
    print("=" * 55)
    render_frames()
    generate_audio()
    assemble_video()
    print(f"\n  🎥 {FINAL_VIDEO}")
    print(f"  ⏱  {DURATION}s | {WIDTH}x{HEIGHT} @ {FPS}fps")
    print("=" * 55)
