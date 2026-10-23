# ============================================================
# server.py — FastAPI + WebSocket AI Gateway
#   The ESP32-S3 connects here to stream audio, get AI replies
#   and receive synthesized speech back in real time.
#
#   Run: uvicorn server:app --host 0.0.0.0 --port 8765 --reload
# ============================================================
import asyncio
import io
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from stt_engine  import load_model as load_stt, transcribe
from llm_agent   import load_llm, generate_response
from tts_engine  import synthesize_chunks

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Startup / Shutdown lifespan ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Loading STT model (Whisper)...")
    load_stt(model_size="base.en", device="cpu")
    log.info("Loading LLM client...")
    load_llm()
    log.info("✅ AI Gateway ready — waiting for ESP32-S3 connection")
    yield
    log.info("Shutting down AI Gateway")

app = FastAPI(title="Healthcare Robot AI Gateway", lifespan=lifespan)

# ── Active connections registry ────────────────────────────────────────────────
active_connections: dict[str, WebSocket] = {}

# ── Constants ─────────────────────────────────────────────────────────────────
SAMPLE_RATE      = 16000
SILENCE_THRESH_S = 0.8      # seconds of silence to trigger STT
BYTES_PER_SAMPLE = 2        # 16-bit = 2 bytes
SILENCE_BYTES    = int(SILENCE_THRESH_S * SAMPLE_RATE * BYTES_PER_SAMPLE)
MAX_BUFFER_BYTES = SAMPLE_RATE * BYTES_PER_SAMPLE * 30  # 30s max utterance

@app.websocket("/ws/audio")
async def audio_ws(ws: WebSocket):
    await ws.accept()
    client_id = str(ws.client)
    active_connections[client_id] = ws
    log.info(f"[{client_id}] ESP32-S3 connected")

    audio_buffer = bytearray()
    last_nonsilent_byte_count = 0

    try:
        while True:
            # Receive binary PCM chunk from ESP32
            data = await asyncio.wait_for(ws.receive_bytes(), timeout=10.0)

            if not data:
                continue

            audio_buffer.extend(data)

            # ── Simple energy-based silence detection
            import numpy as np
            chunk_np = np.frombuffer(data, dtype=np.int16).astype(np.float32)
            energy   = float(np.sqrt(np.mean(chunk_np ** 2)))

            if energy > 500:  # Threshold — tune based on mic gain
                last_nonsilent_byte_count = len(audio_buffer)

            silence_bytes = len(audio_buffer) - last_nonsilent_byte_count

            # ── Trigger pipeline when silence detected or buffer is full
            if silence_bytes >= SILENCE_BYTES and last_nonsilent_byte_count > 0:
                utterance = bytes(audio_buffer[:last_nonsilent_byte_count])
                audio_buffer.clear()
                last_nonsilent_byte_count = 0

                log.info(f"[{client_id}] Utterance captured ({len(utterance)} bytes) — processing...")
                await process_utterance(ws, utterance, client_id)

            elif len(audio_buffer) > MAX_BUFFER_BYTES:
                log.warning(f"[{client_id}] Buffer overflow — flushing")
                audio_buffer.clear()
                last_nonsilent_byte_count = 0

    except WebSocketDisconnect:
        log.info(f"[{client_id}] Disconnected")
    except asyncio.TimeoutError:
        log.warning(f"[{client_id}] Timeout — no audio received for 10s")
    except Exception as e:
        log.error(f"[{client_id}] Error: {e}")
    finally:
        active_connections.pop(client_id, None)
        await ws.close()

async def process_utterance(ws: WebSocket, pcm_bytes: bytes, client_id: str):
    """
    Full STT → LLM → TTS pipeline for one user utterance.
    Streams synthesized audio back to the ESP32-S3 in real time.
    """
    # 1. Speech-to-Text
    try:
        text = transcribe(pcm_bytes, sample_rate=SAMPLE_RATE)
    except Exception as e:
        log.error(f"[STT Error] {e}")
        text = ""

    if not text:
        log.info(f"[{client_id}] Empty transcription — skipping")
        return

    log.info(f"[{client_id}] Transcribed: '{text}'")

    # Send transcript back to ESP32 so dashboard can show it
    try:
        import json as _json
        await ws.send_text(_json.dumps({"transcript": text}))
    except Exception:
        pass

    # 2. LLM Response Generation

    try:
        reply = await generate_response(text)
    except Exception as e:
        log.error(f"[LLM Error] {e}")
        reply = "I'm sorry, I couldn't process that. Please try again."

    log.info(f"[{client_id}] LLM reply: '{reply}'")

    # 3. Text-to-Speech — stream PCM chunks directly back to ESP32
    try:
        chunk_count = 0
        async for pcm_chunk in synthesize_chunks(reply):
            if ws.client_state.value != 1:  # 1 = CONNECTED
                break
            await ws.send_bytes(pcm_chunk)
            chunk_count += 1
            await asyncio.sleep(0)  # Yield to event loop for smooth streaming

        log.info(f"[{client_id}] Sent {chunk_count} audio chunks to robot")
    except Exception as e:
        log.error(f"[TTS Error] {e}")

# ── HTTP health check ──────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "online",
        "connections": len(active_connections),
        "pipeline": "Whisper → LLM → edge-tts"
    }

# ── Serve Frontend Web App ───────────────────────────────────────────────────
import os
from fastapi.staticfiles import StaticFiles
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

