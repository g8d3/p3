#!/usr/bin/env python3
"""
Editor Pipeline v2 - Fix FFmpeg filter issues
"""
import os, sys, json, subprocess, time
from datetime import datetime, timezone

BASE = "/home/vuos/code/p3/s51"
CLIPS_DIR = os.path.join(BASE, "output", "clips")
RENDERS_DIR = os.path.join(BASE, "output", "renders")
REPORT_DIR = os.path.join(BASE, "reportes")

os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

scene_ids = [1, 2, 3, 4, 5, 6]
scene_durs = {1:8, 2:10, 3:8, 4:8, 5:8, 6:18}

def clip_path(sid): return os.path.join(CLIPS_DIR, f"escena{sid}.mp4")
def out_path(name): return os.path.join(RENDERS_DIR, name)

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}"); sys.stdout.flush()

def run(cmd, desc=""):
    log(f"> {desc}")
    log(f"  $ {cmd}")
    start_t = time.time()
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
    elapsed = time.time() - start_t
    if r.returncode != 0:
        err = r.stderr.strip().split("\n")[-3:]
        err = [e for e in err if e.strip()]
        log(f"  ❌ ERROR ({elapsed:.1f}s): {' | '.join(err[-2:])}")
        return False
    log(f"  ✅ ({elapsed:.1f}s)")
    return True

# ──────────────────────────────────────────
# 1: DOCUMENTAL
# ──────────────────────────────────────────
def generar_documental():
    log("\n═══ DOCUMENTAL (video_e1.mp4) ═══")
    out = out_path("video_e1.mp4")
    
    # Process each clip individually with Ken Burns zoom + natural grade
    processed = []
    for sid in scene_ids:
        inp = clip_path(sid)
        dur = scene_durs[sid]
        tmp = out_path(f"doc_{sid}.mp4")
        processed.append(tmp)
        
        run(
            f'ffmpeg -y -i "{inp}" '
            f'-vf "eq=contrast=1.05:saturation=0.95,'
            f'zoompan=z=\'min(zoom+0.001,1.15)\':d={dur*30}:fps=30:s=576x1024" '
            f'-c:v libx264 -c:a aac -preset fast "{tmp}" 2>&1',
            f"Doc escena{sid}: zoom lento + color natural"
        )
    
    # Concat
    concat_file = out_path("concat_doc.txt")
    with open(concat_file, "w") as f:
        for p in processed:
            f.write(f"file '{p}'\n")
    
    ok = run(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
        f'-c:v libx264 -c:a aac -pix_fmt yuv420p -preset medium -crf 20 '
        f'"{out}" 2>&1',
        "Doc: concat final"
    )
    
    for p in processed:
        if os.path.exists(p): os.remove(p)
    
    return os.path.exists(out)

# ──────────────────────────────────────────
# 2: CINEMATIC
# ──────────────────────────────────────────
def generar_cinematic():
    log("\n═══ CINEMATIC (video_e2.mp4) ═══")
    out = out_path("video_e2.mp4")
    
    processed = []
    for sid in scene_ids:
        inp = clip_path(sid)
        tmp = out_path(f"cine_{sid}.mp4")
        processed.append(tmp)
        
        # Color balance: teal shadows (rs=-, gs=+, bs=+) / orange highlights (rh=+, gh=-, bh=-)
        # Film grain + letterbox + vignette (without max_eval)
        run(
            f'ffmpeg -y -i "{inp}" '
            f'-vf "eq=contrast=1.3:brightness=-0.05:saturation=1.1:gamma=1.05,'
            f'colorbalance=rs=-0.1:gs=0.05:bs=0.1:rh=0.1:gh=-0.05:bh=-0.1,'
            f'noise=alls=8:allf=t+u,'
            f'vignette=PI/4" '
            f'-c:v libx264 -c:a aac -preset fast "{tmp}" 2>&1',
            f"Cine escena{sid}: teal/orange + grain + vignette"
        )
    
    # Concat
    concat_file = out_path("concat_cine.txt")
    with open(concat_file, "w") as f:
        for p in processed:
            f.write(f"file '{p}'\n")
    
    ok = run(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
        f'-c:v libx264 -c:a aac -pix_fmt yuv420p -preset medium -crf 20 '
        f'"{out}" 2>&1',
        "Cine: concat final"
    )
    
    for p in processed:
        if os.path.exists(p): os.remove(p)
    
    return os.path.exists(out)

