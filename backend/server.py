# ============================================================
# server.py — FastAPI + WebSocket AI Gateway
#   The ESP32-S3 connects here to stream audio, get AI replies
#   and receive synthesized speech back in real time.
#
#   Run: uvicorn server:app --host 0.0.0.0 --port 8765 --reload
# ============================================================
import os
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

try:
    from stt_engine import (
        load_model as load_stt,
        transcribe_async,
        SUPPORTED_LANGUAGES,
        DEFAULT_MODEL_SIZE,
        DEFAULT_DEVICE,
        DEFAULT_COMPUTE_TYPE,
    )
    from llm_agent import load_llm, generate_response, get_llm_config
    from tts_engine import (
        synthesize_chunks,
        DEFAULT_VOICE,
        DEFAULT_RATE,
        DEFAULT_PITCH,
        CHUNK_BYTES,
    )
except ImportError:
    from backend.stt_engine import (
        load_model as load_stt,
        transcribe_async,
        SUPPORTED_LANGUAGES,
        DEFAULT_MODEL_SIZE,
        DEFAULT_DEVICE,
        DEFAULT_COMPUTE_TYPE,
    )
    from backend.llm_agent import load_llm, generate_response, get_llm_config
    from backend.tts_engine import (
        synthesize_chunks,
        DEFAULT_VOICE,
        DEFAULT_RATE,
        DEFAULT_PITCH,
        CHUNK_BYTES,
    )

<<<<<<< HEAD
# ── RAG imports ────────────────────────────────────────────────────────────────
from rag_index import rebuild_index, get_index_stats, is_index_built
from rag_retriever import retrieve_context, format_context
from rag_config import validate, get_env_summary, KNOWLEDGE_DIR

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
=======
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
>>>>>>> upstream/backend
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
    log.info("Loading Multilingual STT model (Whisper)...")
    stt_model_size = os.getenv("WHISPER_MODEL_SIZE", DEFAULT_MODEL_SIZE)
    stt_device = os.getenv("WHISPER_DEVICE", DEFAULT_DEVICE)
    stt_compute = os.getenv("WHISPER_COMPUTE_TYPE", DEFAULT_COMPUTE_TYPE)
    load_stt(model_size=stt_model_size, device=stt_device, compute_type=stt_compute)

    log.info("Loading Conversational LLM client...")
    load_llm()

<<<<<<< HEAD
    # Initialize RAG
    await init_rag()

    if _rag_initialized:
        stats = get_index_stats()
        log.info(f"[RAG] {stats['chunk_count']} chunks indexed")
    else:
        log.warning("[RAG] RAG not initialized — LLM will respond from general knowledge only")

    log.info("✅ AI Gateway ready — waiting for ESP32-S3 connection")
=======
    log.info(f"✅ AI Voice Gateway ready — default voice: {DEFAULT_VOICE} ({DEFAULT_RATE})")
>>>>>>> upstream/backend
    yield
    log.info("Shutting down AI Gateway")

app = FastAPI(title="Healthcare Robot AI Gateway", lifespan=lifespan)

# ── Active connections registry ────────────────────────────────────────────────
active_connections: dict[str, WebSocket] = {}

# ── Audio Constants ───────────────────────────────────────────────────────────
SAMPLE_RATE      = 16000
SILENCE_THRESH_S = 0.8      # seconds of silence to trigger STT
BYTES_PER_SAMPLE = 2        # 16-bit = 2 bytes
SILENCE_BYTES    = int(SILENCE_THRESH_S * SAMPLE_RATE * BYTES_PER_SAMPLE)
MAX_BUFFER_BYTES = SAMPLE_RATE * BYTES_PER_SAMPLE * 30  # 30s max utterance


