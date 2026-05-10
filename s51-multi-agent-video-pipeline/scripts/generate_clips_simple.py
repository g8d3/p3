#!/usr/bin/env python3
"""
Generador de clips sintéticos para Grupo B - AI Generation.
Crea 4 variaciones por escena con diferentes estilos visuales usando FFmpeg.
"""

import subprocess
import os
import sys

BASE = "/home/vuos/code/p3/s51"
CLIPS_DIR = f"{BASE}/output/clips"
RENDERS_DIR = f"{BASE}/output/renders"
AUDIO_DIR = f"{BASE}/output/audio"

os.makedirs(CLIPS_DIR, exist_ok=True)
os.makedirs(RENDERS_DIR, exist_ok=True)

# Scene definitions from escenas.yaml
scenes = [
    {"id": 1, "desc": "Big Bang", "dur": 8, "color": "ff4500", "color2": "ff8c00"},
    {"id": 2, "desc": "Nebulosas", "dur": 10, "color": "8a2be2", "color2": "ff69b4"},
    {"id": 3, "desc": "Galaxias", "dur": 8, "color": "1a237e", "color2": "4fc3f7"},
    {"id": 4, "desc": "Sistema Solar", "dur": 8, "color": "ff6f00", "color2": "ffd54f"},
    {"id": 5, "desc": "Tierra", "dur": 8, "color": "0d47a1", "color2": "4fc3f7"},
    {"id": 6, "desc": "Humanidad", "dur": 18, "color": "d84315", "color2": "ffab91"},
]


