"""
Pro Sound Effects Library
Generates professional-quality SFX using ffmpeg synthesis.
Uses noise shaping, bandpass sweeps, envelope shaping, and layering —
not just sine tones.
"""

import subprocess
import shutil
import os
from pathlib import Path

SFX_DIR = Path(__file__).parent.parent / "assets" / "sfx"
TMP_DIR = Path(__file__).parent.parent / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)


def ensure_sfx_dir():
    SFX_DIR.mkdir(parents=True, exist_ok=True)


def _render(cmd: list, output: str) -> str:
    """Run ffmpeg command, return output path."""
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode != 0 and not Path(output).exists():
        raise RuntimeError(f"SFX render failed: {result.stderr.decode()[:300]}")
    return output


# ── Transitions ──────────────────────────────────────────────────────────


def generate_whoosh() -> str:
    """
    Professional whoosh: pink noise with bandpass sweep + pitch envelope.
    Sounds like a real trailer/video transition whoosh.
    """
    output = str(SFX_DIR / "whoosh.wav")
    if Path(output).exists():
        return output
    ensure_sfx_dir()
    noise = str(TMP_DIR / "_whoosh_noise.wav")
    # Step 1: Pink noise
    _render([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=d=0.6:c=pink:a=0.8",
        noise
    ], noise)
    # Step 2: Bandpass sweep + fade envelope
    _render([
        "ffmpeg", "-y", "-i", noise,
        "-af", "bandpass=frequency=3000:width_type=h:width=300,"
               "afade=t=in:st=0:d=0.1,afade=t=out:st=0.4:d=0.2,"
               "volume=0.6",
        output
    ], output)
    return output


def generate_riser() -> str:
    """
    Tension riser: noise + tone that pitch-rises. Good before a reveal/punchline.
    Uses aevalsrc for robust pitch sweep (compatible with ffmpeg 6.x).
    """
    output = str(SFX_DIR / "riser.wav")
    if Path(output).exists():
        return output
    ensure_sfx_dir()
    _render([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        "aevalsrc=sin(2*PI*(200 + t*300)*t)*0.3:duration=1.2",
        "-f", "lavfi", "-i", "anoisesrc=d=1.2:c=pink:a=0.5",
        "-filter_complex",
        "[1:a]bandpass=frequency=6000:width_type=h:width=1000,"
        "afade=t=in:st=0:d=0.1,afade=t=out:st=1.0:d=0.2,volume=0.35[noise];"
        "[0:a]afade=t=in:st=0:d=0.15,"
        "afade=t=out:st=1.0:d=0.2,"
        "volume=0.3[tone];"
        "[noise][tone]amix=inputs=2:duration=first,volume=0.6[out]",
        "-map", "[out]", output
    ], output)
    return output


# ── Impacts / Stings ─────────────────────────────────────────────────────


def generate_impact() -> str:
    """
    Cinematic impact: sub boom + transient noise burst.
    Good for emphasizing a statement or section transition.
    Uses aevalsrc for robust sub-frequency sweep.
    """
    output = str(SFX_DIR / "impact.wav")
    if Path(output).exists():
        return output
    ensure_sfx_dir()
    _render([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        "aevalsrc=sin(2*PI*(80 - t*60)*t)*0.5:duration=0.4",
        "-f", "lavfi", "-i", "anoisesrc=d=0.15:c=white:a=1.0",
        "-filter_complex",
        "[0:a]afade=t=in:st=0:d=0.01,"
        "afade=t=out:st=0.35:d=0.05,"
        "volume=0.5[sub];"
        "[1:a]bandpass=frequency=2000:width_type=h:width=2000,"
        "afade=t=in:st=0:d=0.001,afade=t=out:st=0.1:d=0.05,volume=0.3[hit];"
        "[sub][hit]amix=inputs=2:duration=first,volume=0.7[out]",
        "-map", "[out]", output
    ], output)
    return output


def generate_stinger() -> str:
    """
    Short emphasis sting: quick rise + thump. For punctuating a joke.
    """
    output = str(SFX_DIR / "stinger.wav")
    if Path(output).exists():
        return output
    ensure_sfx_dir()
    _render([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        "aevalsrc=sin(2*PI*(150 + t*600)*t)*0.3:duration=0.25",
        "-f", "lavfi", "-i", "sine=frequency=600:duration=0.15",
        "-f", "lavfi", "-i", "anoisesrc=d=0.1:c=white:a=1.0",
        "-filter_complex",
        "[0:a]volume=0.4,afade=t=in:st=0:d=0.01,"
        "afade=t=out:st=0.2:d=0.05[sub];"
        "[1:a]volume=0.2,afade=t=out:st=0.1:d=0.05[ping];"
        "[2:a]bandpass=frequency=3000:width_type=h:width=2000,"
        "afade=t=in:st=0:d=0.001,afade=t=out:st=0.05:d=0.05,volume=0.15[noise];"
        "[sub][ping][noise]amix=inputs=3:duration=first,volume=0.8[out]",
        "-map", "[out]", output
    ], output)
    return output


# ── Comedy / Personality ─────────────────────────────────────────────────


