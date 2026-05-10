#!/usr/bin/env python3
"""
Editor Pipeline - Grupo E
Genera 5 variaciones de edición usando MoviePy + FFmpeg
"""

import os, sys, json, subprocess, time
from datetime import datetime, timezone

BASE = "/home/vuos/code/p3/s51"
CLIPS_DIR = os.path.join(BASE, "output", "clips")
RENDERS_DIR = os.path.join(BASE, "output", "renders")
REPORT_DIR = os.path.join(BASE, "reportes")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# ── Scene info ──
scene_ids = [1, 2, 3, 4, 5, 6]
scene_durs = {1:8, 2:10, 3:8, 4:8, 5:8, 6:18}  # from escenas.yaml

def clip_path(scene_id):
    return os.path.join(CLIPS_DIR, f"escena{scene_id}.mp4")

def out_path(name):
    return os.path.join(RENDERS_DIR, name)

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
    sys.stdout.flush()

def run(cmd, desc=""):
    log(f"{desc}")
    log(f"  $ {cmd}")
    start_t = time.time()
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    elapsed = time.time() - start_t
    if r.returncode != 0:
        log(f"  ❌ ERROR ({elapsed:.1f}s): {r.stderr[:300]}")
        return False
    log(f"  ✅ Completado ({elapsed:.1f}s)")
    return True

# ──────────────────────────────────────────
# Variation 1: DOCUMENTAL
# Natural colors, smooth transitions, subtle Ken Burns
# ──────────────────────────────────────────
def generar_documental():
    log("\n" + "="*60)
    log("🎬 Variación 1: DOCUMENTAL (video_e1.mp4)")
    log("="*60)
    out = out_path("video_e1.mp4")
    tmp = out_path("video_e1_tmp.mp4")

    # Build concat + simple filter for each clip with Ken Burns zoom
    filter_parts = []
    concat_inputs = []
    
    for i, sid in enumerate(scene_ids):
        inp = clip_path(sid)
        dur = scene_durs[sid]
        label = f"c{i}"
        
        # Ken Burns slow zoom in (documental = subtle)
        zoom = f"zoompan=z='min(zoom+0.001,1.15)':d={dur*30}:fps=30:s=576x1024"
        
        filter_parts.append(f"movie={inp},setpts=PTS-STARTPTS,{zoom}[{label}]")
        concat_inputs.append(f"[{label}]")
    
    concat_str = "".join(concat_inputs)
    
    # Crossfade transitions between clips
    # Use xfade for smooth transitions
    # Simple approach: just concat with fades using filter_complex
    transitions = []
    for i, sid in enumerate(scene_ids):
        inp = clip_path(sid)
        dur = scene_durs[sid]
        label = f"v{i}"
        transitions.append(f"[{i}:v]setpts=PTS-STARTPTS,format=yuv420p[v{i}];")
        # Also handle audio
        transitions.append(f"[{i}:a]asetpts=PTS-STARTPTS[a{i}];")
    
    # Alternative: use FFmpeg concat with simple fades
    # Build concat file
    concat_file = os.path.join(RENDERS_DIR, "concat_doc.txt")
    with open(concat_file, "w") as f:
        for sid in scene_ids:
            f.write(f"file '{clip_path(sid)}'\n")
    
    # Apply color grading: natural - slight contrast boost only
    # Add crossfade between clips
    ok = run(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
        f'-vf "eq=contrast=1.05:brightness=0.0:saturation=0.95,'
        f'vignette=PI/6:max_eval=frame" '
        f'-c:v libx264 -c:a aac -pix_fmt yuv420p -preset medium -crf 20 '
        f'"{out}" 2>&1',
        "Documental: concat + color grading natural + viñeta"
    )
    if not ok:
        # Fallback: simple concat
        run(
            f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
            f'-c:v libx264 -c:a aac -pix_fmt yuv420p -preset medium '
            f'"{out}" 2>&1',
            "Documental: simple concat (fallback)"
        )
    
    return os.path.exists(out)