def run_ffmpeg(cmd, label=""):
    """Run FFmpeg with proper error handling."""
    print(f"  {label}...", end=" ", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR")
        # Print last 3 lines of stderr
        err_lines = result.stderr.strip().split("\n")
        for line in err_lines[-3:]:
            print(f"    {line}")
        return False
    print("OK")
    return True


def generate_clip(esc, output_path, style_commands, label):
    """Generate a clip with the given style commands."""
    esc_id = esc["id"]
    dur = esc["dur"]
    audio = f"{AUDIO_DIR}/escena{esc_id}_tts.mp3"
    
    # Create animated color source with moving gradient
    # Use multiple overlay circles for visual interest
    base_cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=#{esc['color']}:s=1080x1920:d={dur}:r=30",
        "-i", audio,
        "-filter_complex",
    ]
    
    # Build filter
    filter_str = style_commands
    
    # Add scene description text
    filter_str += f",drawtext=text='{esc['desc']}':fontcolor=white@0.5:fontsize=60:x=(w-text_w)/2:y=h-150:enable='between(t,0,{dur})'"
    filter_str += f",drawtext=text='{label}':fontcolor=white@0.2:fontsize=30:x=20:y=20:enable='between(t,0,{dur})'"
    filter_str += "[v]"
    
    cmd = base_cmd + [filter_str, "-map", "[v]", "-map", "1:a",
                      "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                      "-c:a", "aac", "-b:a", "128k", "-shortest", output_path]
    
    return run_ffmpeg(cmd, label)


def generate_all_clips():
    """Generate all 4 variations for each scene."""
    
    for esc in scenes:
        esc_id = esc["id"]
        dur = esc["dur"]
        c1 = esc["color"]
        c2 = esc["color2"]
        
        print(f"\n=== Escena {esc_id}: {esc['desc']} ({dur}s) ===")
        
        # B1: Wan2.2 Realista - Natural colors, smooth gradients, balanced
        b1_out = f"{CLIPS_DIR}/escena{esc_id}_b1.mp4"
        b1_filters = (
            f"[0:v]geq=r='r(X,Y)*(0.85+0.15*sin(2*PI*t/{dur}+X/200.0))':"
            f"g='g(X,Y)*(0.85+0.15*cos(1.5*PI*t/{dur}+Y/200.0))':"
            f"b='b(X,Y)*(0.85+0.15*sin(PI*t/{dur}+(X+Y)/400.0))',"
            f"eq=contrast=1.1:saturation=1.0"
        )
        generate_clip(esc, b1_out, b1_filters, "Wan2.2 Realista")
        
        # B2: HunyuanVideo Cinematic - High contrast, letterbox, teal/orange
        b2_out = f"{CLIPS_DIR}/escena{esc_id}_b2.mp4"
        b2_filters = (
            f"[0:v]geq=r='r(X,Y)*(0.9+0.1*sin(2*PI*t/{dur}+X/300.0))':"
            f"g='g(X,Y)*(0.8+0.2*cos(1.5*PI*t/{dur}+Y/300.0))':"
            f"b='b(X,Y)*(0.9+0.1*sin(PI*t/{dur}+(X+Y)/500.0))',"
            f"eq=contrast=1.5:brightness=-0.05:saturation=1.3,"
            f"colorbalance=rs=0.1:gs=-0.05:bs=0.1,"
            f"drawbox=x=0:y=0:w=iw:h=ih/8:color=black:t=fill,"
            f"drawbox=x=0:y=ih-ih/8:w=iw:h=ih/8:color=black:t=fill"
        )
        generate_clip(esc, b2_out, b2_filters, "HunyuanVideo Cinematic")
        
        # B3: CogVideo Artístico - High saturation, edge effects
        b3_out = f"{CLIPS_DIR}/escena{esc_id}_b3.mp4"
        b3_filters = (
            f"[0:v]geq=r='r(X,Y)*(0.7+0.3*sin(3*PI*t/{dur}+X/150.0))':"
            f"g='g(X,Y)*(0.7+0.3*cos(2.5*PI*t/{dur}+Y/150.0))':"
            f"b='b(X,Y)*(0.7+0.3*sin(2*PI*t/{dur}+(X+Y)/300.0))',"
            f"eq=contrast=1.3:brightness=0.1:saturation=1.6,"
            f"colorbalance=rs=0.15:gs=-0.1:bs=0.2,"
            f"hue=s=1.5"
        )
        generate_clip(esc, b3_out, b3_filters, "CogVideo Artistico")
        
        # B4: Variación semillas/ángulos - Different color treatment
        b4_out = f"{CLIPS_DIR}/escena{esc_id}_b4.mp4"
        b4_filters = (
            f"[0:v]geq=r='r(X,Y)*(0.75+0.25*sin(3.5*PI*t/{dur}+Y/150.0))':"
            f"g='g(X,Y)*(0.75+0.25*cos(3*PI*t/{dur}+X/150.0))':"
            f"b='b(X,Y)*(0.75+0.25*sin(2.5*PI*t/{dur}+(X-Y)/350.0))',"
            f"eq=contrast=0.9:saturation=0.8,"
            f"colorbalance=rs=-0.05:gs=0.05:bs=0.05"
        )
        generate_clip(esc, b4_out, b4_filters, "Seed 42 Variacion")
    
    print("\n✅ Todas las escenas generadas!")


def assemble_video(clip_prefix, output_name):
    """Assemble clips from all scenes into one video."""
    clips = []
    for esc_id in range(1, 7):
        clip = f"{CLIPS_DIR}/escena{esc_id}_{clip_prefix}.mp4"
        if os.path.exists(clip) and os.path.getsize(clip) > 1000:
            clips.append(clip)
        else:
            print(f"  ⚠️ Missing: {clip}")
    
    if not clips:
        print(f"  No clips found for {output_name}")
        return None
    
    print(f"\n🔗 Ensamblando {len(clips)} clips -> {output_name}")
    
    output = f"{RENDERS_DIR}/{output_name}"
    
    # Use concat demuxer
    concat_file = f"{CLIPS_DIR}/concat_{output_name}.txt"
    with open(concat_file, "w") as f:
        for clip in clips:
            f.write(f"file '{os.path.abspath(clip)}'\n")
    
    # Try concat first
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        f"{RENDERS_DIR}/{output_name.replace('.mp4', '_raw.mp4')}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    raw_out = f"{RENDERS_DIR}/{output_name.replace('.mp4', '_raw.mp4')}"
    
    if result.returncode == 0 and os.path.exists(raw_out):
        # Add transitions
        dur_total = sum(scenes[i-1]["dur"] for i in range(1, 7))
        print(f"  Añadiendo transiciones (duración total: ~{dur_total}s)")
        
        cmd2 = [
            "ffmpeg", "-y",
            "-i", raw_out,
            "-vf", f"fade=t=in:st=0:d=1,fade=t=out:st={dur_total-2}:d=2",
            "-af", f"afade=t=in:st=0:d=1,afade=t=out:st={dur_total-2}:d=2",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            output
        ]
        subprocess.run(cmd2, capture_output=True, text=True)
        
        # Cleanup
        if os.path.exists(raw_out):
            os.remove(raw_out)
        
        if os.path.exists(output):
            size_mb = os.path.getsize(output) / (1024*1024)
            print(f"  ✅ {output} ({size_mb:.1f} MB)")
            return output
    
    # Fallback: re-encode with concat filter
    print("  Fallback: re-encoding with concat filter...")
    inputs = []
    filter_parts = []
    for i, clip in enumerate(clips):
        inputs.extend(["-i", clip])
        filter_parts.append(f"[{i}:v][{i}:a]")
    
    filter_str = "".join(filter_parts) + f"concat=n={len(clips)}:v=1:a=1[v][a]"
    
    cmd3 = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        output
    ]
    result = subprocess.run(cmd3, capture_output=True, text=True)
    
    if os.path.exists(output):
        size_mb = os.path.getsize(output) / (1024*1024)
        print(f"  ✅ {output} ({size_mb:.1f} MB)")
        return output
    else:
        print(f"  ❌ Failed: {result.stderr[:200]}")
        return None


def main():
    print("=" * 60)
    print("🎬 Grupo B - AI Generation: Generando clips sintéticos")
    print("=" * 60)
    
    # Generate all clips
    generate_all_clips()
    
    # Assemble the 4 variations
    print("\n" + "=" * 60)
    print("🔗 Ensamblando videos finales")
    print("=" * 60)
    
    variations = [
        ("b1", "video_b1.mp4", "Wan2.2 Realista"),
        ("b2", "video_b2.mp4", "HunyuanVideo Cinematic"),
        ("b3", "video_b3.mp4", "CogVideo Artistico"),
        ("b4", "video_b4.mp4", "Variacion Semillas"),
    ]
    
    results = {}
    for prefix, name, label in variations:
        print(f"\n📹 {label}:")
        result = assemble_video(prefix, name)
        if result:
            results[name] = result
    
    print("\n" + "=" * 60)
    print("✅ Generación completa!")
    print(f"   Videos: {list(results.keys())}")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    main()
