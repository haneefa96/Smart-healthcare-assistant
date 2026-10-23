# ============================================================
# llm_agent.py — Healthcare Conversational Agent via OpenAI
#   Compatible with OpenAI API, Google Gemini (openai-compat),
#   or any local Ollama endpoint.
# ============================================================
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# ── System prompt — enforces safe, concise healthcare assistant persona ────────
SYSTEM_PROMPT = """
You are a friendly, empathetic healthcare assistant robot designed to support patients.

Guidelines:
- Keep every response under 40 words (short answers are essential for speech).
- Speak naturally, warmly, and clearly as if talking to an elderly or recovering patient.
- For medical questions: give general wellness information only, never diagnose.
- Always remind users that you are a robot and not a doctor for specific medical advice.
- For emergencies: immediately tell the patient to call emergency services or press the call button.
- Supported topics: medication reminders, hydration prompts, appointment information, general wellness.
- If asked about vitals, you can note that the robot monitors heart rate and SpO₂ for comfort tracking.
""".strip()

_client: AsyncOpenAI | None = None

def load_llm():
    global _client
    api_key  = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model    = os.getenv("LLM_MODEL", "gpt-4o-mini")

    _client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    print(f"[LLM] Client ready — model: {model}, endpoint: {base_url}")

async def generate_response(user_text: str) -> str:
    """
    Send user utterance to the LLM and return the assistant's text response.
    """
    if not user_text:
        return "I didn't catch that. Could you please repeat?"

    if _client is None:
        raise RuntimeError("LLM client not loaded. Call load_llm() first.")

    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    try:
        response = await _client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system",  "content": SYSTEM_PROMPT},
                {"role": "user",    "content": user_text},
            ],
            max_tokens=80,
            temperature=0.6,
        )
        reply = response.choices[0].message.content.strip()
        print(f"[LLM] Response: '{reply}'")
        return reply

    except Exception as e:
        print(f"[LLM] Error: {e}")
        return "I'm having trouble thinking right now. Please try again shortly."