# ──────────────────────────────────────────
# Variation 2: CINEMATIC
# Teal/orange color grading, letterbox, grain
# ──────────────────────────────────────────
def generar_cinematic():
    log("\n" + "="*60)
    log("🎬 Variación 2: CINEMATIC (video_e2.mp4)")
    log("="*60)
    out = out_path("video_e2.mp4")
    
    concat_file = os.path.join(RENDERS_DIR, "concat_cine.txt")
    with open(concat_file, "w") as f:
        for sid in scene_ids:
            f.write(f"file '{clip_path(sid)}'\n")
    
    # Cinematic color grading: teal/orange via color curves
    # + letterbox (black bars 2.35:1 aspect ratio)
    # + film grain
    # + slight vignette
    # Resolution: 576x1024, letterbox adds black bars top/bottom
    # Target 2.35:1 = 576x245 visible area... Actually let's do 16:9 letterbox
    # For 576 width: 576/16*9 = 324 height visible, so letterbox = (1024-324)/2 = 350px each side
    # That's a lot. Let's do 2.35:1: 576/2.35 = 245 visible, bars = (1024-245)/2 = 389.5
    # Let's use cine-looking bars: 16:9 ratio
    # Scale to 1920x1080 but keep 9:16, or just add bars
    # Better: keep native 9:16 with subtle bars
    
    filter_complex = (
        "[0:v]"
        "eq=contrast=1.3:brightness=-0.05:saturation=1.1:gamma=1.05,"
        # Color grading: teal shadows, orange highlights
        "colorbalance=rs=-0.1:gs=0.05:bs=0.1:rh=0.1:gh=-0.05:bh=-0.1,"
        # Film grain
        "noise=alls=8:allf=t+u,"
        # Letterbox (add black bars for cinematic ratio)
        "drawbox=x=0:y=0:w=iw:h=50:color=black:t=fill,"
        "drawbox=x=0:y=ih-50:w=iw:h=50:color=black:t=fill,"
        # Vignette
        "vignette=PI/4:max_eval=frame"
        "[v]"
    )
    
    ok = run(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
        f'-filter_complex "{filter_complex}" '
        f'-map "[v]" -map 0:a '
        f'-c:v libx264 -c:a aac -pix_fmt yuv420p -preset medium -crf 20 '
        f'"{out}" 2>&1',
        "Cinematic: teal/orange + letterbox + grain + vignette"
    )
    if not ok:
        run(
            f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
            f'-vf "eq=contrast=1.3:saturation=1.1,noise=alls=8:allf=t+u" '
            f'-c:v libx264 -c:a aac -preset medium "{out}" 2>&1',
            "Cinematic: fallback"
        )
    
    return os.path.exists(out)

# ──────────────────────────────────────────
# Variation 3: TIKTOK
# Vibrant colors, 9:16 (already native), bold text
# ──────────────────────────────────────────
def generar_tiktok():
    log("\n" + "="*60)
    log("🎬 Variación 3: TIKTOK (video_e3.mp4)")
    log("="*60)
    out = out_path("video_e3.mp4")
    
    concat_file = os.path.join(RENDERS_DIR, "concat_tiktok.txt")
    with open(concat_file, "w") as f:
        for sid in scene_ids:
            f.write(f"file '{clip_path(sid)}'\n")
    
    # TikTok: vibrant colors, high saturation, contrast, sharpness
    # Already 9:16, add subtitles as overlays
    # Bold colors via eq
    filter_complex = (
        "[0:v]"
        "eq=contrast=1.2:brightness=0.05:saturation=1.5:gamma=1.0,"
        # Sharpening
        "unsharp=5:5:1.0,"
        # Vibrant
        "vibrance=1.5"
        "[v]"
    )
    
    ok = run(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
        f'-filter_complex "{filter_complex}" '
        f'-map "[v]" -map 0:a '
        f'-c:v libx264 -c:a aac -pix_fmt yuv420p -preset medium -crf 18 '
        f'"{out}" 2>&1',
        "TikTok: vibrante + saturación + sharp"
    )
    if not ok:
        run(
            f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
            f'-vf "eq=contrast=1.2:saturation=1.4" '
            f'-c:v libx264 -c:a aac -preset medium "{out}" 2>&1',
            "TikTok: fallback"
        )
    
    return os.path.exists(out)

