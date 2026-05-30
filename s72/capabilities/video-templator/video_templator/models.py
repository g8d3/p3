"""Core data structures for the video templator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Word:
    """A single word with precise timing."""

    text: str
    start_ms: float
    end_ms: float

    @property
    def duration_ms(self) -> float:
        return self.end_ms - self.start_ms


@dataclass
class SubtitleBlock:
    """A group of words shown as one subtitle block on screen."""

    words: List[Word]
    start_ms: float
    end_ms: float

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def duration_ms(self) -> float:
        return self.end_ms - self.start_ms


@dataclass
class Narration:
    """Result of TTS generation: audio + word-level timestamps."""

    audio_path: str
    words: List[Word]
    blocks: List[SubtitleBlock]
    duration_ms: float


@dataclass
class TemplateConfig:
    """Configuration for a video template."""

    name: str = "default"
    width: int = 1920
    height: int = 1080
    fps: int = 30

    # subtitle visual style (for ASS rendering)
    subtitle_font: str = "sans-serif"
    subtitle_font_size: int = 96
    subtitle_color: str = "&H00FFFFFF"
    subtitle_highlight_color: str = "&H0000FFFF"
    subtitle_stroke_color: str = "&H00000000"
    subtitle_stroke_width: float = 3.0
    subtitle_margin_bottom: int = 120

    # picture-in-picture (secondary clip)
    pip_width: int = 540
    pip_height: int = 304
    pip_margin: int = 30

    # audio
    bg_music_volume: float = 0.12
    narration_volume: float = 1.0

    # subtitle grouping
    max_words_per_block: int = 3
    min_block_duration_ms: float = 1500.0

    # codec
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    video_bitrate: str = "8M"
    audio_bitrate: str = "128k"
