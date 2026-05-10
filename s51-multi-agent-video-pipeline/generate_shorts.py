#!/usr/bin/env python3
"""
ShortGPT Pipeline - Grupo D
Genera 5 variaciones de shorts a partir de escenas.yaml y TTS generado.

Variaciones:
  1. video_d1.mp4 — Short estándar (español, voz masculina, estilo informativo)
  2. video_d2.mp4 — Short en inglés (voz femenina, estilo entretenimiento)
  3. video_d3.mp4 — Short con subtítulos grandes (kinetic typography)
  4. video_d4.mp4 — Short con ritmo ultra-rápido (cada 2s cambia)
  5. video_d5.mp4 — Short con música electrónica de fondo (estilo TikTok)
"""

import subprocess
import json
import os
import math

BASE_DIR = "/home/vuos/code/p3/s51"
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
RENDERS_DIR = os.path.join(OUTPUT_DIR, "renders")

os.makedirs(RENDERS_DIR, exist_ok=True)

# ─── Scene data from escenas.yaml ───
SCENES = [
    {
        "id": 1, "duration": 8,
        "title": "EL BIG BANG",
        "bg_color": "0x000011",
        "accent_color": "0xFFFFFF",
        "flare_color": "0x4488FF",
        "text": "Hace 13.8 mil millones de años...",
        "subtext": "¡El universo nació con una explosión!",
        "tts_file": "scene1_es.mp3"
    },
    {
        "id": 2, "duration": 12,
        "title": "ESTRELLAS Y GALAXIAS",
        "bg_color": "0x0A001A",
        "accent_color": "0xFF66AA",
        "flare_color": "0xAA44FF",
        "text": "La gravedad unió el polvo cósmico",
        "subtext": "Nacieron miles de millones de estrellas ✨",
        "tts_file": "scene2_es.mp3"
    },
    {
        "id": 3, "duration": 8,
        "title": "SISTEMA SOLAR",
        "bg_color": "0x1A0A00",
        "accent_color": "0xFFAA00",
        "flare_color": "0xFF6600",
        "text": "El Sol encendió su fuego termonuclear",
        "subtext": "Planetas danzando a su alrededor 🪐",
        "tts_file": "scene3_es.mp3"
    },
    {
        "id": 4, "duration": 12,
        "title": "ORIGEN DE LA VIDA",
        "bg_color": "0x001122",
        "accent_color": "0x00FF88",
        "flare_color": "0x44DDFF",
        "text": "El caos químico dio paso al milagro",
        "subtext": "La vida encontró su camino 🌱",
        "tts_file": "scene4_es.mp3"
    },
    {
        "id": 5, "duration": 8,
        "title": "EVOLUCIÓN HUMANA",
        "bg_color": "0x221100",
        "accent_color": "0xFFDD00",
        "flare_color": "0xFF8800",
        "text": "Una especie desarrolló conciencia",
        "subtext": "Miramos al cielo y preguntamos... 🧠",
        "tts_file": "scene5_es.mp3"
    },
    {
        "id": 6, "duration": 12,
        "title": "POLVO DE ESTRELLAS",
        "bg_color": "0x000022",
        "accent_color": "0x88AAFF",
        "flare_color": "0xFFFFFF",
        "text": "Somos polvo de estrellas",
        "subtext": "El viaje continúa... 🚀",
        "tts_file": "scene6_es.mp3"
    }
]

def parse_color(hex_val):
    """Parse hex color int to (r, g, b) tuple."""
    if isinstance(hex_val, str):
        hex_val = int(hex_val, 16)
    return (hex_val >> 16) & 0xFF, (hex_val >> 8) & 0xFF, hex_val & 0xFF


def hex_to_ffmpeg_color(hex_val):
    """Convert 0xRRGGBB to ffmpeg color name or use col=`0xRRGGBB`."""
    return f"0x{hex_val:06X}" if isinstance(hex_val, int) else hex_val

