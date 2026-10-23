# ============================================================
# rag_config.py — RAG Configuration & Environment Variables
# ============================================================
import os
from dotenv import load_dotenv

load_dotenv()

# ── RAG Configuration ──────────────────────────────────────────────────────────
# Embedding model name (must be compatible with sentence-transformers)
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Vector store path (created automatically on first index)
VECTOR_STORE_PATH = os.getenv("RAG_VECTOR_STORE_PATH", "./rag_data/vectorstore")

# Document chunking parameters
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))

# Retrieval parameters
TOP_K = int(os.getenv("RAG_TOP_K", "3"))
RELEVANCE_THRESHOLD = float(os.getenv("RAG_RELEVANCE_THRESHOLD", "0.3"))

# Knowledge base directory (source documents)
KNOWLEDGE_DIR = os.getenv("RAG_KNOWLEDGE_DIR", "./rag_data/knowledge")


def validate():
    """Validate RAG configuration. Returns (bool, error_message)."""
    if not EMBEDDING_MODEL:
        return False, "RAG_EMBEDDING_MODEL is not set"
    if not os.path.exists(KNOWLEDGE_DIR):
        return False, f"RAG_KNOWLEDGE_DIR does not exist: {KNOWLEDGE_DIR}"
    return True, None


def get_env_summary():
    """Return a summary of RAG configuration for logging."""
    return (
        f"Embedding: {EMBEDDING_MODEL}, "
        f"Vector Store: {VECTOR_STORE_PATH}, "
        f"Chunks: {CHUNK_SIZE}+{CHUNK_OVERLAP} chars, "
        f"Top-K: {TOP_K}, "
        f"Threshold: {RELEVANCE_THRESHOLD}, "
        f"Knowledge Dir: {KNOWLEDGE_DIR}"
    )
