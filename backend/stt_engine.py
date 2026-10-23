# ============================================================
# stt_engine.py — Multilingual Speech-to-Text using faster-whisper
# ============================================================
import os
import asyncio
import logging
import threading
import numpy as np

log = logging.getLogger(__name__)

# ── Configurable Defaults ─────────────────────────────────────────────────────
DEFAULT_MODEL_SIZE   = os.getenv("WHISPER_MODEL_SIZE", "small")
DEFAULT_DEVICE       = os.getenv("WHISPER_DEVICE", "cpu")
DEFAULT_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

# ── Supported Languages ───────────────────────────────────────────────────────
SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
    "ml": "Malayalam",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "gu": "Gujarati",
    "bn": "Bengali",
    "ur": "Urdu",
}

LANGUAGE_ALIASES: dict[str, str] = {
    "english": "en", "en-us": "en", "en-in": "en", "en-gb": "en",
    "hindi": "hi", "hi-in": "hi",
    "kannada": "kn", "kn-in": "kn",
    "malayalam": "ml", "ml-in": "ml",
    "tamil": "ta", "ta-in": "ta",
    "telugu": "te", "te-in": "te",
    "marathi": "mr", "mr-in": "mr",
    "gujarati": "gu", "gu-in": "gu",
    "bengali": "bn", "bangla": "bn", "bn-in": "bn", "bn-bd": "bn",
    "urdu": "ur", "ur-in": "ur", "ur-pk": "ur",
}

# ── Model Singleton & Concurrency Lock ────────────────────────────────────────
_model = None
_model_lock = threading.Lock()


def normalize_language_code(lang: str | None, confidence: float = 1.0) -> str:
    """
    Normalize Whisper language codes and regional names to a supported 2-letter code.
    Falls back to 'en' if unrecognized or if detection confidence is below 0.35.
    """
    if not lang:
        return "en"

    clean = str(lang).strip().lower()
    code = LANGUAGE_ALIASES.get(clean, clean)

    if code in SUPPORTED_LANGUAGES:
        # Require reasonable confidence for non-English detection
        if code != "en" and confidence < 0.35:
            log.info(f"[STT] Low confidence ({confidence:.2f}) for '{code}', falling back to 'en'")
            return "en"
        return code

    return "en"


class TranscriptionResult(str):
    """
    Transcription string subclass that retains detected language metadata
    while remaining 100% backward-compatible with any code expecting a plain str.
    """
    language: str
    confidence: float
    raw_text: str

    def __new__(cls, text: str, language: str = "en", confidence: float = 0.0):
        s = super().__new__(cls, text)
        s.language = language
        s.confidence = confidence
        s.raw_text = text
        return s

    def __iter__(self):
        # Support tuple unpacking: text, lang, conf = result
        return iter((self.raw_text, self.language, self.confidence))


def load_model(
    model_size: str | None = None,
    device: str | None = None,
    compute_type: str | None = None
):
    """
    Load the faster-whisper model once at startup. Thread-safe singleton.
    """
    global _model
    with _model_lock:
        if _model is not None:
            return _model

        from faster_whisper import WhisperModel

        size = model_size or DEFAULT_MODEL_SIZE
        dev = device or DEFAULT_DEVICE
        ctype = compute_type or DEFAULT_COMPUTE_TYPE

        log.info(f"[STT] Loading Whisper model '{size}' on {dev} with {ctype} quantization...")
        _model = WhisperModel(size, device=dev, compute_type=ctype)
        log.info(f"[STT] Whisper model '{size}' ready")
        return _model


def pcm_to_float32(pcm_bytes: bytes) -> np.ndarray:
    """
    Convert raw 16-bit signed little-endian PCM audio bytes to normalized float32.
    Safe against malformed buffers and non-finite samples.
    """
    if not pcm_bytes:
        return np.array([], dtype=np.float32)

    # 16-bit signed little-endian PCM = 2 bytes per sample
    # Truncate any dangling trailing odd byte
    usable_len = len(pcm_bytes) - (len(pcm_bytes) % 2)
    if usable_len == 0:
        return np.array([], dtype=np.float32)

    audio_np = np.frombuffer(pcm_bytes[:usable_len], dtype="<i2").astype(np.float32) / 32768.0

    if not np.isfinite(audio_np).all():
        audio_np = np.nan_to_num(audio_np, nan=0.0, posinf=1.0, neginf=-1.0)

    return audio_np


def transcribe(
    pcm_bytes: bytes,
    sample_rate: int = 16000,
    channels: int = 1
) -> TranscriptionResult:
    """
    Transcribe raw 16-bit signed mono PCM audio bytes at 16 kHz.
    Runs automatic language detection.
    Returns a TranscriptionResult (inherits from str, with .language and .confidence).
    """
    if _model is None:
        load_model()

    if not pcm_bytes:
        return TranscriptionResult("", "en", 0.0)

    audio_np = pcm_to_float32(pcm_bytes)

    # Discard audio clips shorter than 300ms
    if len(audio_np) < int(sample_rate * 0.3):
        return TranscriptionResult("", "en", 0.0)

    try:
        # Automatic language detection: beam_size=3, vad_filter=True
        segments, info = _model.transcribe(
            audio_np,
            beam_size=3,
            vad_filter=True
        )

        text_parts = [seg.text.strip() for seg in segments if seg.text.strip()]
        full_text = " ".join(text_parts).strip()

        detected_lang = normalize_language_code(
            info.language,
            confidence=getattr(info, "language_probability", 0.0)
        )
        confidence = float(getattr(info, "language_probability", 0.0))

        log.info(f"[STT] Transcribed: '{full_text}' (detected: {info.language} -> {detected_lang}, conf={confidence:.2f})")
        return TranscriptionResult(full_text, detected_lang, confidence)

    except Exception as e:
        log.error(f"[STT Error] Transcription failed: {e}")
        return TranscriptionResult("", "en", 0.0)


async def transcribe_async(
    pcm_bytes: bytes,
    sample_rate: int = 16000,
    channels: int = 1
) -> TranscriptionResult:
    """
    Asynchronous wrapper that offloads CPU-bound Whisper inference to a worker thread
    to avoid blocking FastAPI's event loop.
    """
    return await asyncio.to_thread(transcribe, pcm_bytes, sample_rate, channels)
