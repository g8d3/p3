#!/usr/bin/env python3
"""
Generador de clips sintéticos v3 - Grupo B AI Generation.
Usa drawbox con expresiones temporales para animación,
y filtros de color para diferenciar estilos.
"""

import subprocess
import os

BASE = "/home/vuos/code/p3/s51"
CLIPS_DIR = f"{BASE}/output/clips"
RENDERS_DIR = f"{BASE}/output/renders"
AUDIO_DIR = f"{BASE}/output/audio"

os.makedirs(CLIPS_DIR, exist_ok=True)
os.makedirs(RENDERS_DIR, exist_ok=True)

# Scenes: (id, desc, duration, color1, color2, num_particles)
scenes = [
    (1, "Big Bang", 8, "ff4500", "ff8c00", 20),
    (2, "Nebulosas", 10, "8a2be2", "ff69b4", 30),
    (3, "Galaxias", 8, "1a237e", "4fc3f7", 25),
    (4, "Sistema Solar", 8, "ff6f00", "ffd54f", 15),
    (5, "Tierra", 8, "0d47a1", "4fc3f7", 12),
    (6, "Humanidad", 18, "d84315", "ffab91", 20),
]


def build_particles(esc_id, dur, num, color):
    """Build drawbox strings for animated particles."""
    import random
    random.seed(esc_id * 100)
    particles = []
    for i in range(num):
        x_start = random.randint(50, 1030)
        y_start = random.randint(50, 1870)
        size = random.randint(5, 20)
        speed = random.uniform(0.5, 2.0)
        phase_x = random.uniform(0, 6.28)
        phase_y = random.uniform(0, 6.28)
        alpha = random.uniform(0.2, 0.6)
        particles.append(
            f"drawbox=x='{x_start}+{int(speed*50)}*sin({speed}*PI*t/{dur}+{phase_x})':"
            f"y='{y_start}+{int(speed*50)}*cos({speed}*PI*t/{dur}+{phase_y})':"
            f"w={size}:h={size}:color={color}@{alpha}:t=fill:enable='between(t,0,{dur})'"
        )
    return particles


def build_style_filters(style_name):
    """Return color grading filter strings for each style."""
    styles = {
        "realista": "eq=contrast=1.1:brightness=0.0:saturation=1.0",
        "cinematic": "eq=contrast=1.5:brightness=-0.05:saturation=1.3,colorbalance=rs=0.1:gs=-0.05:bs=0.1",
        "artistico": "eq=contrast=1.3:brightness=0.05:saturation=1.6,colorbalance=rs=0.15:gs=-0.1:bs=0.2,hue=s=1.5",
        "variacion": "eq=contrast=0.9:brightness=0.0:saturation=0.8,colorbalance=rs=-0.05:gs=0.05:bs=0.05",
    }
    return styles.get(style_name, "eq=contrast=1.0")


