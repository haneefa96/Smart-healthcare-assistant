# ============================================================
# tts_engine.py — Text-to-Speech using Edge-TTS
#   Produces 16-bit 16 kHz mono little-endian PCM chunks for ESP32-S3
# ============================================================
import io
import os
import asyncio
import logging
from typing import AsyncGenerator
import edge_tts
import numpy as np
import soundfile as sf

log = logging.getLogger(__name__)

# ── Baymax-Inspired English Settings ──────────────────────────────────────────
# Calm, gentle, deliberate, reassuring delivery approximating a companion assistant
DEFAULT_VOICE = os.getenv("TTS_DEFAULT_VOICE", "en-US-AndrewMultilingualNeural")
DEFAULT_RATE  = os.getenv("TTS_DEFAULT_RATE", "-12%")   # Slower rate for deliberate pacing
DEFAULT_PITCH = os.getenv("TTS_DEFAULT_PITCH", "-5Hz")   # Slightly lower pitch for grounded warmth
TARGET_RATE   = 16000    # Hz — required by ESP32-S3 I2S speaker
CHUNK_BYTES   = 2048     # ~64ms per chunk at 16 kHz 16-bit mono

# ── Multilingual Voice Map (Male Neural Voices for Indian Languages) ──────────
VOICE_MAP: dict[str, str] = {
    # English (Baymax-inspired male voice)
    "en": "en-US-AndrewMultilingualNeural",
    "english": "en-US-AndrewMultilingualNeural",
    "en-us": "en-US-AndrewMultilingualNeural",
    "en-in": "en-US-AndrewMultilingualNeural",

    # Hindi
    "hi": "hi-IN-MadhurNeural",
    "hindi": "hi-IN-MadhurNeural",
    "hi-in": "hi-IN-MadhurNeural",

    # Kannada
    "kn": "kn-IN-GaganNeural",
    "kannada": "kn-IN-GaganNeural",
    "kn-in": "kn-IN-GaganNeural",

    # Malayalam
    "ml": "ml-IN-MidhunNeural",
    "malayalam": "ml-IN-MidhunNeural",
    "ml-in": "ml-IN-MidhunNeural",

    # Tamil
    "ta": "ta-IN-ValluvarNeural",
    "tamil": "ta-IN-ValluvarNeural",
    "ta-in": "ta-IN-ValluvarNeural",

    # Telugu
    "te": "te-IN-MohanNeural",
    "telugu": "te-IN-MohanNeural",
    "te-in": "te-IN-MohanNeural",

    # Marathi
    "mr": "mr-IN-ManoharNeural",
    "marathi": "mr-IN-ManoharNeural",
    "mr-in": "mr-IN-ManoharNeural",

    # Gujarati
    "gu": "gu-IN-NiranjanNeural",
    "gujarati": "gu-IN-NiranjanNeural",
    "gu-in": "gu-IN-NiranjanNeural",

    # Bengali
    "bn": "bn-IN-BashkarNeural",
    "bengali": "bn-IN-BashkarNeural",
    "bangla": "bn-IN-BashkarNeural",
    "bn-in": "bn-IN-BashkarNeural",

    # Urdu
    "ur": "ur-IN-SalmanNeural",
    "urdu": "ur-IN-SalmanNeural",
    "ur-in": "ur-IN-SalmanNeural",
    "ur-pk": "ur-IN-SalmanNeural",
}


def get_supported_voices() -> dict[str, str]:
    """
    Return a copy of the canonical language-to-voice mapping.
    """
    return {
        "en": "en-US-AndrewMultilingualNeural",
        "hi": "hi-IN-MadhurNeural",
        "kn": "kn-IN-GaganNeural",
        "ml": "ml-IN-MidhunNeural",
        "ta": "ta-IN-ValluvarNeural",
        "te": "te-IN-MohanNeural",
        "mr": "mr-IN-ManoharNeural",
        "gu": "gu-IN-NiranjanNeural",
        "bn": "bn-IN-BashkarNeural",
        "ur": "ur-IN-SalmanNeural",
    }


def resolve_voice(
    language: str | None = None,
    voice: str | None = None
) -> tuple[str, str, str]:
    """
    Resolve the voice identifier, speaking rate, and pitch.
    Returns: (voice_id, rate_str, pitch_str)
    """
    # 1. If an explicit voice override is given
    if voice and voice.strip():
        v = voice.strip()
        if v.lower() in VOICE_MAP:
            v = VOICE_MAP[v.lower()]

        if v == DEFAULT_VOICE:
            return v, DEFAULT_RATE, DEFAULT_PITCH
        return v, "+0%", "+0Hz"

    # 2. If a language code or name is given
    if language and language.strip():
        lang_key = language.strip().lower()
        v = VOICE_MAP.get(lang_key, DEFAULT_VOICE)
        if v == DEFAULT_VOICE or lang_key in ("en", "english", "en-us", "en-in"):
            return v, DEFAULT_RATE, DEFAULT_PITCH
        return v, "+0%", "+0Hz"

    # 3. Default fallback: Baymax-inspired English
    return DEFAULT_VOICE, DEFAULT_RATE, DEFAULT_PITCH