@app.websocket("/ws/audio")
async def audio_ws(ws: WebSocket):
    """
    WebSocket endpoint for ESP32-S3 full-duplex audio stream.
    Receives raw 16-bit 16 kHz PCM chunks, detects silence,
    executes STT -> Gemini -> Edge-TTS, and streams PCM chunks back.
    """
    await ws.accept()
    client_id = str(ws.client)
    active_connections[client_id] = ws
    log.info(f"[{client_id}] ESP32-S3 connected")

    audio_buffer = bytearray()
    last_nonsilent_byte_count = 0

    try:
        while True:
            # Receive frame (handles binary PCM chunks and text frames)
            message = await asyncio.wait_for(ws.receive(), timeout=10.0)

            if message["type"] == "websocket.disconnect":
                break

            # Handle text frame (e.g. ping or query from web/test client)
            if "text" in message and message["text"]:
                raw_text = message["text"].strip()
                if raw_text == "ping":
                    await ws.send_text(json.dumps({"pong": True}))
                    continue
                try:
                    payload = json.loads(raw_text)
                    if "query" in payload:
                        q_text = payload["query"]
                        q_lang = payload.get("language", "en")
                        reply = await generate_response(q_text, language=q_lang)
                        await ws.send_text(json.dumps({
                            "transcript": q_text,
                            "reply": reply,
                            "language": q_lang
                        }))
                except Exception as parse_err:
                    log.debug(f"[{client_id}] Non-JSON text message: {raw_text[:50]}")
                continue

            # Handle binary PCM chunk from microphone
            data = message.get("bytes")
            if not data:
                continue

            audio_buffer.extend(data)

            # Energy-based silence detection
            import numpy as np
            usable_bytes = len(data) - (len(data) % 2)
            if usable_bytes > 0:
                chunk_np = np.frombuffer(data[:usable_bytes], dtype="<i2").astype(np.float32)
                energy = float(np.sqrt(np.mean(chunk_np ** 2)))
            else:
                energy = 0.0

            if energy > 500:  # Active speech detected
                last_nonsilent_byte_count = len(audio_buffer)

            silence_bytes = len(audio_buffer) - last_nonsilent_byte_count

            # Trigger pipeline when silence is detected after speech
            if silence_bytes >= SILENCE_BYTES and last_nonsilent_byte_count > 0:
                utterance = bytes(audio_buffer[:last_nonsilent_byte_count])
                # Clear buffer immediately so subsequent audio isn't corrupted
                audio_buffer.clear()
                last_nonsilent_byte_count = 0

                log.info(f"[{client_id}] Utterance captured ({len(utterance)} bytes) — processing...")
                await process_utterance(ws, utterance, client_id)

            elif len(audio_buffer) > MAX_BUFFER_BYTES:
                log.warning(f"[{client_id}] Buffer overflow (>30s) — flushing")
                audio_buffer.clear()
                last_nonsilent_byte_count = 0

    except WebSocketDisconnect:
        log.info(f"[{client_id}] Disconnected")
    except asyncio.TimeoutError:
        log.warning(f"[{client_id}] Timeout — no audio received for 10s")
    except Exception as e:
        log.error(f"[{client_id}] WebSocket error: {e}")
    finally:
        active_connections.pop(client_id, None)
        try:
            await ws.close()
        except Exception:
            pass


async def process_utterance(ws: WebSocket, pcm_bytes: bytes, client_id: str):
    """
    Multilingual STT → Gemini → Edge-TTS pipeline for one user utterance.
    Streams synthesized 16-bit 16 kHz PCM chunks back to ESP32-S3 in real time.
    """
    # 1. Speech-to-Text (runs in thread pool to keep event loop responsive)
    try:
        transcription = await transcribe_async(pcm_bytes, sample_rate=SAMPLE_RATE)
        text = str(transcription)
        detected_lang = getattr(transcription, "language", "en")
        confidence = getattr(transcription, "confidence", 0.0)
    except Exception as e:
        log.error(f"[{client_id}] STT error: {e}")
        text = ""
        detected_lang = "en"
        confidence = 0.0

    if not text:
        log.info(f"[{client_id}] Empty transcription — skipping utterance")
        return

    log.info(f"[{client_id}] Transcribed ({detected_lang}, conf={confidence:.2f}): '{text}'")

    # Send transcript & language to ESP32 / dashboard
    try:
