# ============================================================
# stt_engine.py — Speech-to-Text using faster-whisper
# ============================================================
import io
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

# Load model once at startup (use "base.en" for speed, "small" for accuracy)
_model: WhisperModel | None = None

def load_model(model_size: str = "base.en", device: str = "cpu"):
    global _model
    print(f"[STT] Loading Whisper model: {model_size} on {device}")
    _model = WhisperModel(model_size, device=device, compute_type="int8")
    print("[STT] Model ready")

def transcribe(pcm_bytes: bytes,
               sample_rate: int = 16000,
               channels: int = 1) -> str:
    """
    Transcribe raw 16-bit signed PCM audio bytes to text.
    Returns empty string if audio is too short or no speech detected.
    """
    if _model is None:
        raise RuntimeError("STT model not loaded. Call load_model() first.")

    # Convert raw PCM bytes → float32 numpy array
    audio_np = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    if len(audio_np) < sample_rate * 0.3:  # Discard clips < 300ms
        return ""

    # faster-whisper expects float32 array at 16 kHz mono
    segments, info = _model.transcribe(audio_np, beam_size=3,
                                       language="en", vad_filter=True)
    text = " ".join(seg.text.strip() for seg in segments)
    print(f"[STT] Transcribed: '{text}' (detected lang: {info.language})")
    return text.strip()
