#!/usr/bin/env python3
"""
Editor Pipeline - Grupo E
Procesa v.mp4 y genera 5 variaciones de edición
"""

import os, sys, json, subprocess, shutil
from datetime import datetime, timezone

BASE = "/home/vuos/code/p3/s51"
SRC_VIDEO = os.path.join(BASE, "v.mp4")
CLIPS_DIR = os.path.join(BASE, "output", "clips")
RENDERS_DIR = os.path.join(BASE, "output", "renders")
REPORT_DIR = os.path.join(BASE, "reportes")

os.makedirs(CLIPS_DIR, exist_ok=True)
os.makedirs(RENDERS_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# Scene definitions from escenas.yaml
escenas = [
    {"id": 1, "dur": 8,  "desc": "Big Bang - Explosión de energía"},
    {"id": 2, "dur": 10, "desc": "Formación de estrellas - Nebulosas"},
    {"id": 3, "dur": 8,  "desc": "Galaxias - Vía Láctea"},
    {"id": 4, "dur": 8,  "desc": "Sistema Solar - Planetas"},
    {"id": 5, "dur": 8,  "desc": "Tierra - Planeta azul"},
    {"id": 6, "dur": 18, "desc": "Humanidad - Desde el fuego hasta las estrellas"},
]

total_dur = sum(e["dur"] for e in escenas)
print(f"[EDITOR] Total duración escenas: {total_dur}s")
print(f"[EDITOR] Video fuente: {SRC_VIDEO}")

def run(cmd, desc=""):
    print(f"[EDITOR] {desc}")
    print(f"  $ {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ERROR: {r.stderr[:500]}")
        return False
    if r.stderr:
        for line in r.stderr.split("\n")[-3:]:
            if line.strip():
                print(f"  {line}")
    return True

# ──────────────────────────────────────────
# FASE 1: Split v.mp4 into scene clips
# ──────────────────────────────────────────
print("\n" + "="*60)
print("FASE 1: Dividiendo v.mp4 en escenas")
print("="*60)

start = 0
for esc in escenas:
    clip_path = os.path.join(CLIPS_DIR, f"escena{esc['id']}.mp4")
    dur = esc["dur"]
    ok = run(
        f'ffmpeg -y -i "{SRC_VIDEO}" -ss {start} -t {dur} '
        f'-c:v libx264 -c:a aac -pix_fmt yuv420p -preset fast '
        f'"{clip_path}" 2>&1',
        f"Escena {esc['id']}: {esc['desc']} ({dur}s)"
    )
    if ok:
        print(f"  ✅ Clip creado: {clip_path}")
    else:
        print(f"  ❌ Error creando clip {esc['id']}")
    start += dur

# Verify clips exist
clips_disponibles = sorted([
    f for f in os.listdir(CLIPS_DIR) if f.endswith(".mp4")
])
print(f"\n[EDITOR] Clips disponibles: {len(clips_disponibles)}")
for c in clips_disponibles:
    path = os.path.join(CLIPS_DIR, c)
    size = os.path.getsize(path)
    print(f"  - {c} ({size/1024:.0f} KB)")