def get_tts_path(lang, scene_id):
    """Get path for TTS audio file."""
    if lang == "es":
        return os.path.join(AUDIO_DIR, f"scene{scene_id}_es.mp3")
    elif lang == "en":
        return os.path.join(AUDIO_DIR, f"scene{scene_id}_en.mp3")
    return None

# ─── Generate a scene video with ffmpeg ───
def generate_scene_video(scene, lang="es", font_size=48, 
                          speed_multiplier=1.0, extra_filters="",
                          use_music=False):
    """
    Generate a single scene as a video file using FFmpeg.
    Creates animated background with text overlays.
    """
    scene_id = scene["id"]
    duration = scene["duration"] / speed_multiplier
    bg_int = scene["bg_color"]
    accent_int = scene["accent_color"]
    bg_r, bg_g, bg_b = parse_color(bg_int)
    ac_r, ac_g, ac_b = parse_color(accent_int)
    bg_str = hex_to_ffmpeg_color(bg_int)
    accent_str = hex_to_ffmpeg_color(accent_int)
    bg = bg_str
    accent = accent_str
    
    output_file = os.path.join(RENDERS_DIR, f"scene{scene_id}_{lang}_raw.mp4")
    tts_file = get_tts_path(lang, scene_id)
    
    # Build complex filter for animated background + text
    # Use gradient with movement, then overlay text
    
    # Simple approach: gradient background with moving elements
    fontfile = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if not os.path.exists(fontfile):
        fontfile = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    # Primary text box
    text_main = f"drawtext=text='{scene['title']}':fontfile={fontfile}:fontsize={font_size}:fontcolor=white:box=1:boxcolor=black@0.5:boxborder_w=20:x=(w-text_w)/2:y=h*0.1:enable='between(t,0,{duration})'"
    
    # Subtitle text
    text_sub = f"drawtext=text='{scene['text']}':fontfile={fontfile}:fontsize={int(font_size*0.7)}:fontcolor=white:box=1:boxcolor=black@0.4:boxborder_w=15:x=(w-text_w)/2:y=h*0.72:enable='between(t,0,{duration})'"
    
    # Bottom text
    text_bottom = f"drawtext=text='{scene['subtext']}':fontfile={fontfile}:fontsize={int(font_size*0.6)}:fontcolor={accent}:box=1:boxcolor=black@0.3:boxborder_w=10:x=(w-text_w)/2:y=h*0.85:enable='between(t,0,{duration})'"
    
    # Animated gradient background
    filter_complex = (
        f"color=c=black:s=1080x1920:d={duration}:r=30[bg];"
        f"color=c={bg}:s=1080x1920:d={duration}:r=30,"
        f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)+32*sin(2*PI*T+{scene_id}*PI/3)',"
        f"format=rgba[grad];"
        f"[bg][grad]overlay=(w-iw)/2:(h-ih)/2[base];"
        # Add animated particles (stars)
        f"color=c=white@0.0:s=1080x1920:d={duration}:r=30,"
        f"geq=r='255*random(1)*sin(T*{scene_id}+X*0.01)':"
        f"g='255*random(2)*sin(T*{scene_id}+Y*0.01)':"
        f"b='255*random(3)*sin(T*{scene_id}+X*Y*0.0001)':"
        f"a='255*pow(random(4),3)*step(0.98,random(5))'[stars];"
        f"[base][stars]overlay=0:0[base2];"
        # Animated light flare
        f"color=c={accent_str}@0.0:s=200x200:d={duration}:r=30,"
        f"geq=r='{ac_r}*exp(-((X-100)^2+(Y-100)^2)/1000)*sin(2*PI*T*0.5)':"
        f"g='{ac_g}*exp(-((X-100)^2+(Y-100)^2)/1000)*sin(2*PI*T*0.5)':"
        f"b='{ac_b}*exp(-((X-100)^2+(Y-100)^2)/1000)*sin(2*PI*T*0.5)':"
        f"a='255*exp(-((X-100)^2+(Y-100)^2)/1000)*0.3'[flare];"
        f"[base2][flare]overlay=540-100:960-100[base3];"
        # Text overlays
        f"[base3]{text_main},{text_sub},{text_bottom}[out]"
    )
    
    # Build ffmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1:r=30",  # dummy input
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_file
    ]
    
    # If we have TTS, add audio
    if tts_file and os.path.exists(tts_file):
        cmd = [
            "ffmpeg", "-y",
            "-i", tts_file,
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-map", "0:a",
            "-shortest",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            output_file
        ]
    
    print(f"  Generating scene {scene_id}... ({duration}s)")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR scene {scene_id}: {result.stderr[:500]}")
        return None
    
    return output_file


