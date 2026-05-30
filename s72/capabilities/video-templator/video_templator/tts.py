"""TTS module: generates narration audio + word-level timestamps via edge-tts."""

from __future__ import annotations

from typing import List, Optional

from edge_tts import Communicate, SubMaker

from .models import Narration, SubtitleBlock, Word
from .subtitles import group_words_into_blocks


async def generate_narration(
    text: str,
    voice: str = "es-MX-DaliaNeural",
    output_path: str = "narration.mp3",
    rate: str = "+0%",
    pitch: str = "+0Hz",
    volume: str = "+0%",
    proxy: Optional[str] = None,
    max_words_per_block: int = 4,
    min_block_duration_ms: float = 1200.0,
) -> Narration:
    """Generate TTS audio + word timestamps using Microsoft Edge's free TTS.

    Args:
        text: The narration script text.
        voice: Edge TTS voice name (see --list-voices).
        output_path: Where to write the mp3 audio.
        rate: Speaking rate adjustment ("+0%", "-20%", "+30%", etc.).
        pitch: Pitch adjustment ("+0Hz", "-50Hz", etc.).
        volume: Volume adjustment ("+0%", "-20%", etc.).
        proxy: Optional proxy URL.
        max_words_per_block: Max words per subtitle block.
        min_block_duration_ms: Minimum duration per subtitle block.

    Returns:
        Narration object with audio path, word timestamps, and subtitle blocks.
    """
    communicate = Communicate(
        text,
        voice,
        rate=rate,
        pitch=pitch,
        volume=volume,
        proxy=proxy,
        boundary="WordBoundary",
    )
    submaker = SubMaker()

    with open(output_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

    # Convert edge-tts cues to our Word model
    words: List[Word] = []
    for cue in submaker.cues:
        words.append(
            Word(
                text=cue.content,
                start_ms=cue.start.total_seconds() * 1000,
                end_ms=cue.end.total_seconds() * 1000,
            )
        )

    duration_ms = words[-1].end_ms if words else 0.0

    # Group words into subtitle blocks
    blocks = group_words_into_blocks(
        words,
        max_words_per_block=max_words_per_block,
        min_duration_ms=min_block_duration_ms,
    )

    return Narration(
        audio_path=output_path,
        words=words,
        blocks=blocks,
        duration_ms=duration_ms,
    )


async def generate_narration_srt(
    text: str,
    voice: str = "es-MX-DaliaNeural",
    output_path: str = "narration.mp3",
    srt_path: str = "subtitles.srt",
    rate: str = "+0%",
    pitch: str = "+0Hz",
    proxy: Optional[str] = None,
) -> tuple[str, str]:
    """Simpler wrapper that writes audio + SRT file directly (no word grouping).

    Returns (audio_path, srt_path).
    """
    communicate = Communicate(
        text,
        voice,
        rate=rate,
        pitch=pitch,
        proxy=proxy,
        boundary="SentenceBoundary",
    )
    submaker = SubMaker()

    with open(output_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                submaker.feed(chunk)

    srt_content = submaker.get_srt()
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    return output_path, srt_path


# Synchronous convenience wrappers

def generate_narration_sync(
    text: str,
    voice: str = "es-MX-DaliaNeural",
    output_path: str = "narration.mp3",
    rate: str = "+0%",
    pitch: str = "+0Hz",
    volume: str = "+0%",
    proxy: Optional[str] = None,
    max_words_per_block: int = 4,
    min_block_duration_ms: float = 1200.0,
) -> Narration:
    """Synchronous version of generate_narration."""
    import asyncio

    return asyncio.run(
        generate_narration(
            text=text,
            voice=voice,
            output_path=output_path,
            rate=rate,
            pitch=pitch,
            volume=volume,
            proxy=proxy,
            max_words_per_block=max_words_per_block,
            min_block_duration_ms=min_block_duration_ms,
        )
    )


def generate_narration_srt_sync(
    text: str,
    voice: str = "es-MX-DaliaNeural",
    output_path: str = "narration.mp3",
    srt_path: str = "subtitles.srt",
    rate: str = "+0%",
    pitch: str = "+0Hz",
    proxy: Optional[str] = None,
) -> tuple[str, str]:
    """Synchronous version of generate_narration_srt."""
    import asyncio

    return asyncio.run(
        generate_narration_srt(
            text=text,
            voice=voice,
            output_path=output_path,
            srt_path=srt_path,
            rate=rate,
            pitch=pitch,
            proxy=proxy,
        )
    )
