# ============================================================
# rag/ — Retrieval-Augmented Generation Module
# ============================================================
"""
This module provides RAG (Retrieval-Augmented Generation) functionality for the
Healthcare Assistant Robot.

Usage:
    from rag import index, retriever
    
    # Rebuild the vector store from source documents
    index.rebuild_index()
    
    # Retrieve context for a query
    chunks = retriever.retrieve_context("What is a normal heart rate?")
    context = retriever.format_context(chunks)

Modules:
    rag_config    — Configuration and environment variables
    rag_loader    — PDF and text document loading
    rag_chunker   — Text chunking with overlap
    rag_embeddings — Embedding generation using sentence-transformers
    rag_index     — ChromaDB vector store management
    rag_retriever — Query embedding and similarity search
"""

from rag_config import validate, get_env_summary
from rag_index import rebuild_index, get_index_stats, is_index_built, clear_vector_store
from rag_retriever import retrieve_context, format_context, format_sources_for_display

__all__ = [
    'validate',
    'get_env_summary',
    'rebuild_index',
    'get_index_stats',
    'is_index_built',
    'clear_vector_store',
    'retrieve_context',
    'format_context',
    'format_sources_for_display',
]
