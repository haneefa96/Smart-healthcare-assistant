# ============================================================
# rag_chunker.py — Text Chunking with Overlap
# ============================================================
import logging
import re
from typing import List, Tuple, Dict

from rag_config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)


def split_by_char(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into chunks of approximately chunk_size characters,
    with overlap between consecutive chunks.
    """
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        if end >= len(text):
            # Last chunk — take rest of text
            chunks.append(chunk)
            break
        else:
            # Try to break at sentence boundary
            # Look backward for a sentence ending (. ! ?)
            last_punct = max(chunk.rfind(". "), chunk.rfind("! "), chunk.rfind("? "))
            if last_punct > chunk_size * 0.5:  # Only break if past 50% of chunk
                chunks.append(text[start:last_punct + 1])
                start = last_punct + 1
            else:
                chunks.append(chunk)
                start = end - overlap if end - overlap > start else end

    return chunks


def split_by_paragraph(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text by paragraphs, merging small ones to stay within chunk_size.
    This preserves paragraph structure better than pure character splitting.
    """
    if not text:
        return []

    # Split by double newline (paragraph boundary)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # If paragraph is larger than chunk_size, fall back to char splitting
        if len(para) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            # Split large paragraph
            sub_chunks = split_by_char(para, chunk_size, overlap)
            chunks.extend(sub_chunks)
            continue

        # Try to add paragraph to current chunk
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
        else:
            # Save current chunk and start new one
            if current_chunk:
                chunks.append(current_chunk)

            # If para is small enough, start new chunk with it
            if len(para) <= chunk_size:
                current_chunk = para
            else:
                # Very large paragraph — fall back
                current_chunk = ""
                sub_chunks = split_by_char(para, chunk_size, overlap)
                chunks.extend(sub_chunks)

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def chunk_documents(
    documents: List[Tuple[str, Dict]],
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP
) -> List[Tuple[str, Dict]]:
    """
    Chunk a list of (text, metadata) tuples.
    Returns list of (chunk_text, metadata_with_chunk_info) tuples.
    """
    chunked_docs = []

    for text, metadata in documents:
        chunks = split_by_paragraph(text, chunk_size, overlap)

        for i, chunk_text in enumerate(chunks):
            chunk_meta = metadata.copy()
            chunk_meta["chunk_index"] = i
            chunk_meta["chunk_count"] = len(chunks)
            chunked_docs.append((chunk_text, chunk_meta))

        if chunks:
            logger.info(f"[RAG] Split document '{metadata.get('source', 'unknown')}' "
                       f"into {len(chunks)} chunks")

    return chunked_docs