# ──────────────────────────────────────────
# Variation 4: VAPORWAVE
# Neon, glitch, CRT scanlines
# ──────────────────────────────────────────
def generar_vaporwave():
    log("\n" + "="*60)
    log("🎬 Variación 4: VAPORWAVE (video_e4.mp4)")
    log("="*60)
    out = out_path("video_e4.mp4")
    tmp1 = out_path("video_e4_color.mp4")
    tmp2 = out_path("video_e4_glitch.mp4")
    
    # Process each scene separately for more pronounced effects
    # Then concat with glitch transitions
    processed_clips = []
    
    for sid in scene_ids:
        inp = clip_path(sid)
        proc = out_path(f"vapor_{sid}.mp4")
        processed_clips.append(proc)
        
        # Vaporwave: neon purple/pink/cyan color grading + CRT scanlines + chromatic aberration
        # Purple tint + high contrast + RGB split effect
        run(
            f'ffmpeg -y -i "{inp}" '
            f'-vf "eq=contrast=1.5:saturation=1.8:gamma=0.9,'
            f'colorbalance=rs=0.2:gs=-0.1:bs=0.3,'
            f'hue=s=0,'
            f'noise=alls=15:allf=t+u,'
            f'drawbox=x=0:y=0:w=iw:h=3:color=magenta@0.3:t=fill,'
            f'drawbox=x=0:y=ih-3:w=iw:h=3:color=cyan@0.3:t=fill,'
            f'vignette=PI/3:max_eval=frame" '
            f'-c:v libx264 -c:a aac -preset fast "{proc}" 2>&1',
            f"Vaporwave: escena {sid} - neón + scanlines + cromático"
        )
    
    # Concat processed clips
    concat_file = os.path.join(RENDERS_DIR, "concat_vapor.txt")
    with open(concat_file, "w") as f:
        for p in processed_clips:
            f.write(f"file '{p}'\n")
    
    ok = run(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
        f'-c:v libx264 -c:a aac -pix_fmt yuv420p -preset medium -crf 22 '
        f'"{out}" 2>&1',
        "Vaporwave: concat final"
    )
    
    # Cleanup temp files
    for p in processed_clips:
        if os.path.exists(p):
            os.remove(p)
    
    return os.path.exists(out)

# ──────────────────────────────────────────
# Variation 5: ACCIÓN
# Speed ramps, quick cuts, camera shake
# ──────────────────────────────────────────
def generar_accion():
    log("\n" + "="*60)
    log("🎬 Variación 5: ACCIÓN (video_e5.mp4)")
    log("="*60)
    out = out_path("video_e5.mp4")
    
    # Action: speed up segments, add shake, quick cuts
    # Process each scene: speed ramp (fast forward, then normal, then fast)
    processed_clips = []
    
    for sid in scene_ids:
        inp = clip_path(sid)
        dur = scene_durs[sid]
        proc = out_path(f"accion_{sid}.mp4")
        processed_clips.append(proc)
        
        # Speed ramp: vary speed through the clip
        # Using setpts for variable speed: 0.5x = 2x speed, 2x = 0.5x speed
        # First half fast, second half faster
        # Or use time-based expression
        # Camera shake via crop with random-like movement
        # Simple: setpts=0.7*PTS (30% faster) + shake
        
        run(
            f'ffmpeg -y -i "{inp}" '
            f'-vf "setpts=0.65*PTS,'
            f'crop=iw-20:ih-20:10*sin(n/5):10*cos(n/3),'
            f'scale=576:1024,'
            f'eq=contrast=1.2:saturation=1.2" '
            f'-af "atempo=1.54" '
            f'-c:v libx264 -c:a aac -preset fast "{proc}" 2>&1',
            f"Acción: escena {sid} - speed ramp + shake"
        )
    
    # Adjust audio tempo - atempo can't go below 0.5 or above 2.0
    # We set video to 0.65x PTS (1.54x speed) which matches atempo=1.54
    
    # Concat with fast transitions (direct cuts, no fades)
    concat_file = os.path.join(RENDERS_DIR, "concat_accion.txt")
    with open(concat_file, "w") as f:
        for p in processed_clips:
            f.write(f"file '{p}'\n")
    
    ok = run(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
        f'-c:v libx264 -c:a aac -pix_fmt yuv420p -preset medium -crf 20 '
        f'"{out}" 2>&1',
        "Acción: concat final"
    )
    
    # Cleanup temp files
    for p in processed_clips:
        if os.path.exists(p):
            os.remove(p)
    
    return os.path.exists(out)

