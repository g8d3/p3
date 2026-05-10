#!/usr/bin/env python3
"""
Genera clips sintéticos simulando estilos de diferentes modelos de IA.
Cada variación (B1-B4) usa diferentes tratamientos visuales FFmpeg.
"""

import subprocess
import os
import json

BASE = "/home/vuos/code/p3/s51"
CLIPS_DIR = f"{BASE}/output/clips"
RENDERS_DIR = f"{BASE}/output/renders"
AUDIO_DIR = f"{BASE}/output/audio"

os.makedirs(CLIPS_DIR, exist_ok=True)
os.makedirs(RENDERS_DIR, exist_ok=True)

# Escenas del YAML
escenas = [
    {"id": 1, "desc": "Big Bang", "duracion": 8, "color": "0xFFFF5500", "mov": "zoom out"},
    {"id": 2, "desc": "Nebulosas", "duracion": 10, "color": "0xFF8800AA", "mov": "dolly lateral"},
    {"id": 3, "desc": "Galaxias", "duracion": 8, "color": "0xFF0044FF", "mov": "zoom in + pan"},
    {"id": 4, "desc": "Sistema Solar", "duracion": 8, "color": "0xFFFFAA00", "mov": "fly-through"},
    {"id": 5, "desc": "Tierra", "duracion": 8, "color": "0xFF0066FF", "mov": "zoom in"},
    {"id": 6, "desc": "Humanidad", "duracion": 18, "color": "0xFFFF4400", "mov": "montaje"},
]


def get_audio_duration(audio_file):
    """Get duration of audio file in seconds."""
    if not os.path.exists(audio_file):
        return 0
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_file
    ], capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 0


