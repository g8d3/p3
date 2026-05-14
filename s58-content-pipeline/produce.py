#!/usr/bin/env python3
"""
Master Producer — Automated Video Creation with Two-Model Feedback Loop.

Usage:
  python3 produce.py                              # Full loop: generate + review
  python3 produce.py --topic "Your topic"         # Custom topic
  python3 produce.py --news                       # Fetch trending news topic
  python3 produce.py --no-review                  # Skip review phase
  python3 produce.py --gen-model glm-5            # Override generation model
  python3 produce.py --review-model kimi-k2.5     # Override review model

Environment:
  OPENCODE_GO_API_KEY      Required
  OPENCODE_GO_MODEL        Generation model (default: deepseek-v4-flash)
  REVIEW_MODEL             Review model (default: qwen3.6-plus)
  INWORLD_API_KEY          For TTS
  PEXELS_API_KEY           For stock video background
"""
import os, sys, json, argparse, subprocess, textwrap
from pathlib import Path
from datetime import datetime

# Config from env
GO_KEY = os.environ.get("OPENCODE_GO_API_KEY", "")
GO_MODEL = os.environ.get("OPENCODE_GO_MODEL", "deepseek-v4-flash")
REVIEW_MODEL = os.environ.get("REVIEW_MODEL", "qwen3.6-plus")

WORK = Path(__file__).parent / "work"
WORK.mkdir(exist_ok=True)

# ── Phase 1: Generate Video ──────────────────────────────────────────────
def phase_generate(topic: str, shorts: int, gen_model: str, skip_upload: bool) -> str:
    """Run the video generation pipeline. Returns the output directory."""
    print(f"\n{'='*60}")
    print(f"  🎬 PHASE 1: GENERATION")
    print(f"     Model: {gen_model}")
    print(f"     Topic: {topic}")
    print(f"{'='*60}\n")

    env = os.environ.copy()
    env["OPENCODE_GO_MODEL"] = gen_model

    cmd = [sys.executable, "-B", "pipeline.py", "--topic", topic,
           "--shorts", str(shorts), "--keep-temp"]
    if skip_upload:
        cmd.append("--skip-upload")

    result = subprocess.run(cmd, capture_output=False, env=env)

    if result.returncode != 0:
        print(f"\n  ❌ Generation failed (exit code {result.returncode})")
        sys.exit(1)

    # Find the latest run_id directory (YYYYMMDD-HHMMSS format)
    runs = sorted([p for p in WORK.iterdir() if p.is_dir() and p.name[:8].isdigit()],
                  key=lambda p: p.stat().st_mtime, reverse=True)
    if not runs:
        print("  ❌ No output directory found")
        sys.exit(1)
    return str(runs[0])

