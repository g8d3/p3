#!/usr/bin/env python3
"""Render Spanish A2A demo: asciinema terminal + ES-CO TTS to video."""
import json, os, re, subprocess, textwrap
from PIL import Image, ImageDraw, ImageFont

CAST = "/tmp/es-recording.cast"
TTS_DIR = "/tmp/es-tts"
OUT_DIR = "/tmp/es-video"
os.makedirs(OUT_DIR, exist_ok=True)

W, H = 1280, 720
COLS, ROWS = 65, 12
CW, CH = 10, 20
TX = (W - COLS * CW) // 2
TY = (H - ROWS * CH) // 2

FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
FONT_T = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
FONT_S = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)

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

def render(buf, annotation=""):
    img = Image.new("RGB", (W, H), (18, 18, 32))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0,0),(W,38)], fill=(0,35,70))
    draw.text((15,9), "Demo A2A — Terminal Real", font=FONT_T, fill=(180,210,255))
    draw.rectangle([(TX-8,TY-8),(TX+COLS*CW+8,TY+ROWS*CH+8)], fill=(0,0,0), outline=(50,50,70))
    for ri, line in enumerate(buf[-ROWS:]):
        clean = strip_ansi(line)[:COLS]
        if '\r' in clean: clean = clean.split('\r')[-1]
        draw.text((TX, TY + ri*CH), clean, font=FONT, fill=(170,255,170))
    if annotation:
        draw.rectangle([(0,H-45),(W,H)], fill=(0,25,55))
        draw.text((15, H-32), annotation[:130], font=FONT_S, fill=(255,210,80))
    return img

def main():
    hdr, evts = parse_cast(CAST)
    cast_dur = evts[-1][0]

    tts_files = [os.path.join(TTS_DIR, f"paso{i}.mp3") for i in range(1,6)]
    tts_durs = []
    for f in tts_files:
        if os.path.exists(f):
            r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f],
                capture_output=True,text=True,timeout=10)
            tts_durs.append(float(r.stdout.strip() or 5))
        else:
            tts_durs.append(5)

    total_t = sum(tts_durs)
    fps = 10
    nframes = int(total_t * fps)
    scale = total_t / cast_dur  # stretch factor

    labels = ["Paso 1/5: Descubrimiento", "Paso 2/5: Ejecución", "Paso 3/5: Cancelación",
              "Paso 4/5: ❌ Sin calidad", "Paso 5/5: Solución A2A-Q"]
    anns = [
        "Tarjetas de agente en .well-known/agent.json — describen capacidades pero NO calidad",
        "POST /message:send → ciclo: submitted → working → completed",
        "POST /tasks/{id}:cancel → cancelación funciona (bug corregido)",
        "Código bueno y con error → ambos devuelven 'completed' — el protocolo no distingue calidad",
        "A2A-Q agrega: pending-review, needs-revision, quality-passed + métricas",
    ]

    fdir = os.path.join(OUT_DIR, "frames")
    os.makedirs(fdir, exist_ok=True)

    buf = [""] * ROWS
    evt_i = 0
    final_buf = None

    for fi in range(nframes):
        t = fi / fps
        # Map video time to cast time (stretch)
        cast_t = min(t / scale, cast_dur)

        while evt_i < len(evts) and evts[evt_i][0] <= cast_t:
            _, et, data = evts[evt_i]
            if et == "o":
                txt = data
                while '\n' in txt:
                    idx = txt.index('\n')
                    buf.append(txt[:idx])
                    txt = txt[idx+1:]
                if txt:
                    buf[-1] += txt
                buf = buf[-ROWS*2:]
            evt_i += 1
        if cast_t >= cast_dur:
            if final_buf is None:
                final_buf = buf.copy()
        else:
            final_buf = buf.copy()

        cum = 0; si = 0
        for i, d in enumerate(tts_durs):
            if t < cum + d: si = i; break
            cum += d

        ann = f"{labels[si]}: {anns[si]}"
        img = render(final_buf or buf, ann)
        img.save(os.path.join(fdir, f"f{fi:06d}.png"))
        if fi % 100 == 0:
            print(f"  Frame {fi}/{nframes}")

    print("\nConcatenando audio...")
    audio_list = os.path.join(OUT_DIR, "audio.txt")
    with open(audio_list, "w") as f:
        for af in tts_files: f.write(f"file '{af}'\n")
    audio_all = os.path.join(OUT_DIR, "narracion.mp3")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",audio_list,"-c","copy",audio_all],
        capture_output=True, timeout=30)

    print("Renderizando video...")
    vout = os.path.join(OUT_DIR, "a2a-demo-es.mp4")
    subprocess.run([
        "ffmpeg","-y","-framerate",str(fps),
        "-i", f"{fdir}/f%06d.png",
        "-i", audio_all,
        "-c:v","libx264","-preset","fast","-crf","28",
        "-c:a","aac","-pix_fmt","yuv420p","-shortest",
        vout
    ], capture_output=True, timeout=180)

    sz = os.path.getsize(vout)/1e6
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",vout],
        capture_output=True,text=True,timeout=10)
    dur = float(r.stdout.strip() or 0)
    print(f"\n✅ {vout}")
    print(f"   Tamaño: {sz:.1f} MB, Duración: {dur:.1f}s")
    print(f"   Grabación terminal: {cast_dur:.1f}s (estirada x{scale:.1f})")

if __name__ == "__main__":
    main()
