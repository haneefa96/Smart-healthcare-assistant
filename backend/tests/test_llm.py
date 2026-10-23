import os
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from openai import APITimeoutError

from llm_agent import (
    check_is_emergency,
    get_llm_config,
    generate_response,
    EMERGENCY_RESPONSES,
    FALLBACK_RESPONSES,
    LANGUAGE_NAMES,
    DEFAULT_MODEL,
    LLMResponse,
)


class TestLLMAgent(unittest.IsolatedAsyncioTestCase):

    def test_emergency_detection_english(self):
        self.assertTrue(check_is_emergency("I have severe chest pain"))
        self.assertTrue(check_is_emergency("Help, I can't breathe"))
        self.assertTrue(check_is_emergency("I think I'm having a heart attack"))
        self.assertFalse(check_is_emergency("What time should I take my vitamins?"))
        self.assertFalse(check_is_emergency("Can I drink some warm water?"))

    def test_emergency_detection_indian_languages(self):
        self.assertTrue(check_is_emergency("सीने में दर्द हो रहा है"))
        self.assertTrue(check_is_emergency("ಎದೆ ನೋವು ಹೆಚ್ಚಾಗಿದೆ"))
        self.assertTrue(check_is_emergency("நெஞ்சு வலி மிக அதிகமாக உள்ளது"))
        self.assertTrue(check_is_emergency("గుండె నొప్పి వస్తోంది"))

    @patch("llm_agent._client")
    async def test_deterministic_emergency_override_no_llm_call(self, mock_client):
        # Emergency queries should NEVER call the LLM — deterministic safety rule
        reply = await generate_response("I have sharp chest pain", language="en")
        self.assertEqual(reply, EMERGENCY_RESPONSES["en"])
        self.assertEqual(reply.source, "emergency_override")
        mock_client.chat.completions.create.assert_not_called()

        reply_hi = await generate_response("सीने में दर्द", language="hi")
        self.assertEqual(reply_hi, EMERGENCY_RESPONSES["hi"])
        self.assertEqual(reply_hi.source, "emergency_override")
        mock_client.chat.completions.create.assert_not_called()

    def test_llm_config_defaults(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-123"}, clear=True):
            api_key, model, base_url = get_llm_config()
            self.assertEqual(api_key, "test-key-123")
            self.assertEqual(model, "gemini-3.5-flash-lite")
            self.assertEqual(base_url, "https://generativelanguage.googleapis.com/v1beta/openai/")

    def test_llm_config_custom_override(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-123", "GEMINI_LLM_MODEL": "custom-model"}, clear=True):
            api_key, model, base_url = get_llm_config()
            self.assertEqual(model, "custom-model")

    def test_llm_config_fallback_to_openai_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fallback-key"}, clear=True):
            api_key, model, base_url = get_llm_config()
            self.assertEqual(api_key, "sk-fallback-key")
            self.assertEqual(model, "gemini-3.5-flash-lite")

    @patch("llm_agent._client")
    async def test_generate_response_multilingual_mocked(self, mock_client):
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(content="आप समय पर पानी पीते रहें और आराम करें।"),
                finish_reason="stop"
            )
        ]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy-test-key"}):
            reply = await generate_response("मुझे क्या करना चाहिए?", language="hi")
            self.assertEqual(reply, "आप समय पर पानी पीते रहें और आराम करें।")
            self.assertEqual(reply.source, "gemini")
            self.assertEqual(reply.finish_reason, "stop")

        call_args = mock_client.chat.completions.create.call_args[1]
        system_msg = call_args["messages"][0]["content"]
        self.assertIn("Hindi", system_msg)
        self.assertIn("40 words", system_msg)
        self.assertEqual(call_args["reasoning_effort"], "low")

    @patch("llm_agent._client")
    async def test_generate_response_timeout_handling(self, mock_client):
        # Simulate a 20-second API timeout
        mock_client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError("Request timed out.")
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy-test-key"}):
            reply = await generate_response("How is my heart rate?", language="en")
            self.assertEqual(reply, FALLBACK_RESPONSES["en"])
            self.assertEqual(reply.source, "fallback")
            self.assertEqual(reply.error_category, "timeout")

    @patch("llm_agent._client")
    async def test_generate_response_handles_api_failure(self, mock_client):
        mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("Quota exceeded"))

        with patch.dict(os.environ, {"GEMINI_API_KEY": "dummy-test-key"}):
            reply_en = await generate_response("How is my blood pressure?", language="en")
            self.assertEqual(reply_en, FALLBACK_RESPONSES["en"])
            self.assertEqual(reply_en.source, "fallback")

            reply_kn = await generate_response("ನನ್ನ ರಕ್ತದೊತ್ತಡ ಹೇಗಿದೆ?", language="kn")
            self.assertEqual(reply_kn, FALLBACK_RESPONSES["kn"])
            self.assertEqual(reply_kn.source, "fallback")


if __name__ == "__main__":
    unittest.main()
