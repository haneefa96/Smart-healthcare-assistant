# ============================================================
# rag_retriever.py — Query Embedding and Similarity Search
# ============================================================
import logging
from typing import List, Tuple, Dict

from rag_config import TOP_K, RELEVANCE_THRESHOLD
from rag_embeddings import embed_text
from rag_index import get_collection

logger = logging.getLogger(__name__)


def retrieve_context(query: str, top_k: int = TOP_K, threshold: float = RELEVANCE_THRESHOLD) -> List[Tuple[str, Dict, float]]:
    """
    Retrieve the most relevant chunks for a given query.
    Returns list of (text, metadata, score) tuples, filtered by relevance threshold.
    """
    if not query.strip():
        logger.warning("[RAG] Empty query — returning empty results")
        return []

    # Generate query embedding
    query_embedding = embed_text(query)

    # Search vector store
    collection = get_collection()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    # Extract results
    chunks = results.get("documents", [[]])[0]  # First batch of results
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    # Convert distances (0-1 cosine distance) to similarity scores (1-distance)
    # Filter by threshold
    retrieved = []
    for i, (chunk, meta, dist) in enumerate(zip(chunks, metadatas, distances)):
        score = 1.0 - dist  # Convert distance to similarity

        if score < threshold:
            logger.debug(f"[RAG] Chunk {i} below threshold: score={score:.3f} < {threshold}")
            continue

        retrieved.append((chunk, meta, score))
        logger.info(f"[RAG] Retrieved chunk {i}: {meta.get('source', 'unknown')} "
                   f"(score={score:.3f})")

    return retrieved


def format_context(chunks: List[Tuple[str, Dict, float]]) -> str:
    """Format retrieved chunks into a single context string for the LLM."""
    if not chunks:
        return ""

    context_parts = []
    for i, (text, metadata, score) in enumerate(chunks, 1):
        source = metadata.get("source", "unknown")
        page = metadata.get("page", "")
        page_info = f" (page {page})" if page else ""

        context_parts.append(
            f"[Source {i}: {source}{page_info}]\n"
            f"Relevance: {score:.2%}\n"
            f"Content:\n{text}\n"
        )

    return "\n".join(context_parts)


def format_sources_for_display(chunks: List[Tuple[str, Dict, float]]) -> str:
    """Format sources for display in the UI or logs (not for LLM prompt)."""
    if not chunks:
        return "No sources retrieved"

    sources = []
    for i, (_, metadata, score) in enumerate(chunks, 1):
        source = metadata.get("source", "unknown")
        page = metadata.get("page", "")
        page_info = f" (page {page})" if page else ""
        sources.append(f"[{i}] {source}{page_info} (score: {score:.2%})")

    return "Sources:\n" + "\n".join(sources)
