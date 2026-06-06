#!/usr/bin/env python3
"""Render A2A demo: split-screen (terminal + summary) for YouTube (H) and TikTok (V)."""
import json, os, re, subprocess, textwrap
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
WD = os.path.join(BASE, "workdir")
CAST = os.path.join(WD, "final-v2.cast")
TTS = os.path.join(WD, "tts-v4")

FONT_M = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
FONT_S = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
FONT_T = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
FONT_B = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)

def strip_ansi(t):
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]|\x1b\][^\x1b]*\x1b\\|\x1b[^[\]A-Za-z]', '', t)

def parse_cast(path):
    with open(path) as f:
        hdr = json.loads(f.readline())
        evts = []
        for line in f:
            ts, et, d = json.loads(line)
            evts.append((ts, et, d))
    return hdr, evts

# Step data: (title, lines_for_summary)
STEPS = [
    ("Intro", [("Setup", "gray")]),
    ("Descubrimiento", [
        ("GET /.well-known/agent.json", "white"),
        ("Alpha: Alpha-Generalist", "green"),
        ("Beta: Beta-Quality", "green"),
        ("Skills OK — calidad NO", "yellow"),
    ]),
    ("Ejecución", [
        ("POST /message:send", "white"),
        ("GET /tasks/{id}", "white"),
        ("→ Estado: completed", "green"),
        ("✅ Ciclo A2A funciona", "green"),
    ]),
    ("Cancelación", [
        ("Cancelación en acción", "white"),
        ("→ Respuesta: 404", "red"),
        ("⚠️ Bug real encontrado", "yellow"),
        ("(procesador seguía vivo)", "gray"),
    ]),
    ("Problema de Calidad", [
        ("Código BUENO → completed", "green"),
        ("Código ERROR → completed", "green"),
        ("❌ MISMO ESTADO", "red"),
        ("A2A no distingue calidad", "red"),
    ]),
    ("Solución A2A-Q", [
        ("Estados: pending-review", "cyan"),
        ("needs-revision, passed", "cyan"),
        ("Operaciones: requestReview", "cyan"),
        ("Métricas: score, tokens, CPU", "cyan"),
        ("RFC listo en GitHub", "yellow"),
    ]),
    ("Final", [
        ("💻 Código: s84/a2a_test/", "white"),
        ("🌐 github.com/g8d3/p3", "white"),
        ("📄 RFC: A2A-Q-RFC.md", "white"),
        ("PRóximo: implementar A2A-Q", "yellow"),
    ]),
]
COLORS = {"white":(220,220,220),"green":(0,220,0),"red":(255,80,80),
          "yellow":(255,220,80),"cyan":(80,220,255),"gray":(120,120,120),
          "title":(0,200,255)}

def get_step_at(t, tts_durs):
    cum=0
    for i,d in enumerate(tts_durs):
        if t<cum+d: return i
        cum+=d
    return len(tts_durs)-1

def render_horizontal(lines, step_idx, progress, t_cum):
    """1920x1080: terminal left 65%, summary right 35%"""
    W,H = 1920, 1080
    img = Image.new("RGB", (W,H), (15,15,25))
    draw = ImageDraw.Draw(img)
    tw = int(W*0.62)
    sw = W-tw-2

    # Terminal area (left)
    draw.rectangle([(0,40),(tw,H-1)], fill=(8,8,8))
    y=45
    term_cols = tw//10
    for line in lines[-38:]:
        clean = strip_ansi(line)[:term_cols]
        if '\r' in clean: clean=clean.split('\r')[-1]
        draw.text((6,y), clean, font=FONT_M, fill=(0,220,0))
        y+=18

    # Summary panel (right)
    sx=tw+20
    draw.rectangle([(tw,40),(W-1,H-1)], fill=(18,18,35))
    # Step title
    title = STEPS[min(step_idx, len(STEPS)-1)][0]
    draw.text((sx,55), f"■ {title}", font=FONT_T, fill=COLORS["title"])
    draw.line([(sx,85),(W-20,85)], fill=(40,40,60))

    # Step number
    draw.text((sx,95), f"Paso {step_idx+1}/7", font=FONT_B, fill=(100,100,120))

    # Summary lines
    yy=125
    step_data = STEPS[min(step_idx, len(STEPS)-1)][1]
    for text,color in step_data:
        c = COLORS.get(color, (200,200,200))
        draw.text((sx,yy), f"▸ {text}", font=FONT_S, fill=c)
        yy+=28

    # Timer at bottom right
    if t_cum >= 0:
        draw.text((sx, H-50), f"⏱ {t_cum:.0f}s", font=FONT_B, fill=(80,80,100))
        draw.rectangle([(sx,H-70),(W-20,H-70+6)], fill=(30,30,50))
        bar_w = (W-20-sx) * progress
        draw.rectangle([(sx,H-70),(sx+int(bar_w),H-70+6)], fill=(0,200,255))

    # Top bar
    draw.rectangle([(0,0),(W,38)], fill=(0,40,80))
    draw.text((15,8), "A2A Protocol Test — Demo en Vivo", font=FONT_T, fill=(180,210,255))

    return img

