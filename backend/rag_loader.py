# ============================================================
# rag_loader.py — PDF and Text Document Loading
# ============================================================
import os
import logging
from typing import List, Dict, Tuple

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


def load_pdf(filepath: str) -> List[Tuple[str, Dict]]:
    """
    Load text from a PDF file.
    Returns list of (text, metadata) tuples.
    Metadata includes filename and page number.
    """
    documents = []
    filename = os.path.basename(filepath)

    try:
        with fitz.open(filepath) as pdf:
            for page_num in range(len(pdf)):
                page = pdf[page_num]
                text = page.get_text("text").strip()
                if text:
                    documents.append((text, {
                        "source": filename,
                        "page": page_num + 1,
                        "doc_type": "pdf"
                    }))
        logger.info(f"[RAG] Loaded {len(documents)} pages from PDF: {filename}")
    except Exception as e:
        logger.error(f"[RAG] Failed to load PDF {filepath}: {e}")
        raise

    return documents


def load_text_file(filepath: str) -> List[Tuple[str, Dict]]:
    """
    Load text from a plain text or markdown file.
    Returns list of (text, metadata) tuples.
    """
    documents = []
    filename = os.path.basename(filepath)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read().strip()
            if text:
                documents.append((text, {
                    "source": filename,
                    "doc_type": "txt"
                }))
        logger.info(f"[RAG] Loaded text file: {filename}")
    except Exception as e:
        logger.error(f"[RAG] Failed to load text file {filepath}: {e}")
        raise

    return documents


def load_document(filepath: str) -> List[Tuple[str, Dict]]:
    """
    Load a document based on its file extension.
    Supports .pdf, .txt, and .md files.
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".pdf":
        return load_pdf(filepath)
    elif ext in (".txt", ".md"):
        return load_text_file(filepath)
    else:
        logger.warning(f"[RAG] Unsupported file type: {ext} — skipping {filepath}")
        return []


def load_all_documents(knowledge_dir: str) -> List[Tuple[str, Dict]]:
    """
    Load all documents from a directory.
    Recursively searches for .pdf, .txt, and .md files.
    Returns list of (text, metadata) tuples.
    """
    all_docs = []

    if not os.path.exists(knowledge_dir):
        logger.warning(f"[RAG] Knowledge directory does not exist: {knowledge_dir}")
        return all_docs

    for root, _, files in os.walk(knowledge_dir):
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in (".pdf", ".txt", ".md"):
                filepath = os.path.join(root, filename)
                docs = load_document(filepath)
                all_docs.extend(docs)

    logger.info(f"[RAG] Loaded {len(all_docs)} total documents from {knowledge_dir}")
    return all_docs
