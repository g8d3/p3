#!/usr/bin/env python3
"""
Render REAL asciinema terminal recording + TTS narration to video.

Strategy: terminal recording is ~9s, TTS is ~92s.
We show the terminal evolution in the first 9s, then freeze
on the final state while narration continues.
"""
import json
import os
import re
import subprocess
import textwrap
from PIL import Image, ImageDraw, ImageFont

CAST = "/tmp/a2a-real-demo.cast"
TTS_DIR = "/tmp/a2a-demo-tts"
OUT_DIR = "/tmp/a2a-real-video"
os.makedirs(OUT_DIR, exist_ok=True)

W, H = 1280, 720
COLS, ROWS = 65, 12
CW, CH = 10, 20
TX = (W - COLS * CW) // 2
TY = (H - ROWS * CH) // 2

FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
FONT_TITLE = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
FONT_SMALL = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
FONT_WRAP = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)

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

    # Title
    draw.rectangle([(0,0),(W,38)], fill=(0,35,70))
    draw.text((15,9), "A2A Protocol Test — Real Terminal", font=FONT_TITLE, fill=(180,210,255))

    # Terminal bg
    draw.rectangle([(TX-8,TY-8),(TX+COLS*CW+8,TY+ROWS*CH+8)], fill=(0,0,0), outline=(50,50,70))

    # Lines
    for ri, line in enumerate(buf[-ROWS:]):
        clean = strip_ansi(line)[:COLS]
        if '\r' in clean:
            clean = clean.split('\r')[-1]
        draw.text((TX, TY + ri*CH), clean, font=FONT, fill=(170,255,170))

    # Annotation bar
    if annotation:
        draw.rectangle([(0,H-45),(W,H)], fill=(0,25,55))
        ann = annotation[:130]
        draw.text((15, H-32), ann, font=FONT_WRAP, fill=(255,210,80))

    return img


def main():
    hdr, evts = parse_cast(CAST)
    cast_dur = evts[-1][0]

    # TTS durations
    tts_files = [os.path.join(TTS_DIR, f"step{i:02d}.mp3") for i in range(1, 6)]
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

    step_labels = [
        "Step 1/5: Agent Discovery",
        "Step 2/5: Task Execution",
        "Step 3/5: Cancellation",
        "Step 4/5: ❌ Quality Gap", 
        "Step 5/5: A2A-Q Solution",
    ]
    step_anns = [
        "Agent Cards at .well-known/agent.json — capabilities described, but NO quality criteria",
        "POST /message:send → Task lifecycle: submitted → working → completed",
        "POST /tasks/{id}:cancel → race condition found and fixed",
        "Good code and buggy code both return state=completed — protocol can't distinguish quality",
        "A2A-Q adds: pending-review, needs-revision, quality-passed + efficacy/efficiency metrics",
    ]

    fdir = os.path.join(OUT_DIR, "frames")
    os.makedirs(fdir, exist_ok=True)

    # Replay terminal events
    buf = [""] * ROWS
    last_frame_buf = None

    evt_i = 0
    freeze_after = cast_dur  # freeze after cast ends
    final_buf = None

    print(f"Recording: {cast_dur:.1f}s, TTS: {total_t:.1f}s, Frames: {nframes}")

    for fi in range(nframes):
        t = fi / fps

        # Process events (only during cast duration)
        if t <= cast_dur:
            while evt_i < len(evts) and evts[evt_i][0] <= t:
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
            final_buf = buf.copy()

        # Determine step from time
        cum = 0
        si = 0
        for i, d in enumerate(tts_durs):
            if t < cum + d:
                si = i
                break
            cum += d

        # Use frozen buffer after cast
        render_buf = buf if t <= cast_dur else (final_buf or buf)
        ann = f"{step_labels[si]}: {step_anns[si]}"
        img = render(render_buf, ann)
        img.save(os.path.join(fdir, f"f{fi:06d}.png"))

        if fi % 100 == 0:
            print(f"  Frame {fi}/{nframes}")

    # Build video
    print("\nConcatenating audio...")
    audio_list = os.path.join(OUT_DIR, "audio.txt")
    with open(audio_list, "w") as f:
        for af in tts_files:
            if os.path.exists(af):
                f.write(f"file '{af}'\n")

    audio_all = os.path.join(OUT_DIR, "narration.mp3")
    subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",audio_list,"-c","copy",audio_all],
        capture_output=True, timeout=30)

    print("Rendering final video...")
    vout = os.path.join(OUT_DIR, "a2a-real-demo.mp4")
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
    print(f"   Size: {sz:.1f} MB")
    print(f"   Duration: {dur:.1f}s")
    print(f"   Frames: {nframes}")
    print(f"   Terminal recording: {cast_dur:.1f}s (then frozen)")


if __name__ == "__main__":
    main()