def render_vertical(lines, step_idx, progress, t_cum):
    """1080x1920: terminal top 40%, summary bottom 60%"""
    W,H = 1080, 1920
    img = Image.new("RGB", (W,H), (15,15,25))
    draw = ImageDraw.Draw(img)
    term_h = int(H*0.42)
    sum_h = H-term_h-40

    # Top bar
    draw.rectangle([(0,0),(W,38)], fill=(0,40,80))
    draw.text((10,8), "A2A Demo — Terminal Real", font=FONT_T, fill=(180,210,255))

    # Terminal area
    draw.rectangle([(0,40),(W,40+term_h)], fill=(8,8,8))
    y=45
    term_cols = W//10
    rows = term_h//18
    for line in lines[-rows:]:
        clean = strip_ansi(line)[:term_cols]
        if '\r' in clean: clean=clean.split('\r')[-1]
        draw.text((4,y), clean, font=FONT_M, fill=(0,220,0))
        y+=18

    # Summary panel
    sy = 45+term_h
    draw.rectangle([(0,sy),(W,H-1)], fill=(18,18,35))

    title = STEPS[min(step_idx, len(STEPS)-1)][0]
    draw.text((25,sy+10), f"■ {title}", font=FONT_T, fill=COLORS["title"])
    draw.line([(25,sy+45),(W-25,sy+45)], fill=(40,40,60))
    draw.text((25,sy+55), f"Paso {step_idx+1}/7", font=FONT_B, fill=(100,100,120))

    yy=sy+85
    step_data = STEPS[min(step_idx, len(STEPS)-1)][1]
    for text,color in step_data:
        c = COLORS.get(color, (200,200,200))
        draw.text((25,yy), f"▸ {text}", font=FONT_S, fill=c)
        yy+=36

    # Progress bar
    if t_cum >= 0:
        bar_y = H-30
        draw.text((25, bar_y-18), f"⏱ {t_cum:.0f}s / {progress*100:.0f}%", font=FONT_B, fill=(80,80,100))
        draw.rectangle([(25,bar_y),(W-25,bar_y+6)], fill=(30,30,50))
        bar_w = (W-50) * progress
        draw.rectangle([(25,bar_y),(25+int(bar_w),bar_y+6)], fill=(0,200,255))

    return img

def main():
    hdr, evts = parse_cast(CAST)
    cast_dur = evts[-1][0]

    tts_files = [os.path.join(TTS, f"c{i}.mp3") for i in range(1,8)]
    tts_durs = []
    for f in tts_files:
        if os.path.exists(f) and os.path.getsize(f)>0:
            r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f],
                capture_output=True,text=True,timeout=10)
            tts_durs.append(float(r.stdout.strip() or 5))
        else:
            tts_durs.append(5)

    total_t = sum(tts_durs)
    cast_scale = total_t / cast_dur if cast_dur > 0 else 1

    # Mobile vertical only: 1080x1920
    OUT = os.path.join(BASE, "demo", "a2a-demo-mobile.mp4")
    fps = 10
    nframes = int(total_t * fps)
    fdir = os.path.join(WD, "frames_mobile")
    os.makedirs(fdir, exist_ok=True)

    buf = [""]*50
    evt_i = 0
    frozen = None

    print(f"Rendering mobile ({nframes} frames)...")

    for fi in range(nframes):
        t = fi / fps
        cast_t = min(t / cast_scale, cast_dur)

        while evt_i < len(evts) and evts[evt_i][0] <= cast_t:
            _, et, data = evts[evt_i]
            if et == "o":
                txt = data
                while '\n' in txt:
                    idx = txt.index('\n')
                    buf.append(txt[:idx].rstrip('\r'))
                    txt = txt[idx+1:]
                if txt:
                    buf[-1] += txt.rstrip('\r')
                buf = buf[-120:]
            evt_i += 1

        if cast_t >= cast_dur and frozen is None:
            frozen = buf.copy()
        display = frozen if cast_t >= cast_dur and frozen else buf

        si = get_step_at(t, tts_durs)
        progress = t/total_t

        img = render_vertical(display, si, progress, t)
        img.save(os.path.join(fdir, f"f{fi:06d}.png"))

        if fi % 150 == 0:
            print(f"  {fi}/{nframes}")

    # Audio concat
    audio_list = os.path.join(WD, "audio_mobile.txt")
    with open(audio_list,"w") as f:
        for af in tts_files:
            if os.path.exists(af) and os.path.getsize(af)>0:
                f.write(f"file '{af}'\n")
    audio_all = os.path.join(WD, "narracion_mobile.mp3")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",audio_list,"-c","copy",audio_all],
        capture_output=True, timeout=30)

    # Video
    subprocess.run([
        "ffmpeg","-y","-framerate",str(fps),
        "-i", f"{fdir}/f%06d.png",
        "-i", audio_all,
        "-c:v","libx264","-preset","fast","-crf","28",
        "-c:a","aac","-pix_fmt","yuv420p","-shortest",
        OUT
    ], capture_output=True, timeout=300)

    sz = os.path.getsize(OUT)/1e6
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",OUT],
        capture_output=True,text=True,timeout=10)
    dur = float(r.stdout.strip() or 0)
    print(f"\n✅ {OUT}")
    print(f"   {sz:.1f} MB, {dur:.1f}s")

if __name__ == "__main__":
    main()
