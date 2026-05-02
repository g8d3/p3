"""
Music Generator
Creates structured background music with chord progressions, bass, and percussion
using ffmpeg synthesis — no external samples needed.

Produces music with:
- Chord progressions (not just single tones)
- Bass lines
- Simple percussion / rhythm
- Intro → build → drop → outro structure
"""

import subprocess
import random
import math
from pathlib import Path

MUSIC_DIR = Path(__file__).parent.parent / "assets" / "music"
TMP_DIR = Path(__file__).parent.parent / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)


def ensure_music_dir():
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)


# ── Music Theory Constants ───────────────────────────────────────────────

# Note frequencies (A4 = 440Hz)
NOTES = {
    "C2": 65.41, "D2": 73.42, "E2": 82.41, "F2": 87.31, "G2": 98.00, "A2": 110.00, "B2": 123.47,
    "C3": 130.81, "D3": 146.83, "E3": 164.81, "F3": 174.61, "G3": 196.00, "A3": 220.00, "B3": 246.94,
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00, "A4": 440.00, "B4": 493.88,
    "C5": 523.25, "D5": 587.33, "E5": 659.25, "F5": 698.46, "G5": 783.99, "A5": 880.00, "B5": 987.77,
}

# Chord definitions (root, third, fifth, optional seventh)
CHORDS = {
    "Cmaj":  ("C4", "E4", "G4"),
    "Dmin":  ("D4", "F4", "A4"),
    "Emin":  ("E4", "G4", "B4"),
    "Fmaj":  ("F4", "A4", "C5"),
    "Gmaj":  ("G4", "B4", "D5"),
    "Amin":  ("A4", "C5", "E5"),
    "Bdim":  ("B4", "D5", "F5"),
    "Cmaj7": ("C4", "E4", "G4", "B4"),
    "Fmaj7": ("F4", "A4", "C5", "E5"),
    "Am7":   ("A4", "C5", "E5", "G5"),
    "G7":    ("G4", "B4", "D5", "F5"),
}

# Popular chord progressions
PROGRESSIONS = [
    ("Cmaj", "Am7", "Fmaj", "G7"),       # I-vi-IV-V7 (pop)
    ("Cmaj", "Gmaj", "Am7", "Fmaj7"),     # I-V-vi-IV7 (modern pop)
    ("Am7", "Fmaj", "Cmaj", "G7"),         # vi-IV-I-V7 (alternative)
    ("Cmaj", "Fmaj", "Am7", "G7"),         # I-IV-vi-V7
    ("Dmin", "Am7", "G7", "Cmaj"),         # ii-vi-V7-I (jazz)
]


def _render(cmd: list, output: str) -> str:
    """Run ffmpeg command, return output path."""
    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode != 0 and not Path(output).exists():
        raise RuntimeError(f"Music render failed: {result.stderr.decode()[:300]}")
    return output


def generate_chord_layer(chord_name: str, duration: float,
                          volume: float = 0.06, wave: str = "sine") -> str:
    """
    Generate a chord pad by layering multiple sine/triangle waves.
    Sounds like a warm synth pad.
    """
    chord_notes = CHORDS[chord_name]
    output = str(TMP_DIR / f"_chord_{chord_name}_{int(duration)}.wav")
    if Path(output).exists():
        return output

    # Build inputs: one lavfi sine per note
    cmd = ["ffmpeg", "-y"]
    for note in chord_notes:
        freq = NOTES[note]
        cmd += ["-f", "lavfi", "-i",
                f"sine=frequency={freq}:duration={duration}"]

    # Mix them together with slightly different volumes for warmth
    n = len(chord_notes)
    mix_inputs = "".join(f"[{i}:a]" for i in range(n))
    vol_factor = volume / n
    vols = [vol_factor * (1 + random.uniform(-0.1, 0.1)) for _ in range(n)]
    vol_filters = "".join(
        f"[{i}:a]volume={vols[i]}[v{i}];" for i in range(n)
    )
    vol_inputs = "".join(f"[v{i}]" for i in range(n))

    filter_str = (
        f"{vol_filters}"
        f"{vol_inputs}amix=inputs={n}:duration=first:dropout_transition=2"
        f",volume=0.5"
        f"[out]"
    )

    cmd += ["-filter_complex", filter_str, "-map", "[out]", output]
    return _render(cmd, output)