def decode_mp3_to_float32(mp3_buffer: io.BytesIO) -> tuple[np.ndarray, int]:
    """
    Decode in-memory MP3 audio bytes to a float32 numpy array.
    Uses soundfile as primary decoder, with fallback handling for environments
    where libsndfile lacks built-in MP3 decoding.
    """
    mp3_buffer.seek(0)
    try:
        audio_float, sr = sf.read(mp3_buffer, dtype="float32", always_2d=False)
        return audio_float, sr
    except Exception as sf_err:
        log.warning(f"[TTS] soundfile MP3 read failed: {sf_err}. Attempting fallback decoders...")
        mp3_buffer.seek(0)
        raw_mp3 = mp3_buffer.read()

        # Fallback 1: miniaudio (lightweight C decoder if installed)
        try:
            import miniaudio
            decoded = miniaudio.mp3_read_f32(raw_mp3)
            samples = np.array(decoded.samples, dtype=np.float32)
            if decoded.nchannels > 1:
                samples = samples.reshape(-1, decoded.nchannels)
            return samples, decoded.sample_rate
        except ImportError:
            pass

        # Fallback 2: pydub / ffmpeg (if installed)
        try:
            from pydub import AudioSegment
            seg = AudioSegment.from_file(io.BytesIO(raw_mp3), format="mp3")
            samples = np.array(seg.get_array_of_samples(), dtype=np.float32) / 32768.0
            if seg.channels > 1:
                samples = samples.reshape(-1, seg.channels)
            return samples, seg.frame_rate
        except ImportError:
            pass

        raise RuntimeError(
            f"Failed to decode MP3 stream. Ensure libsndfile with MP3 support is installed. (Error: {sf_err})"
        )


async def synthesize_chunks(
    text: str,
    voice: str | None = None,
    language: str | None = None,
    rate: str | None = None,
    pitch: str | None = None,
) -> AsyncGenerator[bytes, None]:
    """
    Async generator that yields 16-bit signed little-endian PCM chunks at 16 kHz
    for streaming to the ESP32-S3 I2S speaker.

    Maintains full backward compatibility with calls such as:
      synthesize_chunks(reply)
      synthesize_chunks(reply, voice="...")
    while supporting:
      synthesize_chunks(reply, language="hi")
    """
    if not text or not text.strip():
        return

    resolved_voice, default_rate, default_pitch = resolve_voice(
        language=language,
        voice=voice
    )
    use_rate = rate if rate is not None else default_rate
    use_pitch = pitch if pitch is not None else default_pitch

    # Edge-TTS produces MP3 in memory
    mp3_buffer = io.BytesIO()
    try:
        communicate = edge_tts.Communicate(
            text=text.strip(),
            voice=resolved_voice,
            rate=use_rate,
            pitch=use_pitch,
        )
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_buffer.write(chunk["data"])
    except Exception as e:
        log.error(f"[TTS Error] Edge-TTS synthesis failed with voice '{resolved_voice}': {e}")
        # Safe fallback: if a regional voice failed, try once with the default English voice
        if resolved_voice != DEFAULT_VOICE:
            log.warning(f"[TTS] Retrying synthesis with default fallback voice '{DEFAULT_VOICE}'")
            mp3_buffer = io.BytesIO()
            try:
                fallback_comm = edge_tts.Communicate(
                    text=text.strip(),
                    voice=DEFAULT_VOICE,
                    rate=DEFAULT_RATE,
                    pitch=DEFAULT_PITCH,
                )
                async for chunk in fallback_comm.stream():
                    if chunk["type"] == "audio":
                        mp3_buffer.write(chunk["data"])
            except Exception as fb_err:
                log.error(f"[TTS Error] Fallback synthesis failed: {fb_err}")
                return
        else:
            return

    mp3_buffer.seek(0)
    if mp3_buffer.getbuffer().nbytes == 0:
        log.warning("[TTS Warning] Edge-TTS produced empty audio buffer")
        return

    # Decode MP3 to float32
    try:
        audio_float, original_sr = decode_mp3_to_float32(mp3_buffer)
    except Exception as e:
        log.error(f"[TTS Error] MP3 decoding failed: {e}")
        return

    if audio_float is None or len(audio_float) == 0:
        return

    # Clean any invalid samples (NaN / Inf)
    if not np.isfinite(audio_float).all():
        audio_float = np.nan_to_num(audio_float, nan=0.0, posinf=1.0, neginf=-1.0)

    # 1. Convert multichannel / stereo to mono FIRST
    if audio_float.ndim > 1:
        audio_float = audio_float.mean(axis=1)

    # 2. Resample to 16,000 Hz AFTER mono conversion
    if original_sr != TARGET_RATE:
        if original_sr <= 0:
            log.error(f"[TTS Error] Invalid sample rate: {original_sr}")
            return
        ratio = TARGET_RATE / original_sr
        new_len = int(len(audio_float) * ratio)
        if new_len <= 0:
            return
        indices = np.linspace(0, len(audio_float) - 1, new_len)
        audio_float = np.interp(indices, np.arange(len(audio_float)), audio_float)

    # Convert to signed 16-bit little-endian PCM
    audio_int16 = (audio_float * 32767.0).clip(-32768, 32767).astype("<i2")
    raw_bytes = audio_int16.tobytes()

    # Yield in fixed-size chunks for smooth I2S streaming (2,048 bytes)
    for i in range(0, len(raw_bytes), CHUNK_BYTES):
        yield raw_bytes[i : i + CHUNK_BYTES]
