#!/usr/bin/env python3
"""Render FINAL A2A demo: full-screen terminal + reactive Spanish narration."""
import json, os, re, subprocess
from PIL import Image, ImageDraw, ImageFont

CAST = "/tmp/final-recording.cast"
TTS_DIR = "/tmp/final-tts"
OUT_DIR = "/tmp/final-video"
os.makedirs(OUT_DIR, exist_ok=True)

# Full screen terminal — NO borders, NO title, NO annotations
W, H = 1280, 720
COLS = int(W / 10)  # ~128 chars wide
ROWS = int(H / 20)  # ~36 rows tall
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)

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

def render_frame(lines):
    """Full-screen terminal: black bg, green text, NO borders or chrome."""
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    y = 0
    for line in lines[-ROWS:]:
        clean = strip_ansi(line)[:COLS]
        if '\r' in clean:
            clean = clean.split('\r')[-1]
        draw.text((5, y), clean, font=FONT, fill=(0, 255, 0))
        y += 20
    return img

def main():
    hdr, evts = parse_cast(CAST)
    cast_dur = evts[-1][0]

    tts_files = [os.path.join(TTS_DIR, f"paso{i}.mp3") for i in range(1,6)]
    tts_durs = []
    for f in tts_files:
        if os.path.exists(f) and os.path.getsize(f) > 0:
            r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f],
                capture_output=True,text=True,timeout=10)
            tts_durs.append(float(r.stdout.strip() or 5))
        else:
            print(f"  ⚠️  Missing: {f}")
            tts_durs.append(5)

    total_t = sum(tts_durs)
    fps = 10
    nframes = int(total_t * fps)
    scale = total_t / cast_dur if cast_dur > 0 else 1

    fdir = os.path.join(OUT_DIR, "frames")
    os.makedirs(fdir, exist_ok=True)

    buf = [""] * ROWS
    evt_i = 0
    frozen = [""] * ROWS

    for fi in range(nframes):
        t = fi / fps
        cast_t = min(t / scale, cast_dur)

        while evt_i < len(evts) and evts[evt_i][0] <= cast_t:
            _, et, data = evts[evt_i]
            if et == "o":
                txt = data
                while '\n' in txt:
                    idx = txt.index('\n')
                    line = txt[:idx].rstrip('\r')
                    buf.append(line)
                    txt = txt[idx+1:]
                if txt:
                    buf[-1] += txt.rstrip('\r')
                buf = buf[-ROWS*2:]
            evt_i += 1

        display = buf if cast_t < cast_dur else frozen
        if cast_t >= cast_dur and not any(frozen):
            frozen = buf.copy()

        img = render_frame(display)
        img.save(os.path.join(fdir, f"f{fi:06d}.png"))
        if fi % 100 == 0:
            print(f"  Frame {fi}/{nframes} (t={t:.0f}s)")

    print("\nConcatenando audio...")
    audio_list = os.path.join(OUT_DIR, "audio.txt")
    with open(audio_list, "w") as f:
        for af in tts_files:
            if os.path.exists(af) and os.path.getsize(af) > 0:
                f.write(f"file '{af}'\n")

    audio_all = os.path.join(OUT_DIR, "narracion.mp3")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",audio_list,"-c","copy",audio_all],
        capture_output=True, timeout=30)

    print("Renderizando video final...")
    vout = os.path.join(OUT_DIR, "a2a-demo-final.mp4")
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
    print(f"   Terminal a pantalla completa ({COLS}x{ROWS})")

if __name__ == "__main__":
    main()
