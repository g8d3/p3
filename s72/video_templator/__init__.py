"""video-templator: AI-powered video template engine.

Build video templates quickly using:
- edge-tts for narration + word-level timestamps (free, no GPU)
- ffmpeg for video/audio composition (fast, battle-tested)
- Smart subtitle grouping with optional karaoke highlighting (ASS)
"""

from .models import Narration, SubtitleBlock, TemplateConfig, Word
from .compositor import FfmpegCompositor
from .subtitles import blocks_to_ass, blocks_to_srt, group_words_into_blocks, save_ass, save_srt
from .tts import generate_narration, generate_narration_sync
from .templates import GamingTemplate, random_gameplay, random_music

__all__ = [
    # Models
    "Narration",
    "SubtitleBlock",
    "TemplateConfig",
    "Word",
    # Subtitles
    "blocks_to_ass",
    "blocks_to_srt",
    "group_words_into_blocks",
    "save_ass",
    "save_srt",
    # TTS
    "generate_narration",
    "generate_narration_sync",
    # Templates
    "GamingTemplate",
    "random_gameplay",
    "random_music",
    # Compositor
    "FfmpegCompositor",
]