<<<<<<< HEAD
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
=======
        await ws.send_text(json.dumps({
            "transcript": text,
            "language": detected_lang,
            "confidence": round(confidence, 2)
        }))
    except Exception as send_err:
        log.warning(f"[{client_id}] Failed to send transcript frame: {send_err}")

    # 2. LLM Response Generation (Gemini) in the patient's detected language
    try:
        reply = await generate_response(text, language=detected_lang)
>>>>>>> upstream/backend
    except Exception as e:
        log.error(f"[{client_id}] LLM error: {e}")
        reply = "I'm sorry, I couldn't process that. Please try again."

    llm_source = getattr(reply, "source", "unknown")
    llm_latency_ms = getattr(reply, "latency_s", 0.0) * 1000.0
    log.info(
        f"[{client_id}] LLM reply ({detected_lang}) in {llm_latency_ms:.1f}ms "
        f"[source={llm_source}]: '{reply}'"
    )

    # 3. Text-to-Speech (Edge-TTS) — stream PCM chunks back to ESP32 speaker
    try:
        chunk_count = 0
        async for pcm_chunk in synthesize_chunks(reply, language=detected_lang):
            if ws.client_state.value != 1:  # Client disconnected
                log.warning(f"[{client_id}] Client disconnected during TTS streaming")
                break
            await ws.send_bytes(pcm_chunk)
            chunk_count += 1
            await asyncio.sleep(0)  # Yield to event loop for smooth network streaming

        log.info(f"[{client_id}] Sent {chunk_count} PCM chunks ({detected_lang}) to robot")
    except Exception as e:
        log.error(f"[{client_id}] TTS streaming error: {e}")


# ── Direct HTTP Chat API (Enables testing without microphone) ─────────────────
class ChatRequest(BaseModel):
    text: str
    language: str | None = None

class ChatResponse(BaseModel):
    query: str
    reply: str
    language: str
    source: str | None = None
    llm_latency_ms: float | None = None
    total_latency_ms: float | None = None


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest):
    """
    Direct text chat endpoint with high-precision latency profiling.
    """
    import time
    t0 = time.perf_counter()

    lang = req.language or "en"
    reply = await generate_response(req.text, language=lang)

    total_latency_ms = (time.perf_counter() - t0) * 1000.0
    llm_latency_ms = getattr(reply, "latency_s", 0.0) * 1000.0
    source = getattr(reply, "source", "gemini")
    error_cat = getattr(reply, "error_category", None)
    status_code = getattr(reply, "status_code", None)

    # Diagnostic log without exposing patient text
    error_info = f" | Error: {error_cat} (HTTP {status_code})" if error_cat else ""
    log.info(
        f"[/api/chat] Total: {total_latency_ms:.1f}ms | LLM: {llm_latency_ms:.1f}ms | "
        f"Source: {source} | Lang: {lang}{error_info}"
    )

    return ChatResponse(
        query=req.text,
        reply=str(reply),
        language=lang,
        source=source,
        llm_latency_ms=round(llm_latency_ms, 1),
        total_latency_ms=round(total_latency_ms, 1)
    )


# ── HTTP Health Check ─────────────────────────────────────────────────────────
@app.get("/health")
async def health():
<<<<<<< HEAD
    status = {
        "status": "online",
        "connections": len(active_connections),
        "pipeline": "STT → [RAG] → LLM → TTS",
        "rag_enabled": _rag_initialized,
=======
    _, llm_model, _ = get_llm_config()
    stt_model_size = os.getenv("WHISPER_MODEL_SIZE", DEFAULT_MODEL_SIZE)
    return {
        "status": "online",
        "connections": len(active_connections),
        "pipeline": {
            "stt": f"faster-whisper ({stt_model_size})",
            "llm": f"Google Gemini ({llm_model})",
            "tts": f"Edge-TTS ({DEFAULT_VOICE})",
        },
        "tts_config": {
            "default_voice": DEFAULT_VOICE,
            "rate": DEFAULT_RATE,
            "pitch": DEFAULT_PITCH,
            "sample_rate": SAMPLE_RATE,
            "chunk_bytes": CHUNK_BYTES,
        },
        "supported_languages": list(SUPPORTED_LANGUAGES.keys())
>>>>>>> upstream/backend
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


# ── Serve Frontend Web App ────────────────────────────────────────────────────
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