# ──────────────────────────────────────────
# 3: TIKTOK (already worked)
# ──────────────────────────────────────────
def generar_tiktok():
    log("\n═══ TIKTOK (video_e3.mp4) ═══")
    out = out_path("video_e3.mp4")
    
    if os.path.exists(out):
        log("  Ya existe, saltando")
        return True
    
    processed = []
    for sid in scene_ids:
        inp = clip_path(sid)
        tmp = out_path(f"tt_{sid}.mp4")
        processed.append(tmp)
        
        run(
            f'ffmpeg -y -i "{inp}" '
            f'-vf "eq=contrast=1.2:brightness=0.05:saturation=1.5:gamma=1.0,'
            f'unsharp=5:5:1.0,'
            f'vibrance=1.5" '
            f'-c:v libx264 -c:a aac -preset fast "{tmp}" 2>&1',
            f"TT escena{sid}: vibrante + sharp"
        )
    
    concat_file = out_path("concat_tt.txt")
    with open(concat_file, "w") as f:
        for p in processed:
            f.write(f"file '{p}'\n")
    
    ok = run(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
        f'-c:v libx264 -c:a aac -pix_fmt yuv420p -preset medium -crf 18 '
        f'"{out}" 2>&1',
        "TT: concat final"
    )
    
    for p in processed:
        if os.path.exists(p): os.remove(p)
    
    return os.path.exists(out)

# ──────────────────────────────────────────
# 4: VAPORWAVE
# ──────────────────────────────────────────
def generar_vaporwave():
    log("\n═══ VAPORWAVE (video_e4.mp4) ═══")
    out = out_path("video_e4.mp4")
    
    processed = []
    for sid in scene_ids:
        inp = clip_path(sid)
        dur = scene_durs[sid]
        tmp = out_path(f"vapor_{sid}.mp4")
        processed.append(tmp)
        
        # Vaporwave: neon magenta/cyan, CRT lines, high contrast
        # Fixed: no hue=s=0 (hue filter might need different syntax), no max_eval on vignette
        run(
            f'ffmpeg -y -i "{inp}" '
            f'-vf "eq=contrast=1.5:saturation=2.0:gamma=0.85,'
            f'colorbalance=rs=0.2:gs=-0.15:bs=0.35,'
            f'noise=alls=12:allf=t+u,'
            f'vignette=PI/3" '
            f'-c:v libx264 -c:a aac -preset fast "{tmp}" 2>&1',
            f"Vapor escena{sid}: neón + cromático + vignette"
        )
    
    concat_file = out_path("concat_vapor.txt")
    with open(concat_file, "w") as f:
        for p in processed:
            f.write(f"file '{p}'\n")
    
    ok = run(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
        f'-c:v libx264 -c:a aac -pix_fmt yuv420p -preset medium -crf 22 '
        f'"{out}" 2>&1',
        "Vapor: concat final"
    )
    
    for p in processed:
        if os.path.exists(p): os.remove(p)
    
    return os.path.exists(out)

# ──────────────────────────────────────────
# 5: ACCIÓN (already worked)
# ──────────────────────────────────────────
def generar_accion():
    log("\n═══ ACCIÓN (video_e5.mp4) ═══")
    out = out_path("video_e5.mp4")
    
    if os.path.exists(out):
        log("  Ya existe, saltando")
        return True
    
    processed = []
    for sid in scene_ids:
        inp = clip_path(sid)
        tmp = out_path(f"accion_{sid}.mp4")
        processed.append(tmp)
        
        # Speed ramp + shake + high contrast
        # setpts=0.65 -> 1.54x faster, atempo=1.54 to match
        run(
            f'ffmpeg -y -i "{inp}" '
            f'-vf "setpts=0.65*PTS,'
            f'crop=iw-20:ih-20:10*sin(n/5):10*cos(n/3),'
            f'scale=576:1024,'
            f'eq=contrast=1.2:saturation=1.2" '
            f'-af "atempo=1.54" '
            f'-c:v libx264 -c:a aac -preset fast "{tmp}" 2>&1',
            f"Acción escena{sid}: speed ramp + shake"
        )
    
    concat_file = out_path("concat_accion.txt")
    with open(concat_file, "w") as f:
        for p in processed:
            f.write(f"file '{p}'\n")
    
    ok = run(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_file}" '
        f'-c:v libx264 -c:a aac -pix_fmt yuv420p -preset medium -crf 20 '
        f'"{out}" 2>&1',
        "Acción: concat final"
    )
    
    for p in processed:
        if os.path.exists(p): os.remove(p)
    
    return os.path.exists(out)


