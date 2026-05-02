"""
Video Assembly Engine
Combines screen recording + TTS narration + background music + SFX + subtitles + memes
into a final video using ffmpeg.
"""

import subprocess
import tempfile as _tempfile
import json
import os
import random
from pathlib import Path

TMP = Path(__file__).parent.parent / "tmp"
TMP.mkdir(parents=True, exist_ok=True)


def tmpfile(**kw):
    if "dir" not in kw: kw["dir"] = str(TMP)
    return _tempfile.mktemp(**kw)


class VideoAssembler:
    """Builds final videos from component assets using ffmpeg."""

    def __init__(self, output_dir: str = "/tmp/assembled"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir = Path(__file__).parent.parent / "assets"

    def assemble(self, recording_path: str, narration_path: str,
                 output_path: str = None, title: str = "video",
                 bg_music: str = None, subtitles_path: str = None,
                 sfx_timing: list = None, meme_overlays: list = None,
                 intro_duration: float = 2.0,
                 outro_duration: float = 2.0) -> str:
        """
        Full video assembly pipeline.
        
        Args:
            recording_path: Path to screen recording MP4
            narration_path: Path to TTS narration audio
            output_path: Desired output path
            title: Video title for metadata
            bg_music: Path to background music (or None to skip)
            subtitles_path: Path to SRT subtitle file (or None)
            sfx_timing: List of (time_in_seconds, sfx_file) tuples
            meme_overlays: List of (time_in_seconds, meme_image_path) tuples
            intro_duration: Seconds of intro silence before narration
            outro_duration: Seconds of hold after narration ends
        
        Returns: Path to final video
        """
        if output_path is None:
            output_path = str(self.output_dir / f"{title.replace(' ', '_')}.mp4")

        # Get duration of narration
        narration_duration = self._get_audio_duration(narration_path)
        total_duration = narration_duration + intro_duration + outro_duration

        # Step 1: Mix narration + background music
        mixed_audio = self._mix_audio(narration_path, bg_music, sfx_timing)

        # Step 2: Trim/extend recording to match narration
        trimmed_recording = self._trim_to_duration(recording_path, total_duration)

        # Step 3: Add subtitles if provided
        if subtitles_path:
            subtitled_video = self._burn_subtitles(trimmed_recording, subtitles_path)
            trimmed_recording = subtitled_video

        # Step 4: Add intro slate
        with_intro = self._add_intro_slate(trimmed_recording, title, intro_duration)

        # Step 5: Add meme overlays
        with_memes = self._add_meme_overlays(with_intro, meme_overlays)

        # Step 6: Compose final video with mixed audio
        final = self._compose_final(with_memes, mixed_audio, output_path)

        return final

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "json", audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])

    def _get_video_duration(self, video_path: str) -> float:
        """Get duration of video file in seconds."""
        return self._get_audio_duration(video_path)

    def _mix_audio(self, narration_path: str, bg_music_path: str = None,
                   sfx_timing: list = None) -> str:
        """
        Mix narration with background music and SFX.
        Returns path to mixed audio file.
        """
        output = tmpfile(suffix="_mixed.wav")

        if bg_music_path and os.path.exists(bg_music_path):
            # Get narration duration
            nar_dur = self._get_audio_duration(narration_path)

            # Build complex filter: background music at 15% volume, narration on top
            filter_complex = (
                f"[0:a]volume=0.15[a_bg];"
                f"[1:a]adelay=2000|2000[a_nar];"  # 2s delay for intro
                f"[a_bg][a_nar]amix=inputs=2:duration=longest[aout]"
            )

            cmd = [
                "ffmpeg", "-y",
                "-i", bg_music_path,
                "-i", narration_path,
                "-filter_complex", filter_complex,
                "-map", "[aout]",
                "-ac", "2",
                "-ar", "44100",
                output,
            ]

            # Add a 2-second fade in / fade out for the music
            # Override with atrim to match narration length
            # ── Adjust narration volume here ──────────────────────────
            # To make it louder: increase the volume= value below.
            # 3.0 = 3x louder than original TTS. 5.0 = 5x louder.
            # Or use: python adjust_volume.py video.mp4 --boost X
            # ──────────────────────────────────────────────────────────
            filter_complex_simple = (
                f"[0:a]volume=0.15,atrim=0:{nar_dur + 4}[a_bg];"
                f"[1:a]volume=4.0,adelay=2000|2000[a_nar];"
                f"[a_bg][a_nar]amix=inputs=2:duration=longest:dropout_transition=0[aout]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", bg_music_path,
                "-i", narration_path,
                "-filter_complex", filter_complex_simple,
                "-map", "[aout]",
                output,
            ]
        else:
            # Just use narration with 2s silence padding at start
            cmd = [
                "ffmpeg", "-y",
                "-i", narration_path,
                "-af", "adelay=2000|2000,apad=pad_dur=2",
                output,
            ]

        # Add SFX at specific timestamps (post-mix overlay)
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            print(f"Audio mix warning: {result.stderr.decode()[:300]}")
            # Fallback: just use narration directly
            import shutil
            shutil.copy(narration_path, output)
            # Add silence padding
            subprocess.run([
                "ffmpeg", "-y", "-i", output,
                "-af", "adelay=2000|2000,apad=pad_dur=2",
                output.replace(".wav", "_padded.wav"),
            ], capture_output=True, timeout=60)
            padded = output.replace(".wav", "_padded.wav")
            if os.path.exists(padded):
                return padded
            return output

        # Add SFX overlays if any
        if sfx_timing:
            output = self._apply_sfx(output, sfx_timing)

        return output

    def _apply_sfx(self, audio_path: str, sfx_timing: list) -> str:
        """Overlay sound effects at specified timestamps."""
        output = tmpfile(suffix="_sfx.wav")

        # Build filter_complex for multiple SFX overlays
        inputs = [audio_path]
        filters = []
        for i, (time_sec, sfx_file) in enumerate(sfx_timing):
            if not os.path.exists(sfx_file):
                continue
            inputs.append(sfx_file)
            sfx_idx = i + 1
            # Place SFX at the correct time offset
            filters.append(
                f"[{sfx_idx}:a]adelay={int(time_sec * 1000)}|{int(time_sec * 1000)}[s{sfx_idx}]"
            )

        if not filters:
            return audio_path

        # Mix all together
        sfx_inputs = "".join(f"[s{i + 1}]" for i in range(len(sfx_timing)))
        mix_inputs = f"[0:a]{sfx_inputs}"
        filter_str = ";".join(filters)
        # normalize=0 prevents amix from dividing volume by input count
        # (was causing volume to drop to 1/18th during 17-SFX moments)
        filter_str += f";{mix_inputs}amix=inputs={len(inputs)}:duration=longest:normalize=0[aout]"

        cmd = ["ffmpeg", "-y"] + \
              sum([["-i", inp] for inp in inputs], []) + \
              ["-filter_complex", filter_str,
               "-map", "[aout]", output]

        subprocess.run(cmd, capture_output=True, timeout=120)
        return output

    def _trim_to_duration(self, video_path: str, target_duration: float) -> str:
        """Trim/loop video to match target duration."""
        vid_dur = self._get_video_duration(video_path)

        if vid_dur >= target_duration:
            # Trim
            output = tmpfile(suffix="_trimmed.mp4")
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-t", str(target_duration),
                "-c", "copy", output,
            ]
        else:
            # Loop to fill duration
            output = tmpfile(suffix="_looped.mp4")
            cmd = [
                "ffmpeg", "-y", "-stream_loop", "-1",
                "-i", video_path, "-t", str(target_duration),
                "-c", "copy", output,
            ]

        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            return video_path
        return output

    def _burn_subtitles(self, video_path: str, srt_path: str) -> str:
        """Burn subtitles into video."""
        output = tmpfile(suffix="_subtitled.mp4")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"subtitles={srt_path}:force_style='FontName=Ubuntu,FontSize=18,"
                    f"PrimaryCol=&H00FFFFFF,OutlineCol=&H00000000,BorderStyle=1,"
                    f"Outline=1,Shadow=1,MarginV=50'",
            "-c:a", "copy", output,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            return video_path
        return output

    def _add_intro_slate(self, video_path: str, title: str,
                          duration: float = 2.0) -> str:
        """Add an intro title card using ffmpeg drawtext."""
        # For now, just pad with black at start (proper title cards need more work)
        output = tmpfile(suffix="_intro.mp4")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"drawtext=text='{title}':fontsize=48:fontcolor=white:"
                    f"x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,0,{duration})'",
            "-c:a", "copy", output,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            return video_path
        return output

    def _add_meme_overlays(self, video_path: str,
                            meme_overlays: list = None) -> str:
        """Add meme/image overlays at specific timestamps."""
        if not meme_overlays:
            return video_path

        output = tmpfile(suffix="_memes.mp4")
        current_input = video_path

        for time_sec, meme_path in meme_overlays:
            if not os.path.exists(meme_path):
                continue

            temp_out = tmpfile(suffix="_meme_temp.mp4")
            cmd = [
                "ffmpeg", "-y", "-i", current_input,
                "-i", meme_path,
                "-filter_complex",
                f"[1:v]scale=iw/3:-1[ovr];"
                f"[0:v][ovr]overlay=W-w-20:H-h-20:enable='between(t,{time_sec},{time_sec + 3})'[v]",
                "-map", "[v]", "-map", "0:a", temp_out,
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode == 0:
                current_input = temp_out

        # Copy to final output
        import shutil
        shutil.copy(current_input, output)
        return output

    def _compose_final(self, video_path: str, audio_path: str,
                        output_path: str) -> str:
        """Compose final video with the mixed audio track."""
        temp_output = tmpfile(suffix="_final.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            temp_output,
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            # Fallback: just copy video with audio
            cmd_fallback = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_path,
            ]
            subprocess.run(cmd_fallback, capture_output=True, timeout=300)
        else:
            import shutil
            shutil.copy(temp_output, output_path)

        return output_path


def generate_sfx_timing(script_timing: list,
                        sfx_library: dict = None) -> list:
    """
    Generate a list of SFX events from script timing.
    Adds emphasis SFX at key moments in the script.
    """
    if sfx_library is None:
        sfx_library = {
            "emphasis": "/home/vuos/code/p3/s44/assets/sfx/emphasis.wav",
            "transition": "/home/vuos/code/p3/s44/assets/sfx/whoosh.wav",
            "laugh": "/home/vuos/code/p3/s44/assets/sfx/laugh.wav",
            "boing": "/home/vuos/code/p3/s44/assets/sfx/boing.wav",
            "drum_roll": "/home/vuos/code/p3/s44/assets/sfx/drum_roll.wav",
            "applause": "/home/vuos/code/p3/s44/assets/sfx/applause.wav",
        }

    sfx_events = []
    # Add transition SFX at segment boundaries
    for i, (start, end, text) in enumerate(script_timing):
        if i > 0:
            sfx_events.append((start, sfx_library.get("transition", "")))

        # Add emphasis on sentences with exclamation or question marks
        if "!" in text:
            sfx_events.append((start + 0.5, sfx_library.get("emphasis", "")))

        # Add laugh after punchlines
        if any(word in text.lower() for word in ["hilarious", "ridiculous",
                                                   "unbelievable", "you won't believe"]):
            sfx_events.append((end - 0.3, sfx_library.get("laugh", "")))

    return sfx_events


if __name__ == "__main__":
    assembler = VideoAssembler()
    print(f"Video assembler ready. Output dir: {assembler.output_dir}")
