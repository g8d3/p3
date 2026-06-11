#!/usr/bin/env python3
"""
reviewer_agent.py — Quality reviewer using Mimo v2.5 (vision-capable).

Reviews videos (screenshots), reports, and trading outputs.
Generates structured feedback and writes to progress files.

Usage:
  python3 core/reviewer_agent.py --review-video artifacts/videos/demo.mp4
  python3 core/reviewer_agent.py --review-report trading
  python3 core/reviewer_agent.py --review-report content
  python3 core/reviewer_agent.py --watch       # continuous monitoring mode
"""
import argparse, base64, json, os, subprocess, sys, time, urllib.request
from datetime import datetime
from pathlib import Path

BASE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL = "xiaomi/mimo-v2.5"

LOG_FILE = BASE / "data" / "reviewer.log"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {msg}\n")

def call_mimo(messages, max_tokens=1024):
    payload = {
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    try:
        req = urllib.request.Request(
            API_URL, data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
                "HTTP-Referer": "https://github.com/g8d3/p3",
            },
        )
        r = urllib.request.urlopen(req, timeout=60)
        data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        log(f"Mimo error: {e}")
        return ""

def take_screenshots(video_path, num_shots=4):
    """Extract evenly-spaced frames from video."""
    shots = []
    try:
        dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)]
        duration = float(subprocess.run(dur_cmd, capture_output=True, text=True).stdout.strip())
        interval = duration / (num_shots + 1)
        for i in range(1, num_shots + 1):
            ts = interval * i
            out = BASE / "data" / f"review-shot-{i}.png"
            subprocess.run([
                "ffmpeg", "-ss", str(ts), "-i", str(video_path),
                "-vframes", "1", "-y", str(out)
            ], capture_output=True)
            if out.exists():
                b64 = base64.b64encode(out.read_bytes()).decode()
                shots.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
                out.unlink()
        log(f"{len(shots)} screenshots extracted from {video_path.name}")
    except Exception as e:
        log(f"Screenshot error: {e}")
    return shots

def review_video(video_path):
    log(f"Reviewing video: {video_path}")
    shots = take_screenshots(video_path)
    if not shots:
        return "No se pudieron extraer screenshots"

    messages = [
        {"role": "system", "content": "Eres un revisor de calidad de videos. Revisas si el video tiene contenido visual real (no negro), si la narración coincide con lo que se muestra, y si la calidad es aceptable. Responde en español con una estructura: 1) Resumen 2) Lo que está bien 3) Lo que está mal 4) Recomendaciones."},
        {"role": "user", "content": [
            {"type": "text", "text": "Revisa este video del sistema multi-agente. Las imágenes son frames del video en diferentes tiempos. Dime: ¿el video tiene contenido real? ¿Qué se muestra en cada frame? ¿Hay algo que mejorar?"},
            *shots,
        ]},
    ]
    result = call_mimo(messages)
    log(f"Video review result: {result[:200]}...")
    return result

def review_trading_report():
    log("Reviewing trading report")
    csv_path = BASE / "data" / "trading_log.csv"
    if not csv_path.exists():
        return "No trading data found"

    data = csv_path.read_text()
    messages = [
        {"role": "system", "content": "Eres un revisor de calidad de datos de trading. Analizas señales, detectas problemas, y recomiendas mejoras. Responde en español con estructura: 1) Resumen 2) Señales actuales 3) Problemas detectados 4) Recomendaciones."},
        {"role": "user", "content": f"Revisa este log de señales de trading:\n\n{data}\n\nEvalúa: variedad de activos, calidad de señales, frecuencia, qué falta."},
    ]
    result = call_mimo(messages)
    log(f"Trading review result: {result[:200]}...")
    return result

def review_content_progress():
    log("Reviewing content progress")
    md_path = BASE / "progress" / "CONTENT.md"
    if not md_path.exists():
        return "No content progress found"

    data = md_path.read_text()
    messages = [
        {"role": "system", "content": "Eres un revisor de calidad de contenido. Analizas el progreso de producción de video, detectas problemas, y recomiendas mejoras. Responde en español con estructura: 1) Resumen 2) Avances 3) Problemas 4) Recomendaciones."},
        {"role": "user", "content": f"Revisa este progreso de creación de contenido:\n\n{data}\n\nEvalúa: qué se ha logrado, qué falta, calidad del pipeline, sincronización audio-video."},
    ]
    result = call_mimo(messages)
    log(f"Content review result: {result[:200]}...")
    return result

def save_review(review_type, content):
    out = BASE / "progress" / "REVIEWS.md"
    ts = datetime.now().isoformat()[:19]
    entry = f"\n## Review {review_type} — {ts}\n\n{content}\n---\n"
    with open(out, "a") as f:
        f.write(entry)
    log(f"Review saved to progress/REVIEWS.md")

def watch_mode():
    """Continuous monitoring: reviews everything every 5min."""
    log("Reviewer watch mode started")
    cycle = 0
    while True:
        cycle += 1
        log(f"--- Review cycle {cycle} ---")

        # Review latest video
        videos = sorted((BASE / "artifacts" / "videos").glob("*.mp4"))
        if videos:
            latest = videos[-1]
            if latest.stat().st_size > 10000:  # >10KB = likely has content
                result = review_video(latest)
                save_reason = f"video-{latest.stem[:30]}"
                # Only save if there are issues or every 5th cycle
                if "negro" in result.lower() or "mal" in result.lower() or cycle % 5 == 0:
                    save_review(save_reason, result)

        # Review trading every 3 cycles
        if cycle % 3 == 0:
            result = review_trading_report()
            save_review("trading-periodic", result)

        # Review content every 5 cycles
        if cycle % 5 == 0:
            result = review_content_progress()
            save_review("content-periodic", result)

        time.sleep(300)  # 5 min

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-video", type=str)
    parser.add_argument("--review-report", type=str, choices=["trading", "content"])
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()

    if args.review_video:
        path = Path(args.review_video)
        if path.exists():
            result = review_video(path)
            save_review(f"video-{path.stem[:30]}", result)
            print(result)
        else:
            print(f"Video not found: {path}")
    elif args.review_report == "trading":
        result = review_trading_report()
        save_review("trading", result)
        print(result)
    elif args.review_report == "content":
        result = review_content_progress()
        save_review("content", result)
        print(result)
    elif args.watch:
        watch_mode()
    else:
        # Single review of everything
        result = []
        videos = sorted((BASE / "artifacts" / "videos").glob("*.mp4"))
        if videos:
            result.append(review_video(videos[-1]))
        result.append(review_trading_report())
        result.append(review_content_progress())
        save_review("full-audit", "\n\n".join(result))
        print("\n\n".join(result))