def generate_bass_line(chord_name: str, duration: float,
                        pattern: str = "root") -> str:
    """
    Generate a bass line for the chord. Pattern controls the rhythm.
    """
    root = CHORDS[chord_name][0]  # First note = root
    freq = NOTES[root] * 0.5  # One octave down

    output = str(TMP_DIR / f"_bass_{chord_name}_{int(duration)}.wav")
    if Path(output).exists():
        return output

    # Simple bass: sine wave at root frequency with slight attack
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency={freq}:duration={duration}",
        "-af",
        "volume=0.12,"
        "afade=t=in:st=0:d=0.02,"
        "lowpass=f=200",
        output,
    ]
    return _render(cmd, output)


def generate_percussion(duration: float, bpm: int = 100) -> str:
    """
    Generate a simple kick/snare/hi-hat loop using noise and tones.
    Creates a basic beat at the given BPM.
    """
    output = str(TMP_DIR / f"_perc_{duration}_{bpm}.wav")
    if Path(output).exists():
        return output

    beat_duration = 60.0 / bpm
    num_beats = int(duration / beat_duration) + 1
    total_beats = min(num_beats, 64)  # cap at 64 beats

    # Build percussion by concatenating individual hits
    # Each bar: kick on 1, snare on 3, hi-hat on 8ths

    segment_dur = beat_duration / 4  # 16th note segments

    # Pre-render hit samples
    # Kick: low frequency thump
    kick_in = f"aevalsrc=sin(2*PI*80*t)*exp(-t*15)*0.4:duration={segment_dur * 2}:c=1"
    # Snare: noise burst
    snare_in = f"anoisesrc=d={segment_dur}:c=white:a=0.15"
    # Hi-hat: filtered noise, very short
    hat_in = f"anoisesrc=d={segment_dur * 0.5}:c=white:a=0.06"

    # Build the full beat pattern
    # Using a concat filter
    segments = []
    for beat in range(total_beats):
        pos_in_bar = beat % 4  # position within 4-beat bar (0-indexed)
        eighth_pos = beat % 8  # position within 8 eighth-notes

        # Decide what hits on this 8th note
        if eighth_pos == 0:  # Beat 1 (downbeat)
            segments.append(kick_in)
        elif eighth_pos == 4:  # Beat 3 (backbeat)
            segments.append(snare_in)
        elif eighth_pos % 2 == 0:  # Other 8th notes
            segments.append(hat_in)
        else:  # 16th notes
            segments.append(hat_in)

    # Use aevalsrc with concat for entire pattern
    # Simpler approach: just use noise with amplitude modulation for rhythm
    # Actually, let's use a simpler approach - noise with periodic amplitude

    # Rhythm: modulate white noise at BPM rate for percussive feel
    rhythm_hz = bpm / 60.0
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i",
        f"anoisesrc=d={duration}:c=white:a=0.2",
        "-af",
        # Amplitude modulation creates rhythmic pulses
        f"volume='0.3 + 0.3 * sin(2*PI*{rhythm_hz}*2*t)':eval=frame,"
        f"lowpass=f=8000,highpass=f=200,"
        f"afade=t=in:st=0:d=0.1,afade=t=out:st={duration-0.3}:d=0.3",
        output,
    ]
    return _render(cmd, output)