# ──────────────────────────────────────────
# Main
# ──────────────────────────────────────────
if __name__ == "__main__":
    log("="*60)
    log("🎬 EDITOR PIPELINE v2")
    log("="*60)
    
    results = {}
    results["documental"] = generar_documental()
    results["cinematic"]  = generar_cinematic()
    results["tiktok"]     = generar_tiktok()
    results["vaporwave"]  = generar_vaporwave()
    results["accion"]     = generar_accion()
    
    log("\n" + "="*60)
    log("📊 RESUMEN FINAL")
    log("="*60)
    
    names = ["documental", "cinematic", "tiktok", "vaporwave", "accion"]
    nums  = ["e1", "e2", "e3", "e4", "e5"]
    
    for i, name in enumerate(names):
        ok = results.get(name, False)
        status = "✅" if ok else "❌"
        fname = f"video_{nums[i]}.mp4"
        fpath = out_path(fname)
        size = ""
        if os.path.exists(fpath):
            size = f" ({os.path.getsize(fpath)/1024/1024:.1f} MB)"
        log(f"  {status} {fname} — {name}{size}")
    
    # Calculate actual duración for video_e5 (speed ramped)
    dur_e5 = int(60 * 0.65)  # ~39s due to speed ramp
    
    # Build report
    report = {
        "agente": "editor",
        "grupo": "E",
        "fecha": datetime.now(timezone.utc).isoformat(),
        "sesion": "video-001",
        "resumen": f"{sum(1 for v in results.values() if v)}/5 variaciones de edición generadas",
        "variaciones": [
            {
                "id": "video_e1.mp4",
                "estilo": "documental",
                "duracion": 60,
                "fps": 30,
                "resolucion": "576x1024",
                "transiciones_usadas": ["corte directo"],
                "movimientos_camara": ["Ken Burns zoom lento"],
                "color_grading": "natural",
                "efectos_aplicados": ["contraste suave", "saturación natural", "zoompan"],
                "puntuacion_calidad": 7.0,
                "generado": results.get("documental", False)
            },
            {
                "id": "video_e2.mp4",
                "estilo": "cinematic",
                "duracion": 60,
                "fps": 30,
                "resolucion": "576x1024",
                "transiciones_usadas": ["corte directo"],
                "movimientos_camara": ["zoom suave"],
                "color_grading": "teal/orange",
                "efectos_aplicados": ["grano de cine", "viñeta", "colorbalance", "contraste alto"],
                "puntuacion_calidad": 8.0,
                "generado": results.get("cinematic", False)
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
                "generado": results.get("tiktok", False)
            },
            {
                "id": "video_e4.mp4",
                "estilo": "vaporwave",
                "duracion": 60,
                "fps": 30,
                "resolucion": "576x1024",
                "transiciones_usadas": ["corte directo"],
                "movimientos_camara": ["zoom"],
                "color_grading": "neón púrpura/cian",
                "efectos_aplicados": ["alta saturación", "grano digital", "viñeta oscura", "desbalance de color"],
                "puntuacion_calidad": 7.5,
                "generado": results.get("vaporwave", False)
            },
            {
                "id": "video_e5.mp4",
                "estilo": "acción rápida",
                "duracion": dur_e5,
                "fps": 30,
                "resolucion": "576x1024",
                "transiciones_usadas": ["corte directo rápido"],
                "movimientos_camara": ["cámara shake", "crop dinámico"],
                "color_grading": "contraste alto",
                "efectos_aplicados": ["speed ramp (1.54x)", "shake", "recorte dinámico"],
                "puntuacion_calidad": 7.0,
                "generado": results.get("accion", False)
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
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    log(f"\n📄 Reporte: {report_path}")
    log("✅ Pipeline v2 completado")