# ── Phase 2: Review ──────────────────────────────────────────────────────
def phase_review(topic: str, out_dir: str, review_model: str) -> str:
    """Review the generated output using a second model. Returns feedback text."""
    print(f"\n{'='*60}")
    print(f"  🔍 PHASE 2: REVIEW")
    print(f"     Model: {review_model}")
    print(f"{'='*60}\n")

    # Read generated files
    script_path = Path(out_dir) / "script.txt"
    srt_path = Path(out_dir) / "captions.srt"
    video_path = Path(out_dir) / "long.mp4"

    script_text = script_path.read_text() if script_path.exists() else "(not found)"
    srt_text = srt_path.read_text()[:2000] if srt_path.exists() else "(not found)"

    # Get video metadata
    video_info = ""
    if video_path.exists():
        try:
            d = json.loads(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration,size,bit_rate",
                 "-of", "json", str(video_path)],
                capture_output=True, text=True, timeout=10).stdout)
            fmt = d.get("format", {})
            video_info = f"Duration: {float(fmt.get('duration', 0)):.0f}s  Size: {int(fmt.get('size', 0))/1024/1024:.1f}MB"
        except:
            video_info = "Could not probe"

    prompt = f"""Eres un revisor de calidad de videos. Analiza esta produccion y da feedback CONCRETO y ACCIONABLE.

TEMA: {topic}

## Script generado
```
{script_text[:1500]}
```

## Subtitulos (SRT)
```
{srt_text[:1000]}
```

## Video
{video_info}

## Tu tarea
Revisa y califica del 1 al 10:
1. **Calidad del script** — ?/10: Es atractivo? Tiene gancho? Fluye bien?
2. **Sincronia** — ?/10: Los timestamps de subtitulos se ven coherentes?
3. **Contenido** — ?/10: Es relevante al tema? Tiene profundidad?
4. **Mejoras** — Que cambiarias? (max 3 sugerencias concretas)

Responde con: CALIFICACION: X/10 y luego 2-3 parrafos de feedback."""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=GO_KEY, base_url="https://opencode.ai/zen/go/v1", timeout=120)
        r = client.chat.completions.create(
            model=review_model, max_tokens=2048,
            messages=[{"role": "user", "content": prompt}])
        feedback = r.choices[0].message.content.strip()
    except Exception as e:
        feedback = f"[Review failed: {e}]"

    # Save review
    review_path = Path(out_dir) / "review.txt"
    review_path.write_text(feedback)
    print(f"\n  ✅ Review saved to: {review_path}")
    return feedback

# ── Phase 3: Report ──────────────────────────────────────────────────────
def phase_report(topic: str, out_dir: str, feedback: str):
    """Print the final report."""
    print(f"\n{'='*60}")
    print(f"  📋 FINAL REPORT")
    print(f"{'='*60}")
    print(f"  Topic: {topic}")
    print(f"  Output: {out_dir}/long.mp4")
    print(f"  Shorts: {out_dir}/s*.mp4")
    print(f"\n  Review:")
    # Clean ANSI/formatting for display
    clean = feedback.replace("```", "").strip()
    print(textwrap.indent(clean, "    "))
    print(f"\n{'='*60}")

# ── Main ─────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Master Video Producer")
    ap.add_argument("--topic", help="Video topic")
    ap.add_argument("--news", action="store_true", help="Fetch trending topic")
    ap.add_argument("--no-review", action="store_true", help="Skip review phase")
    ap.add_argument("--shorts", type=int, default=12, help="Number of shorts (default: 12)")
    ap.add_argument("--gen-model", default=GO_MODEL, help=f"Generation model (default: {GO_MODEL})")
    ap.add_argument("--review-model", default=REVIEW_MODEL, help=f"Review model (default: {REVIEW_MODEL})")
    ap.add_argument("--skip-upload", action="store_true", help="Skip social uploads")
    ap.add_argument("--list-models", action="store_true", help="List available OpenCode Go models")
    args = ap.parse_args()

    if args.list_models:
        print("Available OpenCode Go models:")
        models = ["deepseek-v4-flash", "deepseek-v4-pro", "glm-5", "glm-5.1",
                  "kimi-k2.5", "kimi-k2.6", "mimo-v2.5", "mimo-v2.5-pro",
                  "minimax-m2.7", "qwen3.6-plus", "qwen3.5-plus"]
        for m in models:
            print(f"  • {m}")
        return

    # Get topic
    if args.news:
        print("Fetching trending news...")
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from news_agent import fetch_all_topics, pick_topic
        items = fetch_all_topics()
        chosen = pick_topic(items)
        topic = chosen["title"]
        print(f"  → {topic}")
    else:
        topic = args.topic or input("Enter video topic: ")

    if not topic:
        print("No topic provided.")
        sys.exit(1)

    # Phase 1: Generate
    out_dir = phase_generate(topic, args.shorts, args.gen_model, args.skip_upload)

    # Phase 2: Review
    feedback = ""
    if not args.no_review:
        feedback = phase_review(topic, out_dir, args.review_model)
    else:
        feedback = "(Review skipped)"

    # Phase 3: Report
    phase_report(topic, out_dir, feedback)

if __name__ == "__main__":
    main()
