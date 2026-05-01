"""Custom TTS plugin using Chutes Kokoro API."""

import os
import uuid
import wave
import io
from typing import Optional

from livekit.agents import tts, APIConnectOptions, DEFAULT_API_CONNECT_OPTIONS
from livekit.agents.tts import (
    TTS,
    ChunkedStream,
    SynthesizedAudio,
    TTSCapabilities,
    AudioEmitter,
)
from livekit import rtc
import httpx

SAMPLE_RATE = 24000
NUM_CHANNELS = 1


class ChutesTTS(TTS):
    def __init__(
        self,
        *,
        api_token: Optional[str] = None,
        voice: str = "af_heart",
        speed: float = 1.0,
    ):
        super().__init__(
            capabilities=TTSCapabilities(streaming=False),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
        )
        self._api_token = api_token or os.environ.get("CHUTES_API_TOKEN", "")
        self._voice = voice
        self._speed = speed
        self._base_url = "https://chutes-kokoro.chutes.ai/speak"

    @property
    def model(self) -> str:
        return f"kokoro-82m-{self._voice}"

    @property
    def provider(self) -> str:
        return "chutes"

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> ChunkedStream:
        return ChutesChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
            api_token=self._api_token,
            base_url=self._base_url,
            voice=self._voice,
            speed=self._speed,
        )


class ChutesChunkedStream(ChunkedStream):
    def __init__(
        self,
        *,
        tts: ChutesTTS,
        input_text: str,
        conn_options: APIConnectOptions,
        api_token: str,
        base_url: str,
        voice: str,
        speed: float,
    ):
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._api_token = api_token
        self._base_url = base_url
        self._voice = voice
        self._speed = speed

    async def _run(self, output_emitter: AudioEmitter) -> None:
        """Fetch audio from Chutes Kokoro API and push to emitter."""
        request_id = uuid.uuid4().hex[:12]

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "text": self._input_text,
                    "speed": self._speed,
                    "voice": self._voice,
                },
            )

            if resp.status_code != 200:
                raise tts.TTSError(
                    f"Chutes Kokoro error ({resp.status_code}): {resp.text[:200]}"
                )

            wav_bytes = resp.content

        # Parse WAV to extract raw PCM
        with io.BytesIO(wav_bytes) as buf:
            with wave.open(buf, "rb") as wf:
                sample_rate = wf.getframerate()
                num_channels = wf.getnchannels()
                frame_bytes = wf.readframes(wf.getnframes())

        # Convert raw PCM bytes to AudioFrame
        audio_frame = rtc.AudioFrame(
            data=frame_bytes,
            sample_rate=sample_rate,
            num_channels=num_channels,
            samples_per_channel=len(frame_bytes) // (num_channels * 2),
        )

        output_emitter.initialize(
            request_id=request_id,
            sample_rate=sample_rate,
            num_channels=num_channels,
            mime_type="audio/pcm",
        )
        output_emitter.start_segment(segment_id=request_id)
        output_emitter.push(audio_frame.data.tobytes() if hasattr(audio_frame.data, 'tobytes') else bytes(audio_frame.data))
        output_emitter.end_segment()
        output_emitter.end_input()
