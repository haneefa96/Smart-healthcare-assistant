import io
import asyncio
import unittest
import numpy as np
from unittest.mock import patch, MagicMock

from tts_engine import (
    DEFAULT_VOICE,
    DEFAULT_RATE,
    DEFAULT_PITCH,
    TARGET_RATE,
    CHUNK_BYTES,
    VOICE_MAP,
    resolve_voice,
    get_supported_voices,
    synthesize_chunks,
)


class TestTTSEngine(unittest.TestCase):

    def test_baymax_default_voice_and_pacing(self):
        self.assertEqual(DEFAULT_VOICE, "en-US-AndrewMultilingualNeural")
        self.assertEqual(DEFAULT_RATE, "-12%")
        self.assertEqual(DEFAULT_PITCH, "-5Hz")
        self.assertEqual(TARGET_RATE, 16000)
        self.assertEqual(CHUNK_BYTES, 2048)

    def test_voice_resolution_defaults(self):
        v, r, p = resolve_voice()
        self.assertEqual(v, "en-US-AndrewMultilingualNeural")
        self.assertEqual(r, "-12%")
        self.assertEqual(p, "-5Hz")

    def test_voice_resolution_indian_languages(self):
        expected_voices = {
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
        for lang, expected in expected_voices.items():
            voice_id, _, _ = resolve_voice(language=lang)
            self.assertEqual(voice_id, expected, f"Failed for language: {lang}")

    def test_voice_resolution_override(self):
        # Explicit voice name should be respected
        v, r, p = resolve_voice(voice="custom-voice-name")
        self.assertEqual(v, "custom-voice-name")
        self.assertEqual(r, "+0%")
        self.assertEqual(p, "+0Hz")

    def test_synthesize_chunks_empty_text(self):
        async def run():
            chunks = []
            async for chunk in synthesize_chunks(""):
                chunks.append(chunk)
            self.assertEqual(len(chunks), 0)

            async for chunk in synthesize_chunks("   "):
                chunks.append(chunk)
            self.assertEqual(len(chunks), 0)

        asyncio.run(run())

    @patch("tts_engine.decode_mp3_to_float32")
    @patch("edge_tts.Communicate")
    def test_synthesize_chunks_pcm_format_and_chunk_size(self, mock_comm_cls, mock_decode):
        # Mock communicate.stream to yield mock audio chunks
        mock_comm = MagicMock()
        async def mock_stream():
            yield {"type": "audio", "data": b"fake_mp3_bytes_1234"}
        mock_comm.stream = mock_stream
        mock_comm_cls.return_value = mock_comm

        # Mock decode to return 1.0 second of stereo float32 audio at 44100 Hz
        sample_count = 44100
        stereo_audio = np.ones((sample_count, 2), dtype=np.float32) * 0.5
        mock_decode.return_value = (stereo_audio, 44100)

        async def run():
            chunks = []
            # Call with backward-compatible single argument
            async for chunk in synthesize_chunks("Take your medicine, please."):
                chunks.append(chunk)

            # All full chunks must be exactly CHUNK_BYTES (2048 bytes)
            for c in chunks[:-1]:
                self.assertEqual(len(c), 2048)

            total_bytes = sum(len(c) for c in chunks)
            # 1.0s @ 16kHz * 2 bytes/sample = 32000 bytes
            self.assertAlmostEqual(total_bytes, 32000, delta=100)

            # Check that samples are 16-bit little endian (<i2)
            first_chunk = chunks[0]
            samples = np.frombuffer(first_chunk, dtype="<i2")
            # 0.5 * 32767 = 16383
            self.assertTrue(16000 < samples[0] < 16500)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
