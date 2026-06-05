#!/usr/bin/env python3
"""Render FINAL v3: full-screen terminal + reactive Spanish narration + monitor."""
import json, os, re, subprocess
from PIL import Image, ImageDraw, ImageFont

CAST = "/tmp/final-v2.cast"
TTS_DIR = "/tmp/tts-v4"
OUT_DIR = "/tmp/final-v3"
os.makedirs(OUT_DIR, exist_ok=True)

W, H = 1280, 720
COLS = int(W / 9.5)
ROWS = int(H / 19)
FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 13)

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
    # Terminal background
    img = Image.new("RGB", (W, H), (10, 10, 10))
    draw = ImageDraw.Draw(img)
    y = 2
    # Draw ~4px green bar at top as "chrome"
    draw.rectangle([(0,0),(W,4)], fill=(0,80,0))
    # Draw lines
    for line in lines[-ROWS:]:
        clean = strip_ansi(line)[:COLS]
        if '\r' in clean:
            clean = clean.split('\r')[-1]
        draw.text((4, y), clean, font=FONT, fill=(0, 220, 0))
        y += 19
    return img

def main():
    hdr, evts = parse_cast(CAST)
    cast_dur = evts[-1][0]

    tts_files = [os.path.join(TTS_DIR, f"c{i}.mp3") for i in range(1,8)]
    tts_durs = []
    for f in tts_files:
        if os.path.exists(f) and os.path.getsize(f) > 0:
            r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f],
                capture_output=True,text=True,timeout=10)
            tts_durs.append(float(r.stdout.strip() or 5))
        else:
            tts_durs.append(5)

    total_t = sum(tts_durs)
    fps = 10
    nframes = int(total_t * fps)
    scale = total_t / cast_dur if cast_dur > 0 else 1

    fdir = os.path.join(OUT_DIR, "frames")
    os.makedirs(fdir, exist_ok=True)

    buf = [""] * ROWS
    evt_i = 0
    frozen = None

    for fi in range(nframes):
        t = fi / fps
        cast_t = min(t / scale, cast_dur)

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
                buf = buf[-ROWS*2:]
            evt_i += 1

        if cast_t >= cast_dur and frozen is None:
            frozen = buf.copy()

        display = frozen if cast_t >= cast_dur and frozen else buf

        img = render_frame(display)
        img.save(os.path.join(fdir, f"f{fi:06d}.png"))
        if fi % 150 == 0:
            print(f"  Frame {fi}/{nframes}")

    print("Audio...")
    audio_list = os.path.join(OUT_DIR, "audio.txt")
    with open(audio_list, "w") as f:
        for af in tts_files:
            if os.path.exists(af) and os.path.getsize(af) > 0:
                f.write(f"file '{af}'\n")
    audio_all = os.path.join(OUT_DIR, "narracion.mp3")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",audio_list,"-c","copy",audio_all],
        capture_output=True, timeout=30)

    print("Video...")
    vout = os.path.join(OUT_DIR, "a2a-demo-v3.mp4")
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
    print(f"   Size: {sz:.1f} MB, Duration: {dur:.1f}s, Terminal: {COLS}x{ROWS}")

if __name__ == "__main__":
    main()
