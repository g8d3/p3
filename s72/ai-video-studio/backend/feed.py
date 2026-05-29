"""Feed Engine — solo genera componentes, no renderiza video.

El servidor hace lo rápido (~10s):
  - Fetch trends + script via LLM
  - Narración audio (edge-tts)
  - Subtítulos (ASS con karaoke)
  - Selecciona gameplay + música

El browser hace lo pesado (composición) via APIs nativas.
"""

from __future__ import annotations
import asyncio
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Optional

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from backend.sources import get_all_connectors
from backend.config import CONFIG
from backend.visibility import log

POOL_SIZE = 5
MAX_TRENDING_ITEMS = 10
SCRIPT_MAX_CHARS = 3000

_style_state = {
    "voice": CONFIG.default_voice,
    "font_size": CONFIG.subtitle_font_size,
    "max_words": CONFIG.max_words_per_block,
    "music_volume": CONFIG.bg_music_volume,
    "video_bitrate": "8M",
}

_action_log: list[dict] = []
MAX_ACTIONS = 100

def _log_action(kind: str, detail: str, data: dict | None = None) -> None:
    entry = {"ts": time.strftime("%H:%M:%S"), "kind": kind, "detail": detail, "data": data or {}}
    _action_log.append(entry)
    if len(_action_log) > MAX_ACTIONS:
        _action_log[:] = _action_log[-MAX_ACTIONS:]
    log("INFO", "feed", f"{kind}: {detail}")

def get_actions(limit: int = 20) -> list[dict]:
    return list(reversed(_action_log))[:limit]

# ── Trends (force=True bypasses cache for fresh content per package) ──

async def fetch_all_trends(force: bool = False) -> str:
    conns = get_all_connectors()
    parts: list[str] = []
    for name, conn in conns.items():
        if not conn.enabled:
            continue
        try:
            items = conn._do_fetch() if force else conn.fetch()
            if items:
                # Randomize for variety
                picked = random.sample(items, min(len(items), MAX_TRENDING_ITEMS))
                parts.append(f"=== {name} ===")
                for it in picked:
                    title = it.get("title", "?")
                    desc = str(it.get("description", ""))[:120]
                    parts.append(f"- {title}: {desc}")
            _log_action("fetch", f"Fetched {len(items)} items from {name}")
        except Exception as e:
            parts.append(f"- {name}: error {e}")
            _log_action("fetch_error", f"{name}: {e}")
    return "\n".join(parts) if parts else "(sin datos)"

PROXY_URL = os.environ.get("PROXY_URL", "http://127.0.0.1:9100")

async def _call_llm(prompt: str, system: str, max_tokens: int = 4000) -> str:
    import urllib.request
    payload = json.dumps({
        "model": "deepseek-v4-flash",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }).encode()
    try:
        req = urllib.request.Request(f"{PROXY_URL}/chat/completions", data=payload,
            headers={"Content-Type": "application/json"})
        loop = asyncio.get_running_loop()
        r = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=120))
        resp = json.loads(r.read())
        msg = resp["choices"][0]["message"]
        content = msg.get("content", "")
        if not content.strip() and msg.get("reasoning_content"):
            content = msg["reasoning_content"]
        return content
    except Exception as e:
        log("ERROR", "feed.llm", f"Proxy call failed: {e}")
        return "La inteligencia artificial está transformando el mundo. Cada día surgen nuevos modelos."

SYSTEM_PROMPT = (
    "Eres un creador de contenido para TikTok. "
    "Eres directo, conversacional, usas números como dígitos. "
    "Máximo 100 palabras. Sin introducciones ni despedidas largas. "
    "Todo en español. IMPORTANTE: No incluyas razonamiento, solo el guión final."
)

_last_topic: str = ""  # avoid same topic twice in a row

async def generate_script(trends_text: str) -> str:
    global _last_topic
    avoid = f"NO escribas sobre este tema que ya usaste antes: {_last_topic}" if _last_topic else ""
    prompt = (
        "Genera un guión de TikTok de 30-40 segundos basado en estos datos de tendencias de IA.\n"
        "Usa números como dígitos (16% no 'dieciséis por ciento').\n"
        "Sé conversacional, directo. Sin introducciones ni despedidas largas.\n"
        f"{avoid}\n\n"
        f"Datos de tendencias:\n{trends_text[:SCRIPT_MAX_CHARS]}"
    )
    script = await _call_llm(prompt, SYSTEM_PROMPT)
    # Track first ~5 words as topic
    _last_topic = " ".join(script.split()[:5]) if script else ""
    _log_action("script_generated", f"Script ({len(script)} chars)")
    return script

# ── Package generation (sin ffmpeg) ──────────────────────

