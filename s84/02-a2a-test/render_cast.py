#!/usr/bin/env python3
"""Render asciinema cast to MP4 — terminal a PANTALLA COMPLETA + audio sincronizado."""
import json, os, re, subprocess
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
CAST = os.path.join(BASE, "demo", "final-v2.cast")
TTS_DIR = os.path.join(BASE, "demo", "tts-v4")
OUT = os.path.join(BASE, "demo", "a2a-demo.mp4")

# 1920x1080, terminal fills ENTIRE screen
W, H = 1920, 1080
# Font grande: 22px → ~13px de ancho, ~150 cols, ~50 rows
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 22)
COLS = W // 13
ROWS = H // 28

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

def render(lines):
    img = Image.new("RGB", (W, H), (8, 8, 8))
    draw = ImageDraw.Draw(img)
    y = 4
    for line in lines[-ROWS:]:
        clean = strip_ansi(line)[:COLS]
        if '\r' in clean:
            clean = clean.split('\r')[-1]
        draw.text((6, y), clean, font=FONT, fill=(0, 230, 0))
        y += 28
    return img

def main():
    hdr, evts = parse_cast(CAST)
    cast_dur = evts[-1][0]

    tts_files = [os.path.join(TTS_DIR, f"c{i}.mp3") for i in range(1, 8)]
    tts_durs = []
    for f in tts_files:
        if os.path.exists(f) and os.path.getsize(f) > 0:
            r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f],
                capture_output=True,text=True,timeout=10)
            tts_durs.append(float(r.stdout.strip() or 5))
        else:
            tts_durs.append(5)

    total_t = sum(tts_durs)
    cast_scale = total_t / cast_dur if cast_dur > 0 else 1

    fps = 10
    nframes = int(total_t * fps)
    fdir = os.path.join(BASE, "demo", "_frames")
    os.makedirs(fdir, exist_ok=True)

    buf = [""] * 50
    evt_i = 0
    frozen = None

    print(f"Renderizando {nframes} frames...")

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
                buf = buf[-150:]
            evt_i += 1

        if cast_t >= cast_dur and frozen is None:
            frozen = buf.copy()
        display = frozen if cast_t >= cast_dur and frozen else buf

        render(display).save(os.path.join(fdir, f"f{fi:06d}.png"))
        if fi % 200 == 0:
            print(f"  {fi}/{nframes}")

    print("Concatenando audio...")
    audio_list = os.path.join(BASE, "demo", "_audio.txt")
    with open(audio_list, "w") as f:
        for af in tts_files:
            if os.path.exists(af) and os.path.getsize(af) > 0:
                f.write(f"file '{af}'\n")
    audio_all = os.path.join(BASE, "demo", "_audio.mp3")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",audio_list,"-c","copy",audio_all],
        capture_output=True, timeout=30)

    print("Creando video...")
    subprocess.run([
        "ffmpeg","-y","-framerate",str(fps),
        "-i", f"{fdir}/f%06d.png",
        "-i", audio_all,
        "-c:v","libx264","-preset","fast","-crf","28",
        "-c:a","aac","-pix_fmt","yuv420p","-shortest",
        OUT
    ], capture_output=True, timeout=300)

    # Cleanup frames
    for f in os.listdir(fdir):
        os.remove(os.path.join(fdir, f))
    os.rmdir(fdir)
    os.remove(audio_list)
    os.remove(audio_all)

    sz = os.path.getsize(OUT)/1e6
    print(f"\n✅ {OUT}")
    print(f"   {sz:.1f} MB, {total_t:.0f}s")
    print(f"   Terminal: {COLS}x{ROWS} (22px font, 1920x1080)")

if __name__ == "__main__":
    main()
