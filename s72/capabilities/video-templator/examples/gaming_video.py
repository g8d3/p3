"""Example: Create a ReVid-style gaming video with narration, subtitles, and PiP.

Usage:
    python examples/gaming_video.py
"""

import asyncio
import sys
import os

# Add parent dir to path so we can run as `python examples/...`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_templator import GamingTemplate, generate_narration_sync, blocks_to_srt


async def main():
    # ── Step 1: Write your script ──────────────────────────
    script = (
        "¿Qué tal a todos? Bienvenidos a este nuevo video. "
        "Hoy vamos a explorar las ruinas más peligrosas del mapa. "
        "Prepárense porque esto se va a poner intenso. "
        "Miren este pasadizo secreto que encontré detrás de la cascada. "
        "Aquí es donde empieza la verdadera aventura. "
        "No olviden dejar su like si les gusta este contenido. "
        "Y suscríbanse para más gameplay como este. "
        "¡Nos vemos en el próximo video!"
    )

    # ── Step 2: Create template and render ─────────────────
    template = GamingTemplate()

    output = await template.render(
        script=script,
        gameplay_primary="gameplay_primary.mp4",           # required
        gameplay_secondary="gameplay_secondary.mp4",       # optional PiP
        bg_music="background_music.mp3",                   # optional
        output="final_video.mp4",
        voice="es-MX-DaliaNeural",                         # Spanish (Mexican)
        # voice="en-US-JennyNeural",                       # English
        subtitle_format="ass",                             # "ass" (karaoke) or "srt"
    )

    print(f"\n✅ Video created: {output}")


# ── Alternative: step-by-step pipeline ─────────────────────
def step_by_step_example():
    """Shows how to use each component individually."""
    script = "Este es un video creado paso a paso con la librería."

    # 1. TTS → audio + word timestamps
    narration = generate_narration_sync(
        text=script,
        voice="es-MX-DaliaNeural",
        output_path="narration.mp3",
    )
    print(f"Narration: {narration.duration_ms:.0f}ms, {len(narration.words)} words")

    # 2. Generate SRT subtitles
    srt_content = blocks_to_srt(narration.blocks)
    with open("subtitles.srt", "w", encoding="utf-8") as f:
        f.write(srt_content)
    print(f"Subtitles: {len(narration.blocks)} blocks -> subtitles.srt")

    # 3. Compose with ffmpeg (manually)
    from video_templator import FfmpegCompositor, TemplateConfig

    compositor = FfmpegCompositor(TemplateConfig())
    compositor.compose(
        primary_clip="gameplay.mp4",
        narration_path="narration.mp3",
        subtitles_path="subtitles.srt",
        output="output_step_by_step.mp4",
    )
    print("Video composed with ffmpeg.")


if __name__ == "__main__":
    asyncio.run(main())