_package_queue: list[dict] = []
_queue_lock = asyncio.Lock()
_refresh_task: Optional[asyncio.Task] = None
_generation_count: int = 0
_QUEUE_MAX = POOL_SIZE * 2  # allow up to 10 packages to absorb bursts

async def _generate_one_package() -> dict | None:
    global _generation_count
    _generation_count += 1
    # Force fresh trends every time so each video has different news
    trends = await fetch_all_trends(force=True)
    script = await generate_script(trends)
    if not script.strip():
        log("WARN", "feed", "Empty script")
        return None

    # Vary assets each time
    gp_dir = Path(CONFIG.assets_dir) / "gameplay"
    gameplay_choices = list(gp_dir.glob("*.mp4"))
    gameplay = str(random.choice(gameplay_choices)) if gameplay_choices else ""

    mu_dir = Path(CONFIG.assets_dir) / "audio"
    music_choices = list(mu_dir.glob("*.mp3"))
    music = str(random.choice(music_choices)) if music_choices else ""

    import uuid
    pkg_id = str(uuid.uuid4())[:8]
    output_base = os.path.join(CONFIG.output_dir, pkg_id)
    nar_path = f"{output_base}_narration.mp3"
    sub_path = f"{output_base}_subtitles.ass"

    from video_templator.tts import generate_narration
    from video_templator.subtitles import save_ass
    from video_templator.models import TemplateConfig

    cfg = TemplateConfig(
        width=1080, height=1920,
        subtitle_font_size=_style_state["font_size"],
        subtitle_stroke_width=3.0, subtitle_margin_bottom=160,
        subtitle_color="&H00FFFFFF", subtitle_highlight_color="&H0000FFFF",
        subtitle_stroke_color="&H00000000",
        max_words_per_block=_style_state["max_words"],
        min_block_duration_ms=1500,
        bg_music_volume=_style_state["music_volume"],
        video_bitrate=_style_state["video_bitrate"],
    )

    narration = await generate_narration(
        text=script, voice=_style_state["voice"],
        output_path=nar_path,
        max_words_per_block=cfg.max_words_per_block,
        min_block_duration_ms=cfg.min_block_duration_ms,
    )

    save_ass(
        narration.blocks, sub_path,
        video_width=cfg.width, video_height=cfg.height,
        font_name=cfg.subtitle_font, font_size=cfg.subtitle_font_size,
        primary_color=cfg.subtitle_color, secondary_color=cfg.subtitle_highlight_color,
        stroke_color=cfg.subtitle_stroke_color, stroke_width=cfg.subtitle_stroke_width,
        margin_bottom=cfg.subtitle_margin_bottom,
    )

    dur_s = narration.duration_ms / 1000.0
    pkg = {
        "pkg_id": pkg_id, "script": script,
        "narration_path": nar_path, "subtitle_path": sub_path,
        "gameplay_path": gameplay, "music_path": music,
        "duration_s": dur_s,
        "voice": _style_state["voice"], "font_size": _style_state["font_size"],
        "created_at": time.time(),
    }
    _log_action("package_ready", f"Package {pkg_id} ({dur_s:.1f}s)")
    return pkg

async def ensure_queue_filled() -> None:
    """Continuous producer: always generating, never waits for consumption."""
    global _refresh_task
    while True:
        try:
            pkg = await _generate_one_package()
            if pkg:
                async with _queue_lock:
                    if len(_package_queue) >= _QUEUE_MAX:
                        _package_queue.pop(0)
                    _package_queue.append(pkg)
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log("ERROR", "feed", f"Producer error: {e}")
            await asyncio.sleep(2)

def start_background_refresh() -> None:
    global _refresh_task
    if _refresh_task is None or _refresh_task.done():
        _refresh_task = asyncio.create_task(ensure_queue_filled())
        _log_action("system", "Feed engine started (browser compositing)")

def get_queue_status() -> list[dict]:
    return [_pkg_summary(p) for p in _package_queue]

def _pkg_summary(pkg: dict) -> dict:
    return {"pkg_id": pkg["pkg_id"], "duration_s": pkg.get("duration_s"),
            "script": pkg.get("script", "")[:80], "created_at": pkg.get("created_at")}

async def pop_next_package() -> Optional[dict]:
    async with _queue_lock:
        if _package_queue:
            pkg = _package_queue.pop(0)
            _log_action("package_consumed", f"Package {pkg['pkg_id']}")
            return pkg
    return None

def peek_next_package() -> Optional[dict]:
    if _package_queue:
        return _package_queue[0]
    return None

def get_style() -> dict:
    return dict(_style_state)

def update_style(**kwargs) -> dict:
    for key, value in kwargs.items():
        if key in _style_state:
            _style_state[key] = value
    _log_action("style_update", f"Style: {kwargs}")
    return dict(_style_state)
