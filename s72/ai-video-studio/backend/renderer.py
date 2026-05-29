"""Video rendering via video-templator."""
from __future__ import annotations
import os
import sys
import json
import time
import random
from pathlib import Path
from typing import Optional

# Ensure we can import video-templator
VIDEO_TEMPLATOR_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
if VIDEO_TEMPLATOR_DIR not in sys.path:
    sys.path.insert(0, VIDEO_TEMPLATOR_DIR)

from video_templator import GamingTemplate, TemplateConfig

from .config import CONFIG


class RenderJob:
    """Tracks a single video render with stage/ETA progress."""

    STAGES = ["narration", "subtitles", "composing"]

    def __init__(self, job_id: str, params: dict):
        self.job_id = job_id
        self.params = params
        self.status = "queued"  # queued → rendering → done / failed
        self.progress = 0.0
        self.stage: str = ""
        self.eta_s: Optional[float] = None
        self.stage_start: float = 0.0
        self.output_path: Optional[str] = None
        self.narration_path: Optional[str] = None
        self.subtitle_path: Optional[str] = None
        self.gameplay_path: Optional[str] = None
        self.music_path: Optional[str] = None
        self.script: str = ""
        self.error: Optional[str] = None
        self.created_at = time.time()
        self.duration_s: Optional[float] = None

    def set_stage(self, stage: str) -> None:
        """Move to a new stage, update progress/ETA."""
        self.stage = stage
        self.stage_start = time.time()
        stage_idx = self.STAGES.index(stage) if stage in self.STAGES else 0
        self.progress = stage_idx / len(self.STAGES)
        # Estimate: each stage ~20-30s
        remaining_stages = len(self.STAGES) - stage_idx
        self.eta_s = remaining_stages * 25


# In-memory job store (replace with DB for production)
_jobs: dict[str, RenderJob] = {}


async def start_render(params: dict) -> str:
    """Start a render job in a background task (non-blocking)."""
    import uuid
    import asyncio
    job_id = str(uuid.uuid4())[:8]
    job = RenderJob(job_id, params)
    _jobs[job_id] = job
    asyncio.create_task(_do_render(job))
    return job_id


async def _do_render(job: RenderJob) -> None:
    """Execute the render with stage tracking."""
    job.status = "rendering"
    p = job.params
    job.script = p.get("script", "")

    # 1. Build config
    cfg = TemplateConfig(
        width=p.get("width", 1080),
        height=p.get("height", 1920),
        subtitle_font_size=p.get("font_size", CONFIG.subtitle_font_size),
        subtitle_stroke_width=p.get("stroke_width", CONFIG.subtitle_stroke_width),
        subtitle_margin_bottom=p.get("margin_bottom", 160),
        subtitle_color=p.get("text_color", "&H00FFFFFF"),
        subtitle_highlight_color=p.get("highlight_color", "&H0000FFFF"),
        subtitle_stroke_color=p.get("stroke_color", "&H00000000"),
        max_words_per_block=p.get("max_words", CONFIG.max_words_per_block),
        min_block_duration_ms=1500,
        bg_music_volume=p.get("music_volume", CONFIG.bg_music_volume),
        video_bitrate=p.get("video_bitrate", "8M"),
    )

    # 2. Source assets
    script = job.script
    voice = p.get("voice", CONFIG.default_voice)
    gameplay = p.get("gameplay")
    if not gameplay or not os.path.exists(gameplay):
        gp_dir = os.path.join(CONFIG.assets_dir, "gameplay")
        choices = [f for f in os.listdir(gp_dir) if f.endswith(".mp4")]
        if choices:
            gameplay = os.path.join(gp_dir, random.choice(choices))
        else:
            raise FileNotFoundError("No gameplay video available")
    job.gameplay_path = gameplay

    music = p.get("music")
    if music and not os.path.exists(music):
        music = None
    if not music:
        mu_dir = os.path.join(CONFIG.assets_dir, "audio")
        choices = [f for f in os.listdir(mu_dir) if f.endswith((".mp3", ".m4a"))]
        if choices:
            music = os.path.join(mu_dir, random.choice(choices))
    job.music_path = music

    # 3. Generate narration (fast, ~5s) + subtitles
    job.set_stage("narration")
    output_base = os.path.join(CONFIG.output_dir, job.job_id)
    nar_path = f"{output_base}_narration.mp3"
    sub_path = f"{output_base}_subtitles.ass"

    from video_templator.tts import generate_narration
    from video_templator.subtitles import save_ass

    narration = await generate_narration(
        text=script,
        voice=voice,
        output_path=nar_path,
        max_words_per_block=cfg.max_words_per_block,
        min_block_duration_ms=cfg.min_block_duration_ms,
    )
    job.narration_path = nar_path

    job.set_stage("subtitles")
    save_ass(
        narration.blocks,
        sub_path,
        video_width=cfg.width,
        video_height=cfg.height,
        font_name=cfg.subtitle_font,
        font_size=cfg.subtitle_font_size,
        primary_color=cfg.subtitle_color,
        secondary_color=cfg.subtitle_highlight_color,
        stroke_color=cfg.subtitle_stroke_color,
        stroke_width=cfg.subtitle_stroke_width,
        margin_bottom=cfg.subtitle_margin_bottom,
    )
    job.subtitle_path = sub_path

    # 4. Compose video (slow, ~30-60s)
    job.set_stage("composing")
    output = os.path.join(CONFIG.output_dir, f"{job.job_id}.mp4")
    tmpl = GamingTemplate(cfg)
    await tmpl.render(
        script=script,
        gameplay_primary=gameplay,
        output=output,
        bg_music=music,
        voice=voice,
        subtitle_format="ass",
    )

    job.status = "done"
    job.output_path = output
    job.progress = 1.0
    job.eta_s = 0

    try:
        import subprocess
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_entries", "format=duration", output],
            capture_output=True, text=True, timeout=10,
        )
        job.duration_s = float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        pass


def get_job(job_id: str) -> Optional[RenderJob]:
    return _jobs.get(job_id)


def list_jobs() -> list[dict]:
    return [
        {"id": jid, "status": j.status, "progress": j.progress,
         "duration_s": j.duration_s, "created_at": j.created_at,
         "error": j.error}
        for jid, j in sorted(_jobs.items(),
                             key=lambda x: x[1].created_at, reverse=True)
    ]
