#!/usr/bin/env python3
"""
ShortGPT Pipeline - Grupo D (Simplified)
Genera 5 variaciones de shorts usando FFmpeg + TTS Chutes.

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
import shlex

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
        "bg": "0x000011",
        "text_color": "white",
        "text": "Hace 13.8 mil millones de años...",
        "subtext": "¡El universo nació con una explosión! 🔥",
        "tts_es": "scene1_es.mp3",
        "tts_en": "scene1_en.mp3"
    },
    {
        "id": 2, "duration": 12,
        "title": "ESTRELLAS Y GALAXIAS",
        "bg": "0x0A001A",
        "text_color": "0xFF66AA",
        "text": "La gravedad unió el polvo cósmico",
        "subtext": "Nacieron miles de millones de estrellas ✨",
        "tts_es": "scene2_es.mp3",
        "tts_en": "scene2_en.mp3"
    },
    {
        "id": 3, "duration": 8,
        "title": "SISTEMA SOLAR",
        "bg": "0x1A0A00",
        "text_color": "0xFFAA00",
        "text": "El Sol encendió su fuego termonuclear",
        "subtext": "Planetas danzando a su alrededor 🪐",
        "tts_es": "scene3_es.mp3",
        "tts_en": "scene3_en.mp3"
    },
    {
        "id": 4, "duration": 12,
        "title": "ORIGEN DE LA VIDA",
        "bg": "0x001122",
        "text_color": "0x00FF88",
        "text": "El caos químico dio paso al milagro",
        "subtext": "La vida encontró su camino 🌱",
        "tts_es": "scene4_es.mp3",
        "tts_en": "scene4_en.mp3"
    },
    {
        "id": 5, "duration": 8,
        "title": "EVOLUCIÓN HUMANA",
        "bg": "0x221100",
        "text_color": "0xFFDD00",
        "text": "Una especie desarrolló conciencia",
        "subtext": "Miramos al cielo y preguntamos... 🧠",
        "tts_es": "scene5_es.mp3",
        "tts_en": "scene5_en.mp3"
    },
    {
        "id": 6, "duration": 12,
        "title": "POLVO DE ESTRELLAS",
        "bg": "0x000022",
        "text_color": "0x88AAFF",
        "text": "Somos polvo de estrellas",
        "subtext": "El viaje continúa... 🚀",
        "tts_es": "scene6_es.mp3",
        "tts_en": "scene6_en.mp3"
    }
]

def quote(s):
    """Escape string for shell."""
    return shlex.quote(str(s))

def generate_scene_video_simple(scene, font_size=48, tts_file=None, duration_override=None):
    """
    Generate a scene video with simple FFmpeg command.
    Uses -vf (filter graph) instead of complex filter_complex.
    """
    scene_id = scene["id"]
    duration = duration_override if duration_override else scene["duration"]
    bg = scene["bg"]
    
    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    
    # Build drawtext filters
    # Title at top
    title_filter = (
        f"drawtext=text='{scene['title']}':"
        f"fontfile={font_bold}:fontsize={font_size}:fontcolor=white:"
        f"box=1:boxcolor=black@0.5:"
        f"x=(w-text_w)/2:y=h*0.1:enable='between(t,0,{duration})'"
    )
    
    # Main text
    main_filter = (
        f"drawtext=text='{scene['text']}':"
        f"fontfile={font_reg}:fontsize={int(font_size*0.65)}:fontcolor=white:"
        f"box=1:boxcolor=black@0.4:"
        f"x=(w-text_w)/2:y=h*0.72:enable='between(t,0,{duration})'"
    )
    
    # Subtext / call to action
    sub_filter = (
        f"drawtext=text='{scene['subtext']}':"
        f"fontfile={font_reg}:fontsize={int(font_size*0.55)}:fontcolor={scene['text_color']}:"
        f"box=1:boxcolor=black@0.3:"
        f"x=(w-text_w)/2:y=h*0.85:enable='between(t,0,{duration})'"
    )
    
    # Combine all drawtext with commas
    vf = f"{title_filter},{main_filter},{sub_filter}"
    
    output_file = os.path.join(RENDERS_DIR, f"scene{scene_id}_tmp.mp4")
    
    if tts_file and os.path.exists(tts_file):
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={bg}:s=1080x1920:d={duration}:r=30",
            "-i", tts_file,
            "-vf", vf,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            output_file
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={bg}:s=1080x1920:d={duration}:r=30",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            output_file
        ]
    
    print(f"  Scene {scene_id}: {duration}s, font={font_size}", end="")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f" ❌\n  {result.stderr[-300:]}")
        return None
    print(f" ✅ ({os.path.getsize(output_file)/1024:.0f} KB)")
    return output_file


def concat_scenes(scene_files, output_file, audio_file=None, music_file=None):
    """Concatenate multiple scene videos into one."""
    if not scene_files:
        return None
    
    # Create concat demuxer file
    concat_txt = os.path.join(RENDERS_DIR, "concat.txt")
    with open(concat_txt, "w") as f:
        for sf in scene_files:
            if sf and os.path.exists(sf):
                f.write(f"file '{os.path.abspath(sf)}'\n")
    
    # Concat video streams
    temp_output = output_file.replace(".mp4", "_tmp.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_txt,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        temp_output
    ]
    
    print(f"  Concatenating scenes...", end="")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f" ❌\n{result.stderr[-200:]}")
        return None
    
    # Add audio if provided
    if music_file and os.path.exists(music_file):
        # Mix narration (if available) + music
        if audio_file and os.path.exists(audio_file):
            mix_cmd = [
                "ffmpeg", "-y",
                "-i", temp_output,
                "-i", audio_file,
                "-i", music_file,
                "-filter_complex",
                "[1:a]volume=1.0[narr];[2:a]volume=0.2[music];[narr][music]amix=inputs=2:duration=first[outa]",
                "-map", "0:v:0",
                "-map", "[outa]",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest",
                output_file
            ]
        else:
            # Just music
            mix_cmd = [
                "ffmpeg", "-y",
                "-i", temp_output,
                "-i", music_file,
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "128k",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                output_file
            ]
        print(f"  Adding audio...", end="")
        result = subprocess.run(mix_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f" ❌\n{result.stderr[-200:]}")
            # Keep video-only version
            os.replace(temp_output, output_file)
        else:
            os.remove(temp_output)
    elif audio_file and os.path.exists(audio_file):
        # Just narration
        mix_cmd = [
            "ffmpeg", "-y",
            "-i", temp_output,
            "-i", audio_file,
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_file
        ]
        print(f"  Adding narration...", end="")
        result = subprocess.run(mix_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f" ❌")
            os.replace(temp_output, output_file)
        else:
            os.remove(temp_output)
    else:
        os.replace(temp_output, output_file)
    
    print(f" ✅ ({os.path.getsize(output_file)/1024:.0f} KB)")
    return output_file


def generate_music(duration=60, style="cinematic"):
    """Generate background music track."""
    output = os.path.join(AUDIO_DIR, f"bg_{style}.mp3")
    
    if style == "electronic":
        # Tech beat
        filt = (
            "aevalsrc=exprs="
            "'sin(2*PI*440*T)*0.08+"  # bass
            "sin(2*PI*880*T)*0.04+"   # harmonic
            "sin(2*PI*220*T)*0.12*sin(2*PI*2*T)+"  # wobble
            "pow(sin(2*PI*4*T),20)*0.3':"  # kick
            f"d={duration}:s=44100:c=mono"
        )
    elif style == "cinematic":
        filt = (
            "aevalsrc=exprs="
            "'sin(2*PI*220*T)*0.15*exp(-T*0.08)+"  # epic strings
            "sin(2*PI*330*T)*0.1*sin(2*PI*0.3*T)+"  # pads
            "sin(2*PI*110*T)*0.25+"  # bass drone
            "pow(sin(2*PI*1.5*T),10)*0.15':"  # slow pulse
            f"d={duration}:s=44100:c=mono"
        )
    else:
        filt = f"aevalsrc=exprs='sin(2*PI*432*T)*0.1':d={duration}:s=44100:c=mono"
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", filt,
        "-c:a", "aac", "-b:a", "128k",
        output
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(output):
        return output
    return None


def merge_tts(scene_ids, lang="es"):
    """Concatenate TTS files for all scenes."""
    segments = []
    for sid in scene_ids:
        fname = os.path.join(AUDIO_DIR, f"scene{sid}_{lang}.mp3")
        if os.path.exists(fname):
            segments.append(fname)
    
    if not segments:
        return None
    
    output = os.path.join(AUDIO_DIR, f"combined_{lang}.mp3")
    concat_txt = os.path.join(AUDIO_DIR, f"concat_{lang}.txt")
    
    with open(concat_txt, "w") as f:
        for seg in segments:
            f.write(f"file '{os.path.abspath(seg)}'\n")
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_txt,
        "-c:a", "aac", "-b:a", "128k",
        output
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(output):
        return output
    return None


# ═══════════════════════════════════════
# VARIATION 1: Español, informativo
# ═══════════════════════════════════════
def gen_v1():
    print("\n" + "="*60)
    print("🎬 V1: Short estándar (Español, Voz masculina, Informativo)")
    print("="*60)
    
    scenes = []
    for s in SCENES:
        tts = os.path.join(AUDIO_DIR, s["tts_es"])
        v = generate_scene_video_simple(s, font_size=52, tts_file=tts)
        if v:
            scenes.append(v)
    
    if not scenes:
        return None
    
    combined = os.path.join(RENDERS_DIR, "video_d1.mp4")
    music = generate_music(60, "cinematic")
    result = concat_scenes(scenes, combined, music_file=music)
    return result


# ═══════════════════════════════════════
# VARIATION 2: Inglés, entretenimiento
# ═══════════════════════════════════════
def gen_v2():
    print("\n" + "="*60)
    print("🎬 V2: Short en inglés (Voz femenina, Entretenimiento)")
    print("="*60)
    
    # English scene data
    en_scenes = [
        {"id": 1, "duration": 8, "title": "THE BIG BANG", "bg": "0x000011", "text_color": "white",
         "text": "13.8 billion years ago...", "subtext": "The universe was born! 🔥",
         "tts_es": "scene1_en.mp3", "tts_en": "scene1_en.mp3"},
        {"id": 2, "duration": 12, "title": "STARS & GALAXIES", "bg": "0x0A001A", "text_color": "0xFF66AA",
         "text": "Gravity united cosmic dust", "subtext": "Billions of stars were born ✨",
         "tts_es": "scene2_en.mp3", "tts_en": "scene2_en.mp3"},
        {"id": 3, "duration": 8, "title": "SOLAR SYSTEM", "bg": "0x1A0A00", "text_color": "0xFFAA00",
         "text": "The Sun ignited its fire", "subtext": "Planets dancing around it 🪐",
         "tts_es": "scene3_en.mp3", "tts_en": "scene3_en.mp3"},
        {"id": 4, "duration": 12, "title": "ORIGIN OF LIFE", "bg": "0x001122", "text_color": "0x00FF88",
         "text": "Chemical chaos became a miracle", "subtext": "Life found its way 🌱",
         "tts_es": "scene4_en.mp3", "tts_en": "scene4_en.mp3"},
        {"id": 5, "duration": 8, "title": "HUMAN EVOLUTION", "bg": "0x221100", "text_color": "0xFFDD00",
         "text": "One species gained consciousness", "subtext": "We looked at the sky... 🧠",
         "tts_es": "scene5_en.mp3", "tts_en": "scene5_en.mp3"},
        {"id": 6, "duration": 12, "title": "STARDUST", "bg": "0x000022", "text_color": "0x88AAFF",
         "text": "We are made of stardust", "subtext": "The journey continues... 🚀",
         "tts_es": "scene6_en.mp3", "tts_en": "scene6_en.mp3"}
    ]
    
    # Generate English TTS if not exists
    en_texts = [
        "In the beginning, everything was an infinitely small and dense point. 13.8 billion years ago, that point exploded. The universe was born.",
        "The universe expanded and cooled. Gravity united gas and cosmic dust, igniting billions of stars. Galaxies were born: immense islands of light in the infinite darkness.",
        "In an arm of an ordinary galaxy, a star called the Sun ignited its fire. Around it, planets of rock and gas began to dance: our solar system.",
        "On Earth, chemical chaos gave way to a miracle. Simple molecules combined to create life. First cells, first oceans full of possibilities. Life found its way.",
        "Life evolved, and among all species, one developed consciousness. The human being looked at the sky and asked: what are we?",
        "We are stardust. The universe didn't just create galaxies and planets... it also created eyes to contemplate itself. And the journey continues."
    ]
    
    for i, (s, txt) in enumerate(zip(en_scenes, en_texts)):
        outfile = os.path.join(AUDIO_DIR, f"scene{s['id']}_en.mp3")
        if not os.path.exists(outfile):
            print(f"  TTS EN scene {s['id']}...", end="")
            cmd = ["tts-speak", txt, "--voice", "af_nicole", "--speed", "1.0", "--output", outfile]
            subprocess.run(cmd, capture_output=True, text=True)
            if os.path.exists(outfile):
                print(f" ✅")
            else:
                print(f" ❌")
    
    scenes = []
    for s in en_scenes:
        tts = os.path.join(AUDIO_DIR, s["tts_en"])
        v = generate_scene_video_simple(s, font_size=52, tts_file=tts)
        if v:
            scenes.append(v)
    
    if not scenes:
        return None
    
    combined = os.path.join(RENDERS_DIR, "video_d2.mp4")
    music = generate_music(60, "cinematic")
    result = concat_scenes(scenes, combined, music_file=music)
    return result


# ═══════════════════════════════════════
# VARIATION 3: Kinetic Typography (big text)
# ═══════════════════════════════════════
def gen_v3():
    print("\n" + "="*60)
    print("🎬 V3: Kinetic Typography (Subtítulos gigantes)")
    print("="*60)
    
    scenes = []
    for s in SCENES:
        tts = os.path.join(AUDIO_DIR, s["tts_es"])
        # Much bigger font for kinetic typography
        v = generate_scene_video_simple(s, font_size=82, tts_file=tts)
        if v:
            scenes.append(v)
    
    if not scenes:
        return None
    
    combined = os.path.join(RENDERS_DIR, "video_d3.mp4")
    music = generate_music(60, "electronic")
    result = concat_scenes(scenes, combined, music_file=music)
    return result


# ═══════════════════════════════════════
# VARIATION 4: Ultra-fast rhythm
# ═══════════════════════════════════════
def gen_v4():
    print("\n" + "="*60)
    print("🎬 V4: Ritmo ultra-rápido (cambios cada 2s)")
    print("="*60)
    
    # Split each scene into ~2s segments
    fast_data = []
    segment_texts = {
        1: ["Punto infinitesimal...", "Explotó!", "Nació el universo!"],
        2: ["Universo se expandió", "Gravedad unió polvo", "Estrellas encendidas", "Galaxias nacieron"],
        3: ["Sol encendió fuego", "Planetas danzando", "Sistema solar formado"],
        4: ["Tierra primitiva", "Océanos hirvientes", "Moléculas brillaron", "Vida emergió"],
        5: ["Evolución", "Conciencia humana", "¿Qué somos?"],
        6: ["Polvo de estrellas", "Ojos que contemplan", "Viaje continúa..."]
    }
    
    # Create fast-paced segments
    fast_scenes = []
    for s in SCENES:
        sid = s["id"]
        texts = segment_texts.get(sid, [s["text"]])
        seg_dur = max(1.5, s["duration"] / len(texts))
        for i, t in enumerate(texts):
            fast_scenes.append({
                "id": sid,
                "duration": seg_dur,
                "title": s["title"] if i == 0 else "",
                "bg": s["bg"],
                "text_color": s["text_color"],
                "text": t,
                "subtext": "▶ " * (i+1),
                "tts_es": s["tts_es"]
            })
    
    scenes = []
    for fs in fast_scenes:
        # Generate each segment as separate video without TTS (too short)
        v = generate_scene_video_simple(fs, font_size=58,
                                         duration_override=fs["duration"])
        if v:
            scenes.append(v)
    
    if not scenes:
        return None
    
    # Use combined TTS audio
    combined_audio = merge_tts([s["id"] for s in SCENES], "es")
    combined = os.path.join(RENDERS_DIR, "video_d4.mp4")
    music = generate_music(60, "electronic")
    result = concat_scenes(scenes, combined, audio_file=combined_audio, music_file=music)
    return result


# ═══════════════════════════════════════
# VARIATION 5: TikTok style (electronic music)
# ═══════════════════════════════════════
def gen_v5():
    print("\n" + "="*60)
    print("🎬 V5: Estilo TikTok (Música electrónica + ritmo rápido)")
    print("="*60)
    
    scenes = []
    for s in SCENES:
        tts = os.path.join(AUDIO_DIR, s["tts_es"])
        v = generate_scene_video_simple(s, font_size=52, tts_file=tts)
        if v:
            scenes.append(v)
    
    if not scenes:
        return None
    
    combined = os.path.join(RENDERS_DIR, "video_d5.mp4")
    # Louder electronic music for TikTok style
    music = generate_music(60, "electronic")
    
    # Mix with louder music volume
    combined_audio = merge_tts([s["id"] for s in SCENES], "es")
    
    # Concat video then mix audio
    temp_video = combined.replace(".mp4", "_novideo.mp4")
    result = concat_scenes(scenes, temp_video)
    if result:
        if music and combined_audio and os.path.exists(music) and os.path.exists(combined_audio):
            mix_cmd = [
                "ffmpeg", "-y",
                "-i", temp_video,
                "-i", combined_audio,
                "-i", music,
                "-filter_complex",
                "[1:a]volume=1.0[narr];[2:a]volume=0.4[music];[narr][music]amix=inputs=2:duration=first[outa]",
                "-map", "0:v:0",
                "-map", "[outa]",
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest",
                combined
            ]
            subprocess.run(mix_cmd, capture_output=True, text=True)
            if os.path.exists(combined):
                os.remove(temp_video)
                return combined
    
    return result


# ═══════════════════════════════════════
# MAIN
# ═══════════════════════════════════════
if __name__ == "__main__":
    results = {}
    
    print("🚀 GRUPO D - SHORTS AUTOMÁTICOS")
    print(f"Directorio: {RENDERS_DIR}")
    
    v1 = gen_v1()
    results["video_d1.mp4"] = v1 if v1 and os.path.exists(v1) else None
    print(f"  ➡ video_d1.mp4: {'✅' if results['video_d1.mp4'] else '❌'}")
    
    v2 = gen_v2()
    results["video_d2.mp4"] = v2 if v2 and os.path.exists(v2) else None
    print(f"  ➡ video_d2.mp4: {'✅' if results['video_d2.mp4'] else '❌'}")
    
    v3 = gen_v3()
    results["video_d3.mp4"] = v3 if v3 and os.path.exists(v3) else None
    print(f"  ➡ video_d3.mp4: {'✅' if results['video_d3.mp4'] else '❌'}")
    
    v4 = gen_v4()
    results["video_d4.mp4"] = v4 if v4 and os.path.exists(v4) else None
    print(f"  ➡ video_d4.mp4: {'✅' if results['video_d4.mp4'] else '❌'}")
    
    v5 = gen_v5()
    results["video_d5.mp4"] = v5 if v5 and os.path.exists(v5) else None
    print(f"  ➡ video_d5.mp4: {'✅' if results['video_d5.mp4'] else '❌'}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 RESUMEN FINAL")
    print("="*60)
    for name, path in results.items():
        if path and os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  ✅ {name}: {size/1024:.0f} KB")
        else:
            print(f"  ❌ {name}: NO GENERADO")
    
    # Save metadata
    json.dump(results, open(os.path.join(RENDERS_DIR, "results.json"), "w"), indent=2)