def run_ffmpeg(cmd, label):
    print(f"  {label}...", end=" ", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        err = result.stderr.strip().split("\n")[-1]
        print(f"ERROR: {err[:100]}")
        return False
    print("OK")
    return True


def generate_clip(esc_id, desc, dur, color1, color2, num_particles, output_path, style, label):
    """Generate a clip with animated particles and style-specific color grading."""
    
    audio = f"{AUDIO_DIR}/escena{esc_id}_tts.mp3"
    if not os.path.exists(audio):
        audio = None
    
    # Build filter chain
    color_filter = build_style_filters(style)
    
    # Background: base color with subtle vertical gradient using drawbox
    bg_filters = [
        f"drawbox=x=0:y=0:w=1080:h=960:color={color1}@0.4:t=fill",
        f"drawbox=x=0:y=960:w=1080:h=960:color={color2}@0.4:t=fill",
    ]
    
    # Add scene label
    label_filters = [
        f"drawtext=text='{desc}':fontcolor=white@0.5:fontsize=60:x=(w-text_w)/2:y=h-150:enable='between(t,0,{dur})'",
        f"drawtext=text='{label}':fontcolor=white@0.2:fontsize=28:x=20:y=20:enable='between(t,0,{dur})'",
    ]
    
    # Animated central element
    center_filters = [
        f"drawbox=x='540-75+75*sin(2*PI*t/{dur})':y='960-75+75*cos(1.5*PI*t/{dur})':w=150:h=150:color={color2}@0.3:t=fill:enable='between(t,0,{dur})'",
        f"drawbox=x='540-40+40*sin(3*PI*t/{dur}+1)':y='960-40+40*cos(2.5*PI*t/{dur}+1)':w=80:h=80:color=white@0.2:t=fill:enable='between(t,0,{dur})'",
    ]
    
    # Particles
    particles = build_particles(esc_id, dur, num_particles, color2)
    
    # Combine all filters
    all_filters = bg_filters + center_filters + particles + label_filters
    
    # Add style grading at the end
    all_filters.append(color_filter)
    
    # Build filter string
    filter_str = "[0:v]" + ",".join(all_filters) + "[v]"
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=#000000:s=1080x1920:d={dur}:r=30",
    ]
    if audio:
        cmd += ["-i", audio]
    cmd += [
        "-filter_complex", filter_str,
        "-map", "[v]",
    ]
    if audio:
        cmd += ["-map", "1:a", "-c:a", "aac", "-b:a", "128k", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", output_path]
    
    return run_ffmpeg(cmd, label)


def generate_all():
    print("=" * 60)
    print("🎬 Grupo B - AI Generation v3")
    print("=" * 60)
    
    styles = [
        ("b1", "realista", "Wan2.2 Realista"),
        ("b2", "cinematic", "HunyuanVideo Cinematic"),
        ("b3", "artistico", "CogVideo Artistico"),
        ("b4", "variacion", "Seed 42 Variacion"),
    ]
    
    for esc_id, desc, dur, color1, color2, num_p in scenes:
        print(f"\n--- Escena {esc_id}: {desc} ({dur}s) ---")
        for prefix, style, label in styles:
            out = f"{CLIPS_DIR}/escena{esc_id}_{prefix}.mp4"
            generate_clip(esc_id, desc, dur, color1, color2, num_p, out, style, label)
    
    print("\n✅ Escenas generadas!")


def assemble_video(prefix, output_name):
    """Assemble clips from all 6 scenes."""
    clips = []
    for esc_id, _, _, _, _, _ in scenes:
        clip = f"{CLIPS_DIR}/escena{esc_id}_{prefix}.mp4"
        if os.path.exists(clip) and os.path.getsize(clip) > 1000:
            clips.append(clip)
        else:
            print(f"  ⚠️ Missing: {clip}")
            return None
    
    if not clips:
        return None
    
    total_dur = sum(s[2] for s in scenes)
    print(f"\n🔗 Ensamblando {len(clips)} clips ({total_dur}s) -> {output_name}")
    
    output = f"{RENDERS_DIR}/{output_name}"
    
    # Use concat filter
    inputs = []
    filter_parts = []
    for i, clip in enumerate(clips):
        inputs.extend(["-i", clip])
        filter_parts.append(f"[{i}:v][{i}:a]")
    
    filter_str = "".join(filter_parts) + f"concat=n={len(clips)}:v=1:a=1[v][a]"
    
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        output
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if os.path.exists(output) and os.path.getsize(output) > 1000:
        # Add transitions
        trans_out = output.replace(".mp4", "_final.mp4")
        cmd2 = [
            "ffmpeg", "-y",
            "-i", output,
            "-vf", f"fade=t=in:st=0:d=1,fade=t=out:st={total_dur-2}:d=2",
            "-af", f"afade=t=in:st=0:d=1,afade=t=out:st={total_dur-2}:d=2",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            trans_out
        ]
        subprocess.run(cmd2, capture_output=True, text=True)
        
        if os.path.exists(trans_out):
            os.replace(trans_out, output)
        
        size_mb = os.path.getsize(output) / (1024*1024)
        print(f"  ✅ {output_name} ({size_mb:.1f} MB)")
        return output
    
    print(f"  ❌ Failed")
    return None


def main():
    generate_all()
    
    print("\n" + "=" * 60)
    print("🔗 Ensamblando videos finales")
    print("=" * 60)
    
    variants = [
        ("b1", "video_b1.mp4"),
        ("b2", "video_b2.mp4"),
        ("b3", "video_b3.mp4"),
        ("b4", "video_b4.mp4"),
    ]
    
    results = {}
    for prefix, name in variants:
        print(f"\n📹 {name}:")
        res = assemble_video(prefix, name)
        if res:
            results[name] = res
    
    print(f"\n✅ Completo! Videos: {list(results.keys())}")
    return results


if __name__ == "__main__":
    main()
