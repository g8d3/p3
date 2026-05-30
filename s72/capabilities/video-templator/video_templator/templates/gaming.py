"""Gaming template — single-screen gameplay + narration + big subtitles.

Features:
- Fullscreen gameplay video (randomly selected from assets)
- Bottom-center subtitles with word-highlight karaoke (ASS)
- Narration audio + randomly selected background music
- TikTok vertical format (1080×1920)
"""

from __future__ import annotations

import os
import random
from typing import Optional

from ..compositor import FfmpegCompositor
from ..models import TemplateConfig
from ..subtitles import save_ass, save_srt
from ..tts import generate_narration
from .base import VideoTemplate


class GamingTemplate(VideoTemplate):
    """Single-screen gaming video template for TikTok.

    Usage:
        template = GamingTemplate()
        out = await template.render(
            script="Hoy vamos a ver este gameplay...",
            gameplay_primary="gameplay.mp4",
        )
    """

    def __init__(self, config: Optional[TemplateConfig] = None):
        super().__init__(config)
        self.compositor = FfmpegCompositor(self.config)

    async def render(
        self,
        script: str,
        gameplay_primary: str,
        output: str = "output.mp4",
        bg_music: Optional[str] = None,
        voice: str = "es-MX-DaliaNeural",
        tts_rate: str = "+0%",
        tts_pitch: str = "+0Hz",
        tts_volume: str = "+0%",
        subtitle_format: str = "ass",
    ) -> str:
        """Full rendering pipeline: TTS → subtitles → composition.

        Args:
            script: Narration text.
            gameplay_primary: Path to primary gameplay video.
            output: Output video path.
            bg_music: Optional background music path.
            voice: Edge TTS voice name.
            tts_rate: Speech rate adjustment.
            tts_pitch: Speech pitch adjustment.
            tts_volume: Speech volume adjustment.
            subtitle_format: "ass" for karaoke, "srt" for plain.

        Returns:
            Path to the rendered video.
        """
        base, _ext = os.path.splitext(output)

        # 1. Generate narration audio + word timestamps
        narration = await generate_narration(
            text=script,
            voice=voice,
            output_path=f"{base}_narration.mp3",
            rate=tts_rate,
            pitch=tts_pitch,
            volume=tts_volume,
            max_words_per_block=self.config.max_words_per_block,
            min_block_duration_ms=self.config.min_block_duration_ms,
        )

        # 2. Generate subtitles
        if subtitle_format == "ass":
            sub_path = f"{base}_subtitles.ass"
            save_ass(
                narration.blocks,
                sub_path,
                video_width=self.config.width,
                video_height=self.config.height,
                font_name=self.config.subtitle_font,
                font_size=self.config.subtitle_font_size,
                primary_color=self.config.subtitle_color,
                secondary_color=self.config.subtitle_highlight_color,
                stroke_color=self.config.subtitle_stroke_color,
                stroke_width=self.config.subtitle_stroke_width,
                margin_bottom=self.config.subtitle_margin_bottom,
            )
        else:
            sub_path = f"{base}_subtitles.srt"
            save_srt(narration.blocks, sub_path)

        # 3. Compose video (single-screen, no PiP)
        await self.compositor.compose(
            primary_clip=gameplay_primary,
            narration_path=narration.audio_path,
            subtitles_path=sub_path,
            output=output,
            bg_music_path=bg_music,
        )

        return output

# ── Convenience: pick random asset ───────────────────────

def random_gameplay(assets_dir: str = "assets/gameplay") -> str:
    """Pick a random gameplay video from the assets directory."""
    files = [f for f in os.listdir(assets_dir) if f.endswith((".mp4", ".mov", ".mkv"))]
    if not files:
        raise FileNotFoundError(f"No gameplay videos found in {assets_dir}")
    return os.path.join(assets_dir, random.choice(files))


def random_music(assets_dir: str = "assets/audio") -> Optional[str]:
    """Pick a random music track from the assets directory."""
    files = [f for f in os.listdir(assets_dir) if f.endswith((".mp3", ".m4a", ".wav"))]
    if not files:
        return None
    return os.path.join(assets_dir, random.choice(files))
