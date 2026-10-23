#!/usr/bin/env python3
"""
Simple test script to verify RAG pipeline functionality.
Tests document loading, chunking, embedding, indexing, and retrieval.

Usage:
    python test_rag.py [--verbose]
"""

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# Import RAG modules
from rag_index import rebuild_index, get_index_stats, clear_vector_store
from rag_retriever import retrieve_context, format_context, format_sources_for_display
from rag_config import validate, get_env_summary, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K


async def test_rag_pipeline():
    """Run the RAG pipeline tests."""
    print("\n" + "="*70)
    print("RAG Pipeline Test")
    print("="*70)

    # 1. Validate configuration
    print("\n1. Validating configuration...")
    valid, error = validate()
    if not valid:
        print(f"   ❌ Configuration validation failed: {error}")
        return False
    print(f"   ✅ Configuration valid: {get_env_summary()}")

    # 2. Rebuild index
    print(f"\n2. Building RAG index (chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    try:
        success = rebuild_index()
        if not success:
            print("   ❌ Failed to build index")
            return False
        print("   ✅ Index built successfully")
    except Exception as e:
        print(f"   ❌ Index build error: {e}")
        return False

    # 3. Get index stats
    print("\n3. Index statistics:")
    stats = get_index_stats()
    print(f"   - Collection: {stats['collection']}")
    print(f"   - Chunk count: {stats['chunk_count']}")

    # 4. Test retrieval with different queries
    print("\n4. Testing retrieval...")

    test_queries = [
        "What is a normal heart rate?",
        "How do I take my vitals?",
        "What is this robot?",
    ]

    all_passed = True
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        try:
            chunks = retrieve_context(query, top_k=TOP_K)

            if not chunks:
                print("   ⚠️  No chunks retrieved")
                all_passed = False
                continue

            print(f"   Retrieved {len(chunks)} chunks:")
            for i, (text, meta, score) in enumerate(chunks, 1):
                print(f"     [{i}] {meta.get('source', 'unknown')} (score: {score:.3f})")
                print(f"         First 100 chars: {text[:100]}...")

            # Format context
            context = format_context(chunks)
            print(f"   Context length: {len(context)} chars")

            # Format sources for display
            sources = format_sources_for_display(chunks)
            print(f"   Sources:\n{sources}")

        except Exception as e:
            print(f"   ❌ Retrieval error: {e}")
            all_passed = False

    # 5. Final summary
    print("\n" + "="*70)
    if all_passed:
        print("✅ All RAG tests passed!")
    else:
        print("⚠️  Some tests had issues (check logs)")
    print("="*70 + "\n")

    return all_passed


async def main():
    verbose = "--verbose" in sys.argv

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Clear existing index to force rebuild
    print("Clearing existing vector store...")
    try:
        clear_vector_store()
    except Exception as e:
        log.warning(f"Could not clear vector store: {e}")

    success = await test_rag_pipeline()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