def generate_music_track(duration, style="electronic", output_file=None):
    """Generate background music using FFmpeg audio synthesis."""
    if output_file is None:
        output_file = os.path.join(AUDIO_DIR, f"bg_music_{style}.mp3")
    
    if style == "electronic":
        # Electronic beat: kick + synth
        filter_complex = (
            f"aformat=sample_rates=44100:channel_layouts=mono,"
            f"aevalsrc=exprs="
            f"'sin(2*PI*440*T)*0.1 + "  # bass synth
            f"sin(2*PI*880*T)*0.05 + "  # harmonic
            f"sin(2*PI*220*T)*0.15*sin(2*PI*2*T) + "  # wobble bass
            f"pow(sin(2*PI*4*T), 20)*0.3'"  # kick drum pattern
            f":d={duration}:s=44100[c]"
        )
    elif style == "cinematic":
        filter_complex = (
            f"aevalsrc=exprs="
            f"'sin(2*PI*220*T)*0.2*exp(-T*0.1) + "  # epic strings
            f"sin(2*PI*330*T)*0.15*sin(2*PI*0.5*T) + "  # pads
            f"sin(2*PI*110*T)*0.3 + "  # bass drone
            f"pow(sin(2*PI*2*T), 10)*0.2'"  # slow pulse
            f":d={duration}:s=44100[c]"
        )
    else:
        filter_complex = (
            f"aevalsrc=exprs="
            f"'sin(2*PI*432*T)*0.1*exp(-T*0.05)'"
            f":d={duration}:s=44100[c]"
        )
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", filter_complex,
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_file
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Music generation error: {result.stderr[:300]}")
        return None
    return output_file


def concat_videos(video_files, output_file, audio_file=None, music_file=None):
    """Concatenate video scenes and add audio."""
    if not video_files:
        return None
    
    # Create concat file
    concat_file = os.path.join(RENDERS_DIR, "concat_list.txt")
    with open(concat_file, "w") as f:
        for vf in video_files:
            if vf and os.path.exists(vf):
                f.write(f"file '{vf}'\n")
    
    # Concat videos
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_file
    ]
    
    print(f"  Concatenating: {output_file}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Concat error: {result.stderr[:500]}")
        return None
    
    # If we have a combined audio track, mix it in
    if audio_file and os.path.exists(audio_file):
        # Mix narration + music
        temp_output = output_file.replace(".mp4", "_temp.mp4")
        mix_cmd = [
            "ffmpeg", "-y",
            "-i", output_file,
            "-i", audio_file,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            temp_output
        ]
        if music_file and os.path.exists(music_file):
            # Mix narration + music
            mix_cmd = [
                "ffmpeg", "-y",
                "-i", output_file,
                "-i", audio_file,
                "-i", music_file,
                "-filter_complex",
                "[1:a]volume=1.0[narr];[2:a]volume=0.15[music];[narr][music]amix=inputs=2:duration=first[outa]",
                "-map", "0:v:0",
                "-map", "[outa]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                temp_output
            ]
        
        result = subprocess.run(mix_cmd, capture_output=True, text=True)
        if result.returncode == 0 and os.path.exists(temp_output):
            os.replace(temp_output, output_file)
    
    return output_file