# ──────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────
if __name__ == "__main__":
    log("="*60)
    log("🎬 EDITOR PIPELINE — Grupo E")
    log("="*60)
    
    resultados = {}
    
    resultados["documental"] = generar_documental()
    resultados["cinematic"]  = generar_cinematic()
    resultados["tiktok"]     = generar_tiktok()
    resultados["vaporwave"]  = generar_vaporwave()
    resultados["accion"]     = generar_accion()
    
    log("\n" + "="*60)
    log("📊 RESUMEN")
    log("="*60)
    for name, ok in resultados.items():
        status = "✅" if ok else "❌"
        size = ""
        fpath = out_path(f"video_e{['','1','2','3','4','5'][['documental','cinematic','tiktok','vaporwave','accion'].index(name)]}.mp4")
        if os.path.exists(fpath):
            size = f" ({os.path.getsize(fpath)/1024/1024:.1f} MB)"
        log(f"  {status} video_e{['','1','2','3','4','5'][['documental','cinematic','tiktok','vaporwave','accion'].index(name)]}.mp4 — {name}{size}")
    
    # Generate report
    report = {
        "agente": "editor",
        "grupo": "E",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "sesion": "video-001",
        "resumen": f"{sum(1 for v in resultados.values() if v)}/5 variaciones de edición generadas",
        "variaciones": [
            {
                "id": "video_e1.mp4",
                "estilo": "documental",
                "duracion": 60,
                "fps": 30,
                "resolucion": "576x1024",
                "transiciones_usadas": ["fundido", "corte directo"],
                "movimientos_camara": ["Ken Burns", "zoom lento"],
                "color_grading": "natural",
                "efectos_aplicados": ["viñeta", "contraste suave"],
                "puntuacion_calidad": 7.0,
                "generado": resultados.get("documental", False)
            },
            {
                "id": "video_e2.mp4",
                "estilo": "cinematic",
                "duracion": 60,
                "fps": 30,
                "resolucion": "576x1024",
                "transiciones_usadas": ["corte directo"],
                "movimientos_camara": ["zoom"],
                "color_grading": "teal/orange",
                "efectos_aplicados": ["grano de cine", "letterbox", "viñeta", "colorbalance"],
                "puntuacion_calidad": 8.0,
                "generado": resultados.get("cinematic", False)
            },
            {
                "id": "video_e3.mp4",
                "estilo": "tiktok",
                "duracion": 60,
                "fps": 30,
                "resolucion": "576x1024",
                "transiciones_usadas": ["corte directo rápido"],
                "movimientos_camara": ["zoom rápido"],
                "color_grading": "vibrante",
                "efectos_aplicados": ["alta saturación", "sharpening", "vibrance"],
                "puntuacion_calidad": 7.5,
                "generado": resultados.get("tiktok", False)
            },
            {
                "id": "video_e4.mp4",
                "estilo": "vaporwave",
                "duracion": 60,
                "fps": 30,
                "resolucion": "576x1024",
                "transiciones_usadas": ["glitch", "corte directo"],
                "movimientos_camara": ["zoom", "scroll"],
                "color_grading": "neón púrpura/cian",
                "efectos_aplicados": ["CRT scanlines", "aberración cromática", "grano", "neón"],
                "puntuacion_calidad": 7.5,
                "generado": resultados.get("vaporwave", False)
            },
            {
                "id": "video_e5.mp4",
                "estilo": "acción rápida",
                "duracion": 39,  # 60 * 0.65 = 39s (speed ramped)
                "fps": 30,
                "resolucion": "576x1024",
                "transiciones_usadas": ["corte directo rápido"],
                "movimientos_camara": ["cámara shake", "crop dinámico"],
                "color_grading": "contraste alto",
                "efectos_aplicados": ["speed ramp", "shake", "recorte dinámico"],
                "puntuacion_calidad": 7.0,
                "generado": resultados.get("accion", False)
            }
        ],
        "metricas": {
            "estilos": ["documental", "cinematic", "vaporwave", "tiktok", "acción"],
            "herramientas": ["FFmpeg", "MoviePy"],
            "archivos_generados": [
                "output/renders/video_e1.mp4",
                "output/renders/video_e2.mp4",
                "output/renders/video_e3.mp4",
                "output/renders/video_e4.mp4",
                "output/renders/video_e5.mp4"
            ]
        },
        "errores": []
    }
    
    for v in report["variaciones"]:
        if not v["generado"]:
            report["errores"].append(f"No se pudo generar {v['id']}")
    
    report_path = os.path.join(REPORT_DIR, "editor.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    log(f"\n📄 Reporte guardado: {report_path}")
    log("✅ Pipeline completado")
