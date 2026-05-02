"""
TTS Voiceover Module
Supports multiple backends: speak (Chutes Kokoro), edge-tts (free), espeak (local)
"""

import subprocess
import tempfile as _tempfile
import asyncio
import json
import os
from pathlib import Path

TMP_DIR = Path(__file__).parent.parent / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)


def tempfile(**kwargs):
    """Local tempfile wrapper — puts everything in ./tmp/ no /tmp."""
    if "dir" not in kwargs:
        kwargs["dir"] = str(TMP_DIR)
    return _tempfile.mktemp(**kwargs)

VOICES = {
    "kokoro": {
        "af_heart": "Female, warm, expressive — good for reviews",
        "af_bella": "Female, friendly, engaging",
        "am_michael": "Male, professional, calm",
        "am_adam": "Male, energetic, upbeat",
    },
    "edge": {
        "en-US-JennyNeural": "Female, natural US English",
        "en-US-GuyNeural": "Male, natural US English",
        "en-GB-SoniaNeural": "Female, British English",
        "en-GB-RyanNeural": "Male, British English",
    }
}


def speak_kokoro(text: str, voice: str = "af_heart", speed: float = 1.0,
                 output_path: str = None, chutes_token: str = None) -> str:
    """
    Use the speak zsh function (Chutes Kokoro API) to generate TTS audio.
    Writes to output_path or returns raw audio bytes.
    """
    if output_path is None:
        output_path = tempfile(suffix=".wav")

    token = chutes_token or os.environ.get("CHUTES_API_TOKEN", "")
    if not token:
        raise ValueError("CHUTES_API_TOKEN not set and not provided")

    cmd = [
        "curl", "-s", "-X", "POST", "https://chutes-kokoro.chutes.ai/speak",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"text": text, "speed": speed, "voice": voice}),
        "-o", output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"Kokoro TTS failed: {result.stderr.decode()[:500]}")

    return output_path


async def speak_edge(text: str, voice: str = "en-US-JennyNeural",
                     output_path: str = None) -> str:
    """
    Use edge-tts (free, Microsoft Edge TTS) for high-quality voiceover.
    """
    import edge_tts

    if output_path is None:
        output_path = tempfile(suffix=".mp3")

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return output_path


def generate_speech(text: str, backend: str = "kokoro",
                    voice: str = "af_heart", speed: float = 1.0,
                    output_path: str = None) -> str:
    """Generate speech audio from text. Returns path to audio file."""
    if backend == "kokoro":
        return speak_kokoro(text, voice=voice, speed=speed, output_path=output_path)
    elif backend == "edge":
        return asyncio.run(speak_edge(text, voice=voice, output_path=output_path))
    else:
        raise ValueError(f"Unknown TTS backend: {backend}")


def generate_voiceover(script_path: str, output_path: str,
                       backend: str = "kokoro", voice: str = "af_heart",
                       speed: float = 1.0) -> str:
    """
    Generate a full voiceover from a script file.
    Script file format: one paragraph per line, blank lines = pause markers.
    Returns path to combined audio file.
    """
    with open(script_path) as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]

    audio_segments = []
    for i, paragraph in enumerate(lines):
        seg_path = tempfile(suffix=f"_seg{i}.wav")
        generate_speech(paragraph, backend=backend, voice=voice,
                        speed=speed, output_path=seg_path)
        audio_segments.append(seg_path)

    if len(audio_segments) == 1:
        import shutil
        shutil.copy(audio_segments[0], output_path)
        return output_path

    # Concatenate all segments with 0.3s silence between paragraphs
    concat_file = tempfile(suffix=".txt")
    with open(concat_file, "w") as f:
        for seg in audio_segments:
            f.write(f"file '{seg}'\n")
            f.write("duration 0.3\n")  # silence between paragraphs

    output_path = output_path or tempfile(suffix=".wav")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file, "-c", "copy", output_path
    ], capture_output=True, timeout=120)

    return output_path


def get_available_voices() -> dict:
    """Return available voices grouped by backend."""
    return VOICES


if __name__ == "__main__":
    # Quick test
    test_text = "This is a test of the TTS voiceover system. It seems to be working perfectly."
    out = generate_speech(test_text, backend="kokoro", output_path="/tmp/tts_test.wav")
    print(f"TTS test complete: {out}")