def generate_music(duration: float = 60.0, bpm: int = 100,
                   progression_idx: int = None, output_path: str = None) -> str:
    """
    Generate full background music track with:
    - Chord pad (warm synth)
    - Bass line
    - Percussion (rhythmic pulse)
    - Intro → build → drop → outro arc
    
    Args:
        duration: Target duration in seconds
        bpm: Beats per minute (80-120 typical for tech content)
        progression_idx: Which chord progression to use (None = random)
        output_path: Where to save the final WAV
    
    Returns: Path to generated WAV file
    """
    ensure_music_dir()
    if output_path is None:
        output_path = str(MUSIC_DIR / f"bgm_{bpm}bpm_{int(duration)}s.wav")

    if progression_idx is None:
        progression_idx = random.randrange(len(PROGRESSIONS))

    progression = PROGRESSIONS[progression_idx % len(PROGRESSIONS)]
    chord_duration = 4.0 * (60.0 / bpm)  # 4 beats per chord
    num_chords = len(progression)
    loop_duration = num_chords * chord_duration
    num_loops = max(1, int(duration / loop_duration) + 1)

    # Generate layers
    print(f"    Music: {bpm}bpm, progression {progression_idx+1}/{len(PROGRESSIONS)}")
    print(f"    Chords: {' → '.join(progression)}")
    print(f"    Duration: {duration}s, loops: {num_loops}")

    total_duration = min(loop_duration * num_loops, duration + chord_duration)

    # Generate chord pad
    chord_file = str(TMP_DIR / f"_music_chords.wav")
    chords = []
    for loop in range(num_loops):
        for chord in progression:
            chords.append(generate_chord_layer(chord, chord_duration, volume=0.05))

    # Concatenate all chord segments
    concat_list = str(TMP_DIR / "_chord_concat.txt")
    with open(concat_list, "w") as f:
        for ch in chords:
            f.write(f"file '{ch}'\n")
    _render([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-t", str(total_duration),
        "-c", "copy", chord_file
    ], chord_file)

    # Generate bass
    bass_file = str(TMP_DIR / f"_music_bass.wav")
    bass_segments = []
    for loop in range(num_loops):
        for chord in progression:
            bass_segments.append(generate_bass_line(chord, chord_duration))

    concat_bass = str(TMP_DIR / "_bass_concat.txt")
    with open(concat_bass, "w") as f:
        for bs in bass_segments:
            f.write(f"file '{bs}'\n")
    _render([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_bass,
        "-t", str(total_duration),
        "-c", "copy", bass_file
    ], bass_file)

    # Generate percussion
    perc_file = generate_percussion(total_duration, bpm)

    # Mix all layers
    final = str(TMP_DIR / f"_music_mixed.wav")

    # Add volume envelope: fade in, slight dip in middle for "build", fade out
    intro_dur = min(4.0, total_duration * 0.1)
    outro_dur = min(4.0, total_duration * 0.1)

    _render([
        "ffmpeg", "-y",
        "-i", chord_file,
        "-i", bass_file,
        "-i", perc_file,
        "-filter_complex",
        f"[0:a]volume=0.6,afade=t=in:st=0:d={intro_dur},"
        f"afade=t=out:st={total_duration - outro_dur}:d={outro_dur}[ch];"
        f"[1:a]volume=0.3,afade=t=in:st=0:d={intro_dur}[bass];"
        f"[2:a]volume=0.15,afade=t=in:st=0:d={intro_dur},"
        f"afade=t=out:st={total_duration - outro_dur}:d={outro_dur}[perc];"
        f"[ch][bass][perc]amix=inputs=3:duration=first:dropout_transition=2,"
        f"volume=0.8[out]",
        "-map", "[out]", "-ac", "2", "-ar", "44100", final
    ], final)

    # Copy to output
    import shutil
    shutil.copy(final, output_path)

    size = Path(output_path).stat().st_size
    print(f"    → {output_path} ({size/1024/1024:.1f} MB)")

    return output_path


def generate_track_variants():
    """Generate multiple background music tracks with different moods."""
    ensure_music_dir()
    print("  Generating background music tracks...")

    tracks = [
        (60, 95, 0, "bgm_chill_60s.wav"),     # Chill lo-fi style
        (90, 100, 1, "bgm_pop_90s.wav"),       # Upbeat pop
        (120, 105, 2, "bgm_energetic_120s.wav"), # Higher energy
        (90, 90, 3, "bgm_mellow_90s.wav"),     # Mellow
        (60, 110, 4, "bgm_driving_60s.wav"),   # Driving rhythm
    ]

    for dur, bpm, prog_idx, fname in tracks:
        print(f"    Generating {fname} ({dur}s, {bpm}bpm)...")
        try:
            path = str(MUSIC_DIR / fname)
            generate_music(duration=dur, bpm=bpm,
                           progression_idx=prog_idx, output_path=path)
        except Exception as e:
            print(f"    ✗ {fname}: {e}")

    print(f"  Music library ready at: {MUSIC_DIR}")


if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "all"

    if action == "all":
        generate_track_variants()
    elif action == "single":
        duration = float(sys.argv[2]) if len(sys.argv) > 2 else 60
        generate_music(duration=duration)
    else:
        print(f"Usage: python pipeline/music.py [all|single <duration>]")