def generate_base_clip(escena, output_path, width=1080, height=1920, fps=30):
    """Generate a base synthetic clip for a scene with animated content."""
    esc_id = escena["id"]
    dur = escena["duracion"]
    color = escena["color"]
    desc = escena["desc"]
    
    # Create a visually interesting clip using color gradients, shapes, particles
    # Using colorbars, gradients, and animated overlays
    filters = []
    
    # Base: gradient with moving colors
    filters.append(
        f"color=c={color}:s={width}x{height}:d={dur}:r={fps},"
        f"drawbox=x=0:y=0:w={width}:h={height}:color=black@0.3:t=fill,"
        f"geq=r='r(X,Y)*sin(1*PI*T/{dur}+X/{width})':"
        f"g='g(X,Y)*cos(1*PI*T/{dur}+Y/{height})':"
        f"b='b(X,Y)*sin(2*PI*T/{dur})'"
    )
    
    # Add moving elements (circles/stars)
    stars = []
    import random
    random.seed(esc_id * 42)
    for i in range(30):
        x = random.randint(50, width-50)
        y = random.randint(50, height-50)
        r = random.randint(2, 8)
        phase = random.random() * 2 * 3.14159
        stars.append(f"drawbox=x={x}:y={y}:w={r*2}:h={r*2}:color=white@0.8:t=fill:enable='between(t,0,{dur})'")
    
    # Camera movement simulation using zoom/pan
    if "zoom out" in escena["mov"] or "zoom in" in escena["mov"]:
        # Simulate zoom
        start_zoom = 1.0
        end_zoom = 1.5 if "zoom out" in escena["mov"] else 0.7
        if "zoom in" in escena["mov"]:
            start_zoom, end_zoom = 1.5, 1.0
        
        zoom_filter = f"zoompan=z='if(eq(0,on),{start_zoom},{start_zoom}+({end_zoom}-{start_zoom})*(on/({dur}*{fps})))':d={dur*fps}:s={width}x{height}:fps={fps}"
    else:
        zoom_filter = f"null"
    
    # Build complex filter
    filter_str = (
        f"color=c=black:s={width}x{height}:d={dur}:r={fps} [bg];"
        f"color=c={color}:s={width}x{height}:d={dur}:r={fps},"
        f"geq=r='r(X,Y)*abs(sin(PI*T/{dur}+X/{width}))+40*sin(2*PI*T/{dur})':"
        f"g='g(X,Y)*abs(cos(PI*T/{dur}+Y/{height}))+40*cos(1.5*PI*T/{dur})':"
        f"b='b(X,Y)*abs(sin(1.5*PI*T/{dur}+(X+Y)/({width}+{height})))+40*sin(3*PI*T/{dur})' [base];"
        f"[bg][base] overlay=0:0:format=auto, "
        f"drawtext=text='{desc}':fontcolor=white@0.3:fontsize=40:x=(w-text_w)/2:y=h-100:enable='between(t,0,{dur})'"
    )
    
    # Add particle-like dots
    for i, s in enumerate(stars[:15]):
        filter_str += f",{s}"
    
    cmd = [
        "ffmpeg", "-y",
        "-filter_complex", filter_str,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    
    print(f"  Generando clip base para escena {esc_id}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:200]}")
    else:
        print(f"  OK: {output_path}")
    return result.returncode == 0


def apply_style_wan(output_path, audio_path, final_path, dur):
    """Wan2.2 - Realista: natural colors, balanced, clean."""
    # Natural/realistic look: slight contrast, natural color balance
    cmd = [
        "ffmpeg", "-y",
        "-i", output_path,
        "-i", audio_path,
        "-filter_complex",
        "[0:v]eq=contrast=1.1:brightness=0.05:saturation=1.0,"
        "unsharp=5:5:0.8:5:5:0.2,"
        "colorbalance=rs=0.05:gs=0.03:bs=-0.02,"
        f"drawtext=text='Wan2.2 • Realista':fontcolor=white@0.15:fontsize=24:x=20:y=20:enable='between(t,0,{dur})'"
        "[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        final_path
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    return os.path.exists(final_path)


def apply_style_hunyuan(output_path, audio_path, final_path, dur):
    """HunyuanVideo - Cinematic: high contrast, teal/orange, letterbox."""
    # Cinematic look: letterbox bars, teal/orange grade, film grain
    cmd = [
        "ffmpeg", "-y",
        "-i", output_path,
        "-i", audio_path,
        "-filter_complex",
        "[0:v]eq=contrast=1.4:brightness=-0.02:saturation=1.3,"
        "colorbalance=rs=0.1:gs=-0.05:bs=0.1,"
        "curves=vintage='0.0/0.0 0.2/0.15 0.5/0.5 0.8/0.85 1.0/1.0',"
        "grain=strength=3:size=1,"
        "drawbox=x=0:y=0:w=iw:h=ih/8:color=black:t=fill,"
        "drawbox=x=0:y=ih-ih/8:w=iw:h=ih/8:color=black:t=fill,"
        f"drawtext=text='HunyuanVideo • Cinematic':fontcolor=white@0.15:fontsize=24:x=20:y=70:enable='between(t,0,{dur})'"
        "[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        final_path
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    return os.path.exists(final_path)


def apply_style_artistic(output_path, audio_path, final_path, dur):
    """CogVideo - Artístico: stylized, painterly effects."""
    # Artistic look: edge detection, color quantization, artistic filters
    cmd = [
        "ffmpeg", "-y",
        "-i", output_path,
        "-i", audio_path,
        "-filter_complex",
        "[0:v]eq=contrast=1.2:brightness=0.1:saturation=1.5,"
        "edgedetect=low=0.1:high=0.3,"
        "colorbalance=rs=0.15:gs=-0.1:bs=0.2,"
        "curves=preset='darker',"
        "hue=s=2,"
        "smartblur=lr=1:ls=1:lt=3,"
        f"drawtext=text='CogVideo • Artístico':fontcolor=white@0.15:fontsize=24:x=20:y=20:enable='between(t,0,{dur})'"
        "[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        final_path
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    return os.path.exists(final_path)


def apply_style_seedvar(output_path, audio_path, final_path, dur, seed=42):
    """Variación de semillas/ángulos - same base with different visual treatment."""
    # Different angle simulation: flip, rotate, color shift
    angle_text = "Cenital" if seed == 42 else "Contrapicado"
    cmd = [
        "ffmpeg", "-y",
        "-i", output_path,
        "-i", audio_path,
        "-filter_complex",
        f"[0:v]eq=contrast=1.0:brightness=0.0:saturation=0.9,"
        f"colorbalance=rs={0.05 if seed==42 else -0.05}:gs=0:bs={-0.05 if seed==42 else 0.05},"
        f"drawtext=text='Seed {seed} • {angle_text}':fontcolor=white@0.15:fontsize=24:x=20:y=20:enable='between(t,0,{dur})'"
        "[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        final_path
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    return os.path.exists(final_path)


def create_scene_clips():
    """Generate all scene clips for all 4 variations."""
    
    results = {
        "video_b1": {"modelo": "Wan2.2", "estilo": "realista", "clips": []},
        "video_b2": {"modelo": "HunyuanVideo", "estilo": "cinematic", "clips": []},
        "video_b3": {"modelo": "CogVideo", "estilo": "artístico", "clips": []},
        "video_b4": {"modelo": "Wan2.2+Hunyuan", "estilo": "variación semillas", "clips": []},
    }
    
    for esc in escenas:
        esc_id = esc["id"]
        dur = esc["duracion"]
        audio_file = f"{AUDIO_DIR}/escena{esc_id}_tts.mp3"
        audio_dur = get_audio_duration(audio_file)
        actual_dur = max(dur, audio_dur) if audio_dur else dur
        
        print(f"\n=== Escena {esc_id}: {esc['desc']} ({actual_dur}s) ===")
        
        # Generate base clip (shared raw material)
        base_clip = f"{CLIPS_DIR}/escena{esc_id}_base.mp4"
        generate_base_clip(esc, base_clip)
        
        # B1: Wan2.2 Realista
        print(f"  [B1] Aplicando estilo Wan2.2 Realista...")
        b1_out = f"{CLIPS_DIR}/escena{esc_id}_b1.mp4"
        ok1 = apply_style_wan(base_clip, audio_file, b1_out, actual_dur)
        if ok1:
            results["video_b1"]["clips"].append(b1_out)
        
        # B2: HunyuanVideo Cinematic
        print(f"  [B2] Aplicando estilo HunyuanVideo Cinematic...")
        b2_out = f"{CLIPS_DIR}/escena{esc_id}_b2.mp4"
        ok2 = apply_style_hunyuan(base_clip, audio_file, b2_out, actual_dur)
        if ok2:
            results["video_b2"]["clips"].append(b2_out)
        
        # B3: CogVideo Artístico
        print(f"  [B3] Aplicando estilo CogVideo Artístico...")
        b3_out = f"{CLIPS_DIR}/escena{esc_id}_b3.mp4"
        ok3 = apply_style_artistic(base_clip, audio_file, b3_out, actual_dur)
        if ok3:
            results["video_b3"]["clips"].append(b3_out)
        
        # B4: Variación semillas (seed 42)
        print(f"  [B4] Aplicando variación Seed 42...")
        b4_out = f"{CLIPS_DIR}/escena{esc_id}_b4.mp4"
        ok4 = apply_style_seedvar(base_clip, audio_file, b4_out, actual_dur, seed=42)
        if ok4:
            results["video_b4"]["clips"].append(b4_out)
    
    return results


def assemble_video(clip_list, output_path):
    """Concatenate clips with transitions using concat demuxer."""
    if not clip_list:
        print(f"  No clips to assemble for {output_path}")
        return False
    
    # Create temp concat file
    concat_file = f"{CLIPS_DIR}/concat_{os.path.basename(output_path)}.txt"
    with open(concat_file, "w") as f:
        for clip in clip_list:
            abs_path = os.path.abspath(clip)
            f.write(f"file '{abs_path}'\n")
    
    print(f"  Ensamblando {len(clip_list)} clips -> {output_path}")
    
    # First try concat protocol (lossless)
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        # Fallback: re-encode with concat filter
        inputs = []
        filter_parts = []
        for i, clip in enumerate(clip_list):
            inputs.extend(["-i", clip])
            filter_parts.append(f"[{i}:v][{i}:a]")
        
        filter_str = "".join(filter_parts) + f"concat=n={len(clip_list)}:v=1:a=1[v][a]"
        
        cmd2 = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_str,
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            output_path
        ]
        result = subprocess.run(cmd2, capture_output=True, text=True)
    
    ok = os.path.exists(output_path) and os.path.getsize(output_path) > 1000
    if ok:
        print(f"  OK: {output_path} ({os.path.getsize(output_path)//1024} KB)")
    else:
        print(f"  ERROR ensamblando: {result.stderr[:200]}")
    
    return ok


def add_transitions(input_path, output_path):
    """Add fade in/out transitions to final video."""
    # Probe duration
    result = subprocess.run([
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", input_path
    ], capture_output=True, text=True)
    dur = float(result.stdout.strip())
    
    print(f"  Añadiendo transiciones (fade in/out) a {os.path.basename(output_path)} ({dur:.1f}s)")
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", f"fade=t=in:st=0:d=1,fade=t=out:st={dur-2}:d=2",
        "-af", f"afade=t=in:st=0:d=1,afade=t=out:st={dur-2}:d=2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    
    ok = os.path.exists(output_path)
    if ok:
        print(f"  OK con transiciones: {output_path}")
    return ok


def main():
    print("=" * 60)
    print("🎬 Grupo B - AI Generation: Generando clips sintéticos")
    print("=" * 60)
    
    # Step 1: Generate all scene clips with different styles
    print("\n📦 Fase 1: Generando clips por escena y estilo...")
    results = create_scene_clips()
    
    # Step 2: Assemble each variation
    print("\n🔗 Fase 2: Ensamblando videos finales...")
    
    variations = [
        ("video_b1.mp4", results["video_b1"]["clips"]),
        ("video_b2.mp4", results["video_b2"]["clips"]),
        ("video_b3.mp4", results["video_b3"]["clips"]),
        ("video_b4.mp4", results["video_b4"]["clips"]),
    ]
    
    final_videos = {}
    for name, clips in variations:
        if not clips:
            print(f"  ⚠️ No hay clips para {name}")
            continue
        
        temp = f"{RENDERS_DIR}/{name.replace('.mp4', '_temp.mp4')}"
        final = f"{RENDERS_DIR}/{name}"
        
        ok = assemble_video(clips, temp)
        if ok:
            ok = add_transitions(temp, final)
            if ok:
                final_videos[name] = final
        
        # Cleanup temp
        if os.path.exists(temp):
            os.remove(temp)
    
    # Step 3: Cleanup base clips
    print("\n🧹 Limpieza...")
    for esc in escenas:
        base = f"{CLIPS_DIR}/escena{esc['id']}_base.mp4"
        if os.path.exists(base):
            os.remove(base)
    
    print("\n✅ Generación completa!")
    print(f"   Videos generados: {list(final_videos.keys())}")
    
    return final_videos


if __name__ == "__main__":
    main()