def generate_boing() -> str:
    """
    Cartoon spring boing. Frequency sweep down with bounce.
    """
    output = str(SFX_DIR / "boing.wav")
    if Path(output).exists():
        return output
    ensure_sfx_dir()

    # Create using longer single tone with pitch envelope
    # "Boing" effect: fast descending pitch with a bounce at the end
    _render([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "sine=frequency=600:duration=0.35",
        "-filter_complex",
        "[0:a]volume=0.4,"
        "asetrate=600*2^(-t/0.35*4+1),aresample=44100,"
        "afade=t=out:st=0.25:d=0.1[boing];"
        "[boing]volume=0.6[out]",
        "-map", "[out]", output
    ], output)
    return output


def generate_laugh() -> str:
    """
    Short synthesized laugh: multi-tone wobble.
    Not perfect but much better than current.
    """
    output = str(SFX_DIR / "laugh.wav")
    if Path(output).exists():
        return output
    ensure_sfx_dir()
    # Alternating pitch wobble to simulate a chuckle
    _render([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        "sine=frequency=500:duration=0.6",
        "-filter_complex",
        "[0:a]volume=0.25,"
        "asetrate=500*(1+0.3*sin(2*PI*t*12)),aresample=44100,"
        "afade=t=in:st=0:d=0.05,afade=t=out:st=0.5:d=0.1[out]",
        "-map", "[out]", output
    ], output)
    return output


# ── UI / Interaction Sounds ──────────────────────────────────────────────


def generate_click() -> str:
    """Clean UI click: short noise burst + tone."""
    output = str(SFX_DIR / "click.wav")
    if Path(output).exists():
        return output
    ensure_sfx_dir()
    _render([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "anoisesrc=d=0.03:c=white:a=0.8",
        "-f", "lavfi", "-i", "sine=frequency=1200:duration=0.02",
        "-filter_complex",
        "[0:a]bandpass=frequency=4000:width_type=h:width=2000,"
        "afade=t=in:st=0:d=0.001,afade=t=out:st=0.02:d=0.01,volume=0.3[noise];"
        "[1:a]volume=0.15,afade=t=out:st=0.015:d=0.005[tone];"
        "[noise][tone]amix=inputs=2:duration=first,volume=0.5[out]",
        "-map", "[out]", output
    ], output)
    return output


def generate_type_key() -> str:
    """Keyboard typing click."""
    output = str(SFX_DIR / "type_key.wav")
    if Path(output).exists():
        return output
    ensure_sfx_dir()
    _render([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "anoisesrc=d=0.02:c=white:a=0.6",
        "-af", "bandpass=frequency=3000:width_type=h:width=500,"
               "afade=t=in:st=0:d=0.001,afade=t=out:st=0.01:d=0.01,volume=0.25",
        output
    ], output)
    return output


# ── Ambience ──────────────────────────────────────────────────────────────


def generate_drum_roll() -> str:
    """Snare-style drum roll (noise + resonance)."""
    output = str(SFX_DIR / "drum_roll.wav")
    if Path(output).exists():
        return output
    ensure_sfx_dir()
    _render([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "anoisesrc=d=1.0:c=brown:a=0.8",
        "-af",
        "lowpass=f=200,"
        "afade=t=in:st=0:d=0.1,afade=t=out:st=0.8:d=0.2,"
        "volume=0.4",
        output
    ], output)
    return output


def generate_applause() -> str:
    """Applause-like noise burst."""
    output = str(SFX_DIR / "applause.wav")
    if Path(output).exists():
        return output
    ensure_sfx_dir()
    _render([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "anoisesrc=d=2.5:c=white:a=0.2",
        "-af",
        "lowpass=f=5000,highpass=f=300,"
        "afade=t=in:st=0:d=0.3,afade=t=out:st=2.0:d=0.5,"
        "volume=0.35",
        output
    ], output)
    return output


# ── New: Transition / Impact variations ──────────────────────────────────


def generate_swoosh() -> str:
    """Softer whoosh variant for gentle transitions."""
    output = str(SFX_DIR / "swoosh.wav")
    if Path(output).exists():
        return output
    ensure_sfx_dir()
    _render([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "anoisesrc=d=0.4:c=pink:a=0.5",
        "-af",
        "bandpass=frequency=2000:width_type=h:width=500,"
        "afade=t=in:st=0:d=0.05,afade=t=out:st=0.3:d=0.1,"
        "volume=0.35",
        output
    ], output)
    return output


# ── Generation ───────────────────────────────────────────────────────────


GENERATORS = [
    ("whoosh", generate_whoosh),
    ("riser", generate_riser),
    ("impact", generate_impact),
    ("stinger", generate_stinger),
    ("boing", generate_boing),
    ("laugh", generate_laugh),
    ("click", generate_click),
    ("type_key", generate_type_key),
    ("drum_roll", generate_drum_roll),
    ("applause", generate_applause),
    ("swoosh", generate_swoosh),
]


def generate_all_sfx():
    """Generate all SFX files."""
    ensure_sfx_dir()
    print("  Generating SFX library...")
    for name, func in GENERATORS:
        try:
            path = func()
            size = Path(path).stat().st_size
            print(f"    ✓ {name}: {size/1024:.0f} KB")
        except Exception as e:
            print(f"    ✗ {name}: {e}")
    print(f"  SFX library ready at: {SFX_DIR}")


def get_sfx_map() -> dict:
    """Return mapping of SFX names to file paths."""
    ensure_sfx_dir()
    return {name: str(SFX_DIR / f"{name}.wav") for name, _ in GENERATORS}


if __name__ == "__main__":
    generate_all_sfx()
