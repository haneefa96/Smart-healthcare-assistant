# ============================================================
# rag_embeddings.py — Embedding Generation Using Local Model
# ============================================================
import logging
from typing import List

import torch
from sentence_transformers import SentenceTransformer

from rag_config import EMBEDDING_MODEL

logger = logging.getLogger(__name__)

# Global model instance (loaded once)
_model: SentenceTransformer | None = None
_device: str = "cuda" if torch.cuda.is_available() else "cpu"


def load_model():
    """Load the embedding model once at startup. Returns model instance."""
    global _model

    if _model is not None:
        return _model

    logger.info(f"[RAG] Loading embedding model: {EMBEDDING_MODEL} on {_device}")
    _model = SentenceTransformer(EMBEDDING_MODEL, device=_device)
    logger.info(f"[RAG] Embedding model ready — {EMBEDDING_MODEL}")
    return _model


def get_dimension() -> int:
    """Return the embedding dimension for the configured model."""
    model = load_model()
    return model.get_sentence_embedding_dimension()


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of text strings.
    Returns list of embedding vectors (lists of floats).
    """
    if not texts:
        return []

    model = load_model()

    try:
        embeddings = model.encode(texts, convert_to_tensor=False, show_progress_bar=False)
        # Convert numpy arrays to Python lists
        return [emb.tolist() for emb in embeddings]
    except Exception as e:
        logger.error(f"[RAG] Failed to generate embeddings: {e}")
        raise


def embed_text(text: str) -> List[float]:
    """Generate embedding for a single text string."""
    return embed_texts([text])[0]
