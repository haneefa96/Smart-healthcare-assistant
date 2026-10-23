# ============================================================
# rag_index.py — ChromaDB Vector Store Management
# ============================================================
import logging
import os
import shutil
from typing import List, Tuple, Dict

import chromadb
from chromadb.config import Settings

from rag_config import VECTOR_STORE_PATH, CHUNK_SIZE, CHUNK_OVERLAP, KNOWLEDGE_DIR
from rag_loader import load_all_documents
from rag_chunker import chunk_documents
from rag_embeddings import embed_texts, get_dimension

logger = logging.getLogger(__name__)

_client: chromadb.Client | None = None
_collection: chromadb.Collection | None = None


def get_client():
    """Get or create the ChromaDB client."""
    global _client

    if _client is not None:
        return _client

    # Ensure vector store directory exists
    os.makedirs(VECTOR_STORE_PATH, exist_ok=True)

    _client = chromadb.PersistentClient(path=VECTOR_STORE_PATH)
    logger.info(f"[RAG] ChromaDB client initialized — store at {VECTOR_STORE_PATH}")

    return _client


def get_collection():
    """Get or create the ChromaDB collection."""
    global _collection

    if _collection is not None:
        return _collection

    client = get_client()

    # Check if collection exists
    collections = client.list_collections()
    collection_names = [c.name for c in collections]

    if "healthcare_rag" in collection_names:
        logger.info("[RAG] Loading existing vector store collection")
        _collection = client.get_collection("healthcare_rag")
    else:
        # Create new collection with embedding dimension
        dimension = get_dimension()
        logger.info(f"[RAG] Creating new vector store collection (dimension={dimension})")
        _collection = client.create_collection(
            "healthcare_rag",
            metadata={"hnsw:space": "cosine", "chunk_size": CHUNK_SIZE, "chunk_overlap": CHUNK_OVERLAP}
        )

    return _collection


def clear_vector_store():
    """Delete the vector store and reset state. Use with caution!"""
    global _collection, _client

    if _collection is not None:
        _collection = None

    if _client is not None:
        _client = None

    # Remove persistent storage
    if os.path.exists(VECTOR_STORE_PATH):
        shutil.rmtree(VECTOR_STORE_PATH)
        logger.info(f"[RAG] Vector store cleared: {VECTOR_STORE_PATH}")


def rebuild_index():
    """Rebuild the entire vector store from source documents."""
    global _collection

    logger.info("[RAG] Starting vector store rebuild...")

    # Clear existing index
    clear_vector_store()

    # Load documents
    documents = load_all_documents(KNOWLEDGE_DIR)

    if not documents:
        logger.warning("[RAG] No documents found in knowledge directory")
        return False

    # Chunk documents
    chunked = chunk_documents(documents, CHUNK_SIZE, CHUNK_OVERLAP)

    if not chunked:
        logger.error("[RAG] No chunks generated from documents")
        return False

    # Extract texts and metadata
    texts = [text for text, _ in chunked]
    metadatas = [meta for _, meta in chunked]
    ids = [f"doc_{i}" for i in range(len(texts))]

    # Generate embeddings
    logger.info(f"[RAG] Generating embeddings for {len(texts)} chunks...")
    embeddings = embed_texts(texts)

    # Add to ChromaDB
    collection = get_collection()
    collection.add(
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
        ids=ids
    )

    logger.info(f"[RAG] Index rebuilt: {len(texts)} chunks added to vector store")
    return True


def get_index_stats() -> Dict:
    """Return statistics about the current vector store."""
    collection = get_collection()
    count = collection.count()
    return {
        "collection": "healthcare_rag",
        "chunk_count": count,
        "vector_store_path": VECTOR_STORE_PATH,
        "embedding_model": collection.metadata.get("embedding_model", "unknown") if hasattr(collection, "metadata") else "unknown"
    }


def is_index_built() -> bool:
    """Check if the vector store has been populated."""
    collection = get_collection()
    return collection.count() > 0
