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

# ── RAG imports ────────────────────────────────────────────────────────────────
from rag_index import rebuild_index, get_index_stats, is_index_built
from rag_retriever import retrieve_context, format_context
from rag_config import validate, get_env_summary, KNOWLEDGE_DIR

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── RAG state ──────────────────────────────────────────────────────────────────
_rag_initialized: bool = False
_rag_error: str | None = None


async def init_rag():
    """Initialize RAG subsystem at startup."""
    global _rag_initialized, _rag_error

    log.info("[RAG] Initializing RAG subsystem...")

    # Validate configuration
    valid, error = validate()
    if not valid:
        _rag_error = f"RAG validation failed: {error}"
        log.warning(f"[RAG] {_rag_error}")
        return False

    log.info(f"[RAG] Config: {get_env_summary()}")

    # Check if knowledge directory has documents
    import os
    doc_count = sum(1 for _ in os.listdir(KNOWLEDGE_DIR) if _.endswith(('.pdf', '.txt', '.md')))
    if doc_count == 0:
        log.warning(f"[RAG] No documents found in {KNOWLEDGE_DIR}. RAG will return empty results.")
        log.warning("[RAG] Add PDF/text documents to enable enhanced responses.")

    # Build or load vector store
    try:
        # Only rebuild if index is empty (first run)
        if not is_index_built():
            log.info("[RAG] Vector store empty — building index...")
            success = rebuild_index()
            if not success:
                log.error("[RAG] Failed to build vector store")
                _rag_error = "Failed to build vector store"
                return False
        else:
            log.info("[RAG] Loading existing vector store")

        _rag_initialized = True
        log.info("[RAG] ✅ Vector store ready")
        return True

    except Exception as e:
        _rag_error = f"RAG initialization error: {e}"
        log.error(f"[RAG] {_rag_error}")
        return False


# ── Startup / Shutdown lifespan ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Loading STT model (Whisper)...")
    load_stt(model_size="base.en", device="cpu")
    log.info("Loading LLM client...")
    load_llm()

    # Initialize RAG
    await init_rag()

    if _rag_initialized:
        stats = get_index_stats()
        log.info(f"[RAG] {stats['chunk_count']} chunks indexed")
    else:
        log.warning("[RAG] RAG not initialized — LLM will respond from general knowledge only")

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

    # 2. RAG Context Retrieval (optional, enabled if configured)
    context = None
    sources = []

    if _rag_initialized:
        try:
            chunks = retrieve_context(text)
            if chunks:
                context = format_context(chunks)
                sources = [meta.get("source", "unknown") for _, meta, _ in chunks]
                log.info(f"[{client_id}] Retrieved {len(chunks)} relevant chunks")
            else:
                log.info(f"[{client_id}] No relevant context found — using general knowledge")
        except Exception as e:
            log.warning(f"[{client_id}] RAG retrieval error: {e}")
            log.info(f"[{client_id}] Falling back to general knowledge")

    # 3. LLM Response Generation
    try:
        reply, llm_sources = await generate_response(text, context=context)
        # Merge sources from RAG and LLM
        all_sources = sources + llm_sources
        if all_sources:
            log.info(f"[{client_id}] Sources: {all_sources}")
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
    status = {
        "status": "online",
        "connections": len(active_connections),
        "pipeline": "STT → [RAG] → LLM → TTS",
        "rag_enabled": _rag_initialized,
    }
    if _rag_error:
        status["rag_error"] = _rag_error
    if _rag_initialized:
        status["rag_stats"] = get_index_stats()
    return status


# ── RAG admin endpoints ────────────────────────────────────────────────────────
@app.post("/rag/rebuild")
async def rag_rebuild():
    """Force rebuild the RAG vector store."""
    if not _rag_initialized:
        return {"error": "RAG not initialized", "rag_error": _rag_error}

    try:
        rebuild_index()
        return {"status": "success", "message": "Vector store rebuilt"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/rag/stats")
async def rag_stats():
    """Return RAG vector store statistics."""
    if not _rag_initialized:
        return {"error": "RAG not initialized", "rag_error": _rag_error}
    return get_index_stats()

# ── Serve Frontend Web App ───────────────────────────────────────────────────
import os
from fastapi.staticfiles import StaticFiles
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

