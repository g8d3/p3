#!/usr/bin/env python3
"""Generate remaining clips with minimal complexity for speed."""

import subprocess
import os

BASE = "/home/vuos/code/p3/s51"
CLIPS_DIR = f"{BASE}/output/clips"
AUDIO_DIR = f"{BASE}/output/audio"

# Missing clips to generate
# escena1_b1, escena5_b1-b4, escena6_b1-b4
missing = [
    # (esc_id, desc, dur, c1, c2, style, prefix, label, particles)
    (1, "Big Bang", 8, "ff4500", "ff8c00", "realista", "b1", "Wan2.2 Realista", 8),
    (5, "Tierra", 8, "0d47a1", "4fc3f7", "realista", "b1", "Wan2.2 Realista", 6),
    (5, "Tierra", 8, "0d47a1", "4fc3f7", "cinematic", "b2", "HunyuanVideo Cinematic", 6),
    (5, "Tierra", 8, "0d47a1", "4fc3f7", "artistico", "b3", "CogVideo Artistico", 6),
    (5, "Tierra", 8, "0d47a1", "4fc3f7", "variacion", "b4", "Seed 42 Variacion", 6),
    (6, "Humanidad", 18, "d84315", "ffab91", "realista", "b1", "Wan2.2 Realista", 6),
    (6, "Humanidad", 18, "d84315", "ffab91", "cinematic", "b2", "HunyuanVideo Cinematic", 6),
    (6, "Humanidad", 18, "d84315", "ffab91", "artistico", "b3", "CogVideo Artistico", 6),
    (6, "Humanidad", 18, "d84315", "ffab91", "variacion", "b4", "Seed 42 Variacion", 6),
]

styles_filter = {
    "realista": "eq=contrast=1.1:saturation=1.0",
    "cinematic": "eq=contrast=1.5:brightness=-0.05:saturation=1.3,colorbalance=rs=0.1:gs=-0.05:bs=0.1",
    "artistico": "eq=contrast=1.3:brightness=0.05:saturation=1.6,colorbalance=rs=0.15:gs=-0.1:bs=0.2,hue=s=1.5",
    "variacion": "eq=contrast=0.9:saturation=0.8,colorbalance=rs=-0.05:gs=0.05:bs=0.05",
}

for esc_id, desc, dur, c1, c2, style, prefix, label, np in missing:
    output = f"{CLIPS_DIR}/escena{esc_id}_{prefix}.mp4"
    audio = f"{AUDIO_DIR}/escena{esc_id}_tts.mp3"
    
    if os.path.exists(output) and os.path.getsize(output) > 1000:
        print(f"Skipping {output} - exists")
        continue
    
    # Simple filters
    bg = f"drawbox=x=0:y=0:w=1080:h=960:color={c1}@0.3:t=fill,drawbox=x=0:y=960:w=1080:h=960:color={c2}@0.3:t=fill"
    center = f"drawbox=x='540-50+50*sin(2*PI*t/{dur})':y='960-50+50*cos(1.5*PI*t/{dur})':w=100:h=100:color={c2}@0.2:t=fill:enable='between(t,0,{dur})'"
    label_txt = f"drawtext=text='{desc}':fontcolor=white@0.4:fontsize=50:x=(w-text_w)/2:y=h-120:enable='between(t,0,{dur})'"
    label_style = f"drawtext=text='{label}':fontcolor=white@0.15:fontsize=24:x=15:y=15:enable='between(t,0,{dur})'"
    grade = styles_filter[style]
    
    # Particles - simpler version
    particles = []
    for i in range(np):
        x = 100 + (i * 80) % 980
        y = 100 + (i * 120) % 1820
        particles.append(
            f"drawbox=x='{x}+{30+i*10}*sin({1+i}*PI*t/{dur}+{i})':"
            f"y='{y}+{30+i*10}*cos({1+i}*PI*t/{dur}+{i})':"
            f"w={5+i%4}:h={5+i%4}:color={c2}@0.4:t=fill:enable='between(t,0,{dur})'"
        )
    
    filter_str = f"[0:v]{bg},{center},{','.join(particles)},{label_txt},{label_style},{grade}[v]"
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=#000000:s=1080x1920:d={dur}:r=30",
        "-i", audio,
        "-filter_complex", filter_str,
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-shortest",
        output
    ]
    
    print(f"Generating {label} (escena{esc_id})...", end=" ", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(output):
        print(f"OK ({os.path.getsize(output)//1024}KB)")
    else:
        print(f"ERROR: {result.stderr.strip()[-80:]}")

print("\nDone! Checking results...")
import glob
clips = sorted(glob.glob(f"{CLIPS_DIR}/escena*_b*.mp4"))
print(f"Total clips: {len(clips)}")
for c in clips:
    print(f"  {os.path.basename(c)} ({os.path.getsize(c)//1024}KB)")
