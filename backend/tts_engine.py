# ============================================================
# tts_engine.py — Text-to-Speech using edge-tts
#   Produces 16-bit 16 kHz mono PCM chunks for ESP32-S3 I2S
# ============================================================
import io
import asyncio
import edge_tts
import numpy as np
import soundfile as sf
from typing import AsyncGenerator

# Choose a natural voice — en-US-AriaNeural is warm and clear
DEFAULT_VOICE = "en-US-AriaNeural"
TARGET_RATE   = 16000  # Hz — must match ESP32 I2S sample rate
CHUNK_BYTES   = 2048   # ~64ms per chunk at 16kHz 16-bit mono

async def synthesize_chunks(text: str,
                             voice: str = DEFAULT_VOICE) -> AsyncGenerator[bytes, None]:
    """
    Async generator that yields 16-bit signed PCM chunks at 16 kHz
    for streaming to the ESP32-S3 I2S speaker.
    """
    if not text:
        return

    # edge-tts produces MP3 in memory; we convert to raw PCM
    communicate = edge_tts.Communicate(text, voice=voice, rate="+0%")

    # Collect all MP3 bytes
    mp3_buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_buffer.write(chunk["data"])

    mp3_buffer.seek(0)
    if mp3_buffer.getbuffer().nbytes == 0:
        return

    # Decode MP3 → float32 numpy array via soundfile
    audio_float, original_sr = sf.read(mp3_buffer, dtype="float32", always_2d=False)

    # Resample to 16 kHz if needed (simple linear interpolation)
    if original_sr != TARGET_RATE:
        ratio     = TARGET_RATE / original_sr
        new_len   = int(len(audio_float) * ratio)
        indices   = np.linspace(0, len(audio_float) - 1, new_len)
        audio_float = np.interp(indices, np.arange(len(audio_float)), audio_float)

    # Ensure mono
    if audio_float.ndim > 1:
        audio_float = audio_float.mean(axis=1)

    # Convert to 16-bit signed PCM
    audio_int16 = (audio_float * 32767).clip(-32768, 32767).astype(np.int16)
    raw_bytes   = audio_int16.tobytes()

    # Yield in fixed-size chunks for smooth I2S streaming
    for i in range(0, len(raw_bytes), CHUNK_BYTES):
        yield raw_bytes[i : i + CHUNK_BYTES]
