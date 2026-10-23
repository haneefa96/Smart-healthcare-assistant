import unittest
import numpy as np
from unittest.mock import MagicMock, patch

from stt_engine import (
    pcm_to_float32,
    normalize_language_code,
    TranscriptionResult,
    transcribe,
    SUPPORTED_LANGUAGES,
)


class TestSTTEngine(unittest.TestCase):

    def test_pcm_to_float32_little_endian_conversion(self):
        # 0x0000 -> 0.0, 0x7FFF (32767) -> ~1.0, 0x8000 (-32768) -> -1.0
        # In little-endian bytes:
        # 0 -> b"\x00\x00"
        # 32767 -> b"\xff\x7f"
        # -32768 -> b"\x00\x80"
        pcm_bytes = b"\x00\x00\xff\x7f\x00\x80"
        arr = pcm_to_float32(pcm_bytes)
        self.assertEqual(len(arr), 3)
        self.assertAlmostEqual(arr[0], 0.0, places=4)
        self.assertAlmostEqual(arr[1], 32767.0 / 32768.0, places=4)
        self.assertAlmostEqual(arr[2], -1.0, places=4)

    def test_pcm_to_float32_handles_odd_bytes(self):
        # Dangling byte should be safely truncated, not crash
        pcm_bytes = b"\x00\x00\xff\x7f\xaa"
        arr = pcm_to_float32(pcm_bytes)
        self.assertEqual(len(arr), 2)

    def test_pcm_empty_and_zero(self):
        self.assertEqual(len(pcm_to_float32(b"")), 0)
        self.assertEqual(len(pcm_to_float32(None)), 0)

    def test_language_code_normalization(self):
        # Canonical codes
        for code in SUPPORTED_LANGUAGES:
            self.assertEqual(normalize_language_code(code), code)

        # Aliases
        self.assertEqual(normalize_language_code("hindi"), "hi")
        self.assertEqual(normalize_language_code("kannada"), "kn")
        self.assertEqual(normalize_language_code("english"), "en")
        self.assertEqual(normalize_language_code("en-us"), "en")
        self.assertEqual(normalize_language_code("ta-in"), "ta")

        # Unknown language should fall back to English
        self.assertEqual(normalize_language_code("xyz"), "en")
        self.assertEqual(normalize_language_code(None), "en")

        # Low confidence fallback for non-English
        self.assertEqual(normalize_language_code("hi", confidence=0.20), "en")
        self.assertEqual(normalize_language_code("hi", confidence=0.85), "hi")

    def test_transcription_result_backward_compatibility(self):
        res = TranscriptionResult("Hello HealthBot", "en", 0.95)
        # Inherits from str
        self.assertTrue(isinstance(res, str))
        self.assertEqual(res, "Hello HealthBot")
        self.assertTrue(bool(res))
        self.assertEqual(res.language, "en")
        self.assertEqual(res.confidence, 0.95)

        # Empty result
        empty = TranscriptionResult("", "en", 0.0)
        self.assertFalse(bool(empty))
        self.assertEqual(empty, "")

        # Unpacking support
        text, lang, conf = res
        self.assertEqual(text, "Hello HealthBot")
        self.assertEqual(lang, "en")
        self.assertEqual(conf, 0.95)

    @patch("stt_engine._model")
    def test_transcribe_short_audio_discarded(self, mock_model):
        # 16000 samples/sec * 0.2s * 2 bytes = 6400 bytes (< 300ms)
        short_bytes = b"\x00\x00" * 3200
        res = transcribe(short_bytes, sample_rate=16000)
        self.assertEqual(res, "")
        self.assertEqual(res.language, "en")
        mock_model.transcribe.assert_not_called()

    @patch("stt_engine._model")
    def test_transcribe_multilingual_mocked(self, mock_model):
        segment = MagicMock()
        segment.text = "नमस्ते, मुझे सिरदर्द है"

        info = MagicMock()
        info.language = "hi"
        info.language_probability = 0.92

        mock_model.transcribe.return_value = ([segment], info)

        # 0.5s of audio @ 16kHz 16-bit mono = 16000 bytes
        audio_bytes = b"\x00\x00" * 8000
        res = transcribe(audio_bytes, sample_rate=16000)

        self.assertEqual(res, "नमस्ते, मुझे सिरदर्द है")
        self.assertEqual(res.language, "hi")
        self.assertAlmostEqual(res.confidence, 0.92, places=2)


if __name__ == "__main__":
    unittest.main()
