import json
import asyncio
import unittest
from unittest.mock import AsyncMock, patch, MagicMock

from stt_engine import TranscriptionResult
from server import process_utterance, health, app


class TestPipelineIntegration(unittest.TestCase):

    @patch("server.synthesize_chunks")
    @patch("server.generate_response")
    @patch("server.transcribe_async")
    def test_complete_multilingual_pipeline_flow(
        self,
        mock_stt,
        mock_llm,
        mock_tts
    ):
        # 1. Setup Mock STT returning Hindi utterance
        mock_stt.return_value = TranscriptionResult(
            text="नमस्ते, मुझे अपनी दवा का समय बताएं",
            language="hi",
            confidence=0.94
        )

        # 2. Setup Mock LLM returning Hindi reply
        mock_llm.return_value = "आपकी दवा का समय दोपहर दो बजे है।"

        # 3. Setup Mock TTS yielding 2048-byte PCM chunks
        async def mock_tts_gen(*args, **kwargs):
            yield b"\x00\x00" * 1024  # 2048 bytes
            yield b"\x10\x00" * 1024  # 2048 bytes
        mock_tts.side_effect = mock_tts_gen

        # 4. Mock WebSocket
        mock_ws = MagicMock()
        mock_ws.client_state.value = 1  # 1 = CONNECTED
        mock_ws.send_text = AsyncMock()
        mock_ws.send_bytes = AsyncMock()

        async def run_pipeline():
            # 1.0 second of dummy PCM input
            dummy_pcm = b"\x00\x00" * 16000
            await process_utterance(mock_ws, dummy_pcm, "test_client_001")

            # Verify STT was called with PCM bytes
            mock_stt.assert_called_once_with(dummy_pcm, sample_rate=16000)

            # Verify Transcript frame was sent to WebSocket with language
            mock_ws.send_text.assert_called_once()
            sent_json = json.loads(mock_ws.send_text.call_args[0][0])
            self.assertEqual(sent_json["transcript"], "नमस्ते, मुझे अपनी दवा का समय बताएं")
            self.assertEqual(sent_json["language"], "hi")
            self.assertEqual(sent_json["confidence"], 0.94)

            # Verify LLM was called with the detected language
            mock_llm.assert_called_once_with(
                "नमस्ते, मुझे अपनी दवा का समय बताएं",
                language="hi"
            )

            # Verify TTS was called with the reply and detected language
            mock_tts.assert_called_once_with(
                "आपकी दवा का समय दोपहर दो बजे है।",
                language="hi"
            )

            # Verify 2 audio PCM chunks were sent back over WebSocket
            self.assertEqual(mock_ws.send_bytes.call_count, 2)
            self.assertEqual(len(mock_ws.send_bytes.call_args_list[0][0][0]), 2048)

        asyncio.run(run_pipeline())

    @patch("server.synthesize_chunks")
    @patch("server.generate_response")
    @patch("server.transcribe_async")
    def test_pipeline_handles_disconnect_gracefully(
        self,
        mock_stt,
        mock_llm,
        mock_tts
    ):
        mock_stt.return_value = TranscriptionResult("Hello", "en", 0.9)
        mock_llm.return_value = "Hello! How can I assist you?"

        # Simulate client disconnecting after first chunk
        async def mock_tts_gen(*args, **kwargs):
            yield b"\x00\x00" * 1024
            yield b"\x00\x00" * 1024
        mock_tts.side_effect = mock_tts_gen

        mock_ws = MagicMock()
        mock_ws.client_state.value = 3  # 3 = DISCONNECTED
        mock_ws.send_text = AsyncMock()
        mock_ws.send_bytes = AsyncMock()

        async def run_disconnect():
            await process_utterance(mock_ws, b"\x00\x00" * 8000, "client_disc")
            # Should not crash and should not send bytes to disconnected client
            mock_ws.send_bytes.assert_not_called()

        asyncio.run(run_disconnect())

    def test_health_check_endpoint(self):
        async def run_health():
            res = await health()
            self.assertEqual(res["status"], "online")
            self.assertIn("faster-whisper", res["pipeline"]["stt"])
            self.assertIn("Google Gemini", res["pipeline"]["llm"])
            self.assertIn("Edge-TTS", res["pipeline"]["tts"])
            self.assertEqual(res["tts_config"]["default_voice"], "en-US-AndrewMultilingualNeural")
            self.assertIn("hi", res["supported_languages"])
            self.assertIn("kn", res["supported_languages"])

        asyncio.run(run_health())


if __name__ == "__main__":
    unittest.main()
