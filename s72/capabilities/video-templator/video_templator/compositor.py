"""Video/Audio compositor using ffmpeg subprocess.

- Scales video to target resolution
- Burns subtitles (SRT or ASS)
- Mixes narration + optional background music
- Trims video to match audio duration (fixes -shortest issues)
"""

from __future__ import annotations

import asyncio
import json
import os
import shlex
import sys
from typing import Optional

from .models import TemplateConfig


def _probe_duration(path: str) -> float:
    """Get duration in seconds of a media file via ffprobe."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_entries", "format=duration", path],
            capture_output=True, text=True, timeout=10,
        )
        data = json.loads(r.stdout)
        return float(data["format"]["duration"])
    except Exception:
        return 0.0


class FfmpegCompositor:
    """Drives ffmpeg to composite the final video.

    Probes audio durations to trim video precisely — no silent gaps.
    """

    def __init__(self, config: TemplateConfig):
        self.config = config
        self._ffmpeg = self._find_ffmpeg()

    async def compose(
        self,
        primary_clip: str,
        narration_path: str,
        subtitles_path: str,
        output: str,
        bg_music_path: Optional[str] = None,
    ) -> None:
        """Assemble the final video. (Async — runs ffmpeg in thread pool.)

        Probes narration (and bg_music) duration and trims the video
        to match, so there's never a silent tail.
        """
        import subprocess

        W = self.config.width
        H = self.config.height

        # ── Probe audio durations ──────────────────────────────
        nar_dur = _probe_duration(narration_path)
        music_dur = _probe_duration(bg_music_path) if bg_music_path else 9999
        target_dur = min(nar_dur, music_dur)

        if target_dur <= 0:
            target_dur = nar_dur

        self._log(f"narration={nar_dur:.1f}s, music={music_dur:.1f}s, target={target_dur:.1f}s")

        # ── Inputs ─────────────────────────────────────────────
        cmd: list[str] = [self._ffmpeg, "-y"]

        # Primary video — trimmed to target_dur
        cmd.extend(["-t", f"{target_dur:.3f}", "-i", primary_clip])
        primary_idx = 0
        input_idx = 1

        cmd.extend(["-i", narration_path])
        narration_idx = input_idx
        input_idx += 1

        bg_music_idx: Optional[int] = None
        if bg_music_path:
            cmd.extend(["-i", bg_music_path])
            bg_music_idx = input_idx
            input_idx += 1

        # ── Filter graph ───────────────────────────────────────
        parts: list[str] = []

        # Video: scale + crop to fill frame + subtitles burned in
        ext = os.path.splitext(subtitles_path)[1].lower()
        sub_filter = f"ass={shlex.quote(subtitles_path)}" if ext == ".ass" else f"subtitles={shlex.quote(subtitles_path)}"

        parts.append(
            f"[{primary_idx}:v]setpts=PTS-STARTPTS,"
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},"
            f"{sub_filter}[vid]"
        )

        # Audio: mix narration + optional bg_music
        audio_sources = [(narration_idx, self.config.narration_volume)]
        if bg_music_idx is not None:
            audio_sources.append((bg_music_idx, self.config.bg_music_volume))

        if audio_sources:
            vol_filtered: list[str] = []
            for idx, vol in audio_sources:
                label = f"a{idx}"
                if vol != 1.0:
                    parts.append(f"[{idx}:a]volume={vol}[{label}]")
                    vol_filtered.append(f"[{label}]")
                else:
                    vol_filtered.append(f"[{idx}:a]")
            mix_inputs = "".join(vol_filtered)
            parts.append(
                f"{mix_inputs}amix=inputs={len(audio_sources)}:duration=first[a]"
            )

        filter_complex = "; ".join(parts)
        cmd.extend(["-filter_complex", filter_complex])
        cmd.extend(["-map", "[vid]"])
        if audio_sources:
            cmd.extend(["-map", "[a]"])
        cmd.extend([
            "-c:v", self.config.video_codec,
            "-b:v", self.config.video_bitrate,
            "-c:a", self.config.audio_codec,
            "-b:a", self.config.audio_bitrate,
            "-pix_fmt", "yuv420p",
            output,
        ])

        # ── Run (async in thread pool) ────────────────────────
        self._log(f"cmd: {' '.join(shlex.quote(str(x)) for x in cmd)}")
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(cmd, capture_output=True, text=True),
        )
        if result.returncode != 0:
            print("ffmpeg stderr:", result.stderr, file=sys.stderr)
            raise RuntimeError(
                f"ffmpeg failed (exit {result.returncode}):\n{result.stderr[:2000]}"
            )

        actual = _probe_duration(output)
        self._log(f"output duration: {actual:.1f}s")

    @staticmethod
    def _find_ffmpeg() -> str:
        import shutil
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("ffmpeg not found")
        return ffmpeg

    @staticmethod
    def _log(msg: str) -> None:
        print(f"[compositor] {msg}", file=sys.stderr)