def concat_audio_files(audio_files, output_file):
    """Concatenate multiple TTS audio files."""
    concat_file = os.path.join(AUDIO_DIR, "concat_audio.txt")
    with open(concat_file, "w") as f:
        for af in audio_files:
            if af and os.path.exists(af):
                f.write(f"file '{af}'\n")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_file
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Audio concat error: {result.stderr[:300]}")
        return None
    return output_file


# ═══════════════════════════════════════════════
# VARIATION 1: Short estándar (español, informativo)
# ═══════════════════════════════════════════════
def generate_variation_1():
    print("\n" + "="*60)
    print("🎬 VARIACIÓN 1: Short estándar (Español, Voz masculina, Informativo)")
    print("="*60)
    
    # Generate each scene video
    scene_videos = []
    for scene in SCENES:
        v = generate_scene_video(scene, lang="es", font_size=52)
        if v:
            scene_videos.append(v)
    
    if not scene_videos:
        print("ERROR: No scenes generated")
        return None
    
    # Concat all scene videos
    output = os.path.join(RENDERS_DIR, "video_d1.mp4")
    
    # Generate combined audio
    tts_files = [os.path.join(AUDIO_DIR, f"scene{s['id']}_es.mp3") for s in SCENES]
    combined_audio = os.path.join(AUDIO_DIR, "combined_es.mp3")
    concat_audio_files(tts_files, combined_audio)
    
    # Generate cinematic background music
    music_file = generate_music_track(60, style="cinematic")
    
    result = concat_videos(scene_videos, output, combined_audio, music_file)
    return output


# ═══════════════════════════════════════════════
# VARIATION 2: Short en inglés (voz femenina, entretenimiento)
# ═══════════════════════════════════════════════
def generate_variation_2():
    print("\n" + "="*60)
    print("🎬 VARIACIÓN 2: Short en inglés (Voz femenina, Entretenimiento)")
    print("="*60)
    
    # English scenes
    en_scenes = [
        {**SCENES[0], "title": "THE BIG BANG", "text": "13.8 billion years ago...", "subtext": "The universe was born! 🔥", "tts_file": None},
        {**SCENES[1], "title": "STARS & GALAXIES", "text": "Gravity united cosmic dust", "subtext": "Billions of stars were born ✨", "tts_file": None},
        {**SCENES[2], "title": "SOLAR SYSTEM", "text": "The Sun ignited its fire", "subtext": "Planets dancing around it 🪐", "tts_file": None},
        {**SCENES[3], "title": "ORIGIN OF LIFE", "text": "Chemical chaos became a miracle", "subtext": "Life found its way 🌱", "tts_file": None},
        {**SCENES[4], "title": "HUMAN EVOLUTION", "text": "One species gained consciousness", "subtext": "We looked at the sky... 🧠", "tts_file": None},
        {**SCENES[5], "title": "STARDUST", "text": "We are made of stardust", "subtext": "The journey continues... 🚀", "tts_file": None}
    ]
    
    # Generate English TTS
    print("  Generating English TTS...")
    en_tts_files = []
    for i, (scene, en_scene) in enumerate(zip(SCENES, en_scenes)):
        output_file = os.path.join(AUDIO_DIR, f"scene{scene['id']}_en.mp3")
        cmd = [
            "tts-speak",
            en_scene["text"] + ". " + en_scene["subtext"].split(" ")[0] + " the universe...",
            "--voice", "af_nicole",
            "--speed", "1.0",
            "--output", output_file
        ]
        # For a more complete TTS, use the full translation
        full_texts = [
            "In the beginning, everything was an infinitely small and dense point. 13.8 billion years ago... that point exploded. The universe was born.",
            "The universe expanded and cooled. Gravity united gas and cosmic dust, igniting billions of stars. Galaxies were born: immense islands of light in the infinite darkness.",
            "In an arm of an ordinary galaxy, a star called the Sun ignited its fire. Around it, planets of rock and gas began to dance: our solar system.",
            "On Earth, chemical chaos gave way to a miracle. Simple molecules combined to create life. First cells, first oceans full of possibilities. Life found its way.",
            "Life evolved, and among all species, one developed consciousness. The human being looked at the sky and asked: what are we?",
            "We are stardust. The universe didn't just create galaxies and planets... it also created eyes to contemplate itself. And the journey continues."
        ]
        cmd = [
            "tts-speak",
            full_texts[i],
            "--voice", "af_nicole",
            "--speed", "1.0",
            "--output", output_file
        ]
        print(f"  TTS en scene {scene['id']}...")
        subprocess.run(cmd, capture_output=True, text=True)
        en_tts_files.append(output_file)
    
    # Generate scene videos
    scene_videos = []
    for i, scene in enumerate(en_scenes):
        v = generate_scene_video(scene, lang="en", font_size=52)
        if v:
            scene_videos.append(v)
    
    if not scene_videos:
        print("ERROR: No scenes generated")
        return None
    
    # Combined English audio
    combined_audio = os.path.join(AUDIO_DIR, "combined_en.mp3")
    concat_audio_files(en_tts_files, combined_audio)
    
    output = os.path.join(RENDERS_DIR, "video_d2.mp4")
    music_file = generate_music_track(60, style="cinematic")
    
    result = concat_videos(scene_videos, output, combined_audio, music_file)
    return output


