"""Audio transcription handler using Google Gemini."""

from __future__ import annotations

import io
import logging
import os
import wave
from pathlib import Path

from google import genai
from google.genai import types as genai_types

from src.config import get_settings

logger = logging.getLogger(__name__)


def transcribe_audio(audio_data: bytes, mime_type: str) -> str:
    """Transcribe audio data using Google Gemini.

    Converts raw PCM16 samples to WAV format when necessary (Chainlit
    streams ``pcm16`` from the browser microphone, which Gemini does not
    accept as-is), then sends the audio to Google Gemini for transcription.

    Args:
        audio_data: Raw audio bytes.
        mime_type: MIME type of the audio data (e.g. ``"audio/webm"``).

    Returns:
        Transcribed text, or empty string if transcription produced nothing.

    Raises:
        Exception: If the Gemini API call fails.
    """
    # Chainlit's browser audio capture sends raw PCM16 samples (no container).
    # Gemini requires a proper audio format, so wrap them in a WAV container.
    if "pcm" in mime_type.lower():
        sample_rate = 24000  # matches [features.audio] sample_rate in config.toml
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)       # mono
            wf.setsampwidth(2)       # 16-bit = 2 bytes per sample
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)
        audio_data = buf.getvalue()
        mime_type = "audio/wav"
        logger.debug("Converted PCM16 to WAV: %d bytes", len(audio_data))

    settings = get_settings()

    # Ensure Vertex AI credentials are set
    key_path = Path(__file__).resolve().parent.parent / "agent" / "nodes" / "google-key.json"
    if key_path.exists():
        os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", str(key_path))

    client = genai.Client(
        vertexai=True,
        project=settings.google_project,
        location=settings.google_location,
    )

    response = client.models.generate_content(
        model=settings.google_model,
        contents=[
            genai_types.Content(
                role="user",
                parts=[
                    genai_types.Part.from_bytes(data=audio_data, mime_type=mime_type),
                    genai_types.Part.from_text(
                        text="Transcribe the audio above accurately. "
                        "Return ONLY the transcription, no commentary."
                    ),
                ],
            )
        ],
    )

    return (response.text or "").strip()