# ═══════════════════════════════════════════════
# VARIATION 3: Subtítulos grandes (kinetic typography)
# ═══════════════════════════════════════════════
def generate_variation_3():
    print("\n" + "="*60)
    print("🎬 VARIACIÓN 3: Kinetic Typography (Subtítulos grandes)")
    print("="*60)
    
    # Extra large font for kinetic typography effect
    scene_videos = []
    for scene in SCENES:
        v = generate_scene_video(scene, lang="es", font_size=72)  # BIG text
        if v:
            scene_videos.append(v)
    
    if not scene_videos:
        return None
    
    output = os.path.join(RENDERS_DIR, "video_d3.mp4")
    tts_files = [os.path.join(AUDIO_DIR, f"scene{s['id']}_es.mp3") for s in SCENES]
    combined_audio = os.path.join(AUDIO_DIR, "combined_es.mp3")
    concat_audio_files(tts_files, combined_audio)
    
    music_file = generate_music_track(60, style="electronic")
    result = concat_videos(scene_videos, output, combined_audio, music_file)
    return output


# ═══════════════════════════════════════════════
# VARIATION 4: Ritmo ultra-rápido (cada 2s cambia)
# ═══════════════════════════════════════════════
def generate_variation_4():
    print("\n" + "="*60)
    print("🎬 VARIACIÓN 4: Ritmo ultra-rápido (cada 2s)")
    print("="*60)
    
    # Split each scene into 2-second segments for ultra-fast pacing
    fast_scenes = []
    for scene in SCENES:
        # Divide each scene into ~2s segments
        duration = scene["duration"]
        num_segments = max(2, duration // 2)
        seg_duration = duration / num_segments
        
        for seg in range(num_segments):
            fast_scenes.append({
                **scene,
                "duration": seg_duration,
                "title": scene["title"] if seg == 0 else "",
                "text": scene["text"],
                "subtext": f"{'█' * (seg+1)}"
            })
    
    scene_videos = []
    for scene in fast_scenes:
        v = generate_scene_video(
            scene, lang="es", font_size=48,
            speed_multiplier=1.5,  # Overall faster
            extra_filters=""
        )
        if v:
            scene_videos.append(v)
    
    if not scene_videos:
        return None
    
    output = os.path.join(RENDERS_DIR, "video_d4.mp4")
    tts_files = [os.path.join(AUDIO_DIR, f"scene{s['id']}_es.mp3") for s in SCENES]
    combined_audio = os.path.join(AUDIO_DIR, "combined_es.mp3")
    concat_audio_files(tts_files, combined_audio)
    
    music_file = generate_music_track(60, style="electronic")
    result = concat_videos(scene_videos, output, combined_audio, music_file)
    return output


# ═══════════════════════════════════════════════
# VARIATION 5: Música electrónica de fondo (TikTok style)
# ═══════════════════════════════════════════════
def generate_variation_5():
    print("\n" + "="*60)
    print("🎬 VARIACIÓN 5: Estilo TikTok (Música electrónica)")
    print("="*60)
    
    scene_videos = []
    for scene in SCENES:
        v = generate_scene_video(scene, lang="es", font_size=52)
        if v:
            scene_videos.append(v)
    
    if not scene_videos:
        return None
    
    output = os.path.join(RENDERS_DIR, "video_d5.mp4")
    tts_files = [os.path.join(AUDIO_DIR, f"scene{s['id']}_es.mp3") for s in SCENES]
    combined_audio = os.path.join(AUDIO_DIR, "combined_es.mp3")
    concat_audio_files(tts_files, combined_audio)
    
    # Electronic beat-heavy music for TikTok style
    music_file = generate_music_track(60, style="electronic")
    
    # Mix with louder music (music volume 0.3 vs narration 1.0)
    if music_file and combined_audio and os.path.exists(music_file) and os.path.exists(combined_audio):
        # Concat video first
        temp_video = output.replace(".mp4", "_novideo.mp4")
        result = concat_videos(scene_videos, temp_video)
        if result:
            # Mix audio with louder music
            final_cmd = [
                "ffmpeg", "-y",
                "-i", temp_video,
                "-i", combined_audio,
                "-i", music_file,
                "-filter_complex",
                "[1:a]volume=1.0[narr];[2:a]volume=0.35[music];[narr][music]amix=inputs=2:duration=first[outa]",
                "-map", "0:v:0",
                "-map", "[outa]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                output
            ]
            subprocess.run(final_cmd, capture_output=True, text=True)
    
    return output


# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════
if __name__ == "__main__":
    results = {}
    
    # Variation 1
    v1 = generate_variation_1()
    results["video_d1.mp4"] = v1 if v1 and os.path.exists(v1) else None
    print(f"  ➡ video_d1.mp4: {'✅ GENERADO' if results['video_d1.mp4'] else '❌ FALLÓ'}")
    
    # Variation 2
    v2 = generate_variation_2()
    results["video_d2.mp4"] = v2 if v2 and os.path.exists(v2) else None
    print(f"  ➡ video_d2.mp4: {'✅ GENERADO' if results['video_d2.mp4'] else '❌ FALLÓ'}")
    
    # Variation 3
    v3 = generate_variation_3()
    results["video_d3.mp4"] = v3 if v3 and os.path.exists(v3) else None
    print(f"  ➡ video_d3.mp4: {'✅ GENERADO' if results['video_d3.mp4'] else '❌ FALLÓ'}")
    
    # Variation 4
    v4 = generate_variation_4()
    results["video_d4.mp4"] = v4 if v4 and os.path.exists(v4) else None
    print(f"  ➡ video_d4.mp4: {'✅ GENERADO' if results['video_d4.mp4'] else '❌ FALLÓ'}")
    
    # Variation 5
    v5 = generate_variation_5()
    results["video_d5.mp4"] = v5 if v5 and os.path.exists(v5) else None
    print(f"  ➡ video_d5.mp4: {'✅ GENERADO' if results['video_d5.mp4'] else '❌ FALLÓ'}")
    
    print("\n" + "="*60)
    print("📊 RESULTADOS FINALES")
    print("="*60)
    for name, path in results.items():
        if path and os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  ✅ {name}: {size/1024:.1f} KB")
        else:
            print(f"  ❌ {name}: NO GENERADO")
    
    # Save results metadata
    json.dump(results, open(os.path.join(RENDERS_DIR, "generation_results.json"), "w"))
