"""
Node 2: Retrieval of Historical Precedent (app/pipeline/retrieve.py)
Input: { "customer_text": str, "intent": str, "confidence": float }
Output: { "retrieved": list[dict] }
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import chromadb
from sentence_transformers import SentenceTransformer

from app.config import (
    CHROMA_DB_DIR,
    EMBEDDING_MODEL_NAME,
    TOP_K_RETRIEVAL,
    CONFIDENCE_THRESHOLD,
    SIMILARITY_FLOOR
)

logger = logging.getLogger("retrieve_node")

COLLECTION_NAME = "grounding_v1"

# Cached ChromaDB client and SentenceTransformer embedder
_CHROMA_COLLECTION = None
_EMBEDDER = None

def get_chroma_collection():
    global _CHROMA_COLLECTION
    if _CHROMA_COLLECTION is None:
        client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        _CHROMA_COLLECTION = client.get_collection(
            name=COLLECTION_NAME
        )
    return _CHROMA_COLLECTION

def get_embedder() -> SentenceTransformer:
    global _EMBEDDER
    if _EMBEDDER is None:
        try:
            _EMBEDDER = SentenceTransformer(EMBEDDING_MODEL_NAME, local_files_only=True)
        except Exception:
            _EMBEDDER = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _EMBEDDER

def retrieve_precedents(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieves top-k historical resolution precedents from ChromaDB collection.
    
    Logic:
    1. Embed customer_text using all-MiniLM-L6-v2.
    2. If confidence >= CONFIDENCE_THRESHOLD and intent != "other_unclear":
       Query top_k filtered by intent.
       If empty or low similarity, fallback to unfiltered semantic search.
    3. If confidence < CONFIDENCE_THRESHOLD:
       Drop intent filter entirely and query pure semantic similarity.
    4. If top similarity < SIMILARITY_FLOOR:
       Return empty list [] (serves as explicit 'no precedent found' routing signal).
    """
    customer_text = state.get("customer_text", "").strip()
    intent = state.get("intent", "other_unclear")
    confidence = float(state.get("confidence", 0.0))

    if not customer_text:
        return {"retrieved": []}

    try:
        collection = get_chroma_collection()
        embedder = get_embedder()

        # Generate query embedding
        query_embedding = embedder.encode([customer_text], normalize_embeddings=True).tolist()

        # Decide whether to apply intent filter
        apply_filter = (confidence >= CONFIDENCE_THRESHOLD) and (intent != "other_unclear")

        results = None
        if apply_filter:
            # 1. Filtered query
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=TOP_K_RETRIEVAL,
                where={"intent": intent}
            )

        # 2. Fallback to unfiltered if no results found or confidence is low
        has_results = results and results["ids"] and len(results["ids"][0]) > 0
        if not has_results:
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=TOP_K_RETRIEVAL
            )

        retrieved_list: List[Dict[str, Any]] = []

        if results and results["ids"] and len(results["ids"][0]) > 0:
            doc_ids = results["ids"][0]
            distances = results["distances"][0]
            metadatas = results["metadatas"][0]

            for i in range(len(doc_ids)):
                dist = distances[i]
                # In Chroma with cosine distance, similarity = 1.0 - distance
                similarity = round(max(0.0, 1.0 - dist), 4)
                meta = metadatas[i]

                retrieved_list.append({
                    "thread_id": str(meta.get("thread_id", doc_ids[i])),
                    "customer_text": str(meta.get("customer_text", "")),
                    "brand_text": str(meta.get("brand_text", "")),
                    "similarity": similarity,
                    "intent": str(meta.get("intent", ""))
                })

        # 3. Floor check: If top similarity < SIMILARITY_FLOOR, return empty list
        if retrieved_list:
            top_similarity = retrieved_list[0]["similarity"]
            if top_similarity < SIMILARITY_FLOOR:
                logger.info(
                    f"Top similarity {top_similarity:.3f} below floor {SIMILARITY_FLOOR:.3f}. "
                    "Returning empty retrieved list (routing signal: no precedent found)."
                )
                return {"retrieved": []}

        return {"retrieved": retrieved_list}

    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return {"retrieved": []}

if __name__ == "__main__":
    # Standalone verification tests
    test_cases = [
        {
            "desc": "High confidence flight delay",
            "state": {
                "customer_text": "@AmericanAir my flight AA290 from DFW to ORD got cancelled and I have a connecting flight! What are my options?",
                "intent": "flight_delay_cancellation",
                "confidence": 0.95
            }
        },
        {
            "desc": "High confidence lost baggage",
            "state": {
                "customer_text": "@AmericanAir landed in MIA but my checked bag didn't show up on carousel 4. Where do I file a claim?",
                "intent": "baggage_luggage_issues",
                "confidence": 0.95
            }
        },
        {
            "desc": "Low confidence query (should trigger fallback to pure similarity)",
            "state": {
                "customer_text": "Is the wifi free on the flight to London?",
                "intent": "other_unclear",
                "confidence": 0.35
            }
        },
        {
            "desc": "Out-of-domain nonsense query (should drop below 0.30 floor and return empty list)",
            "state": {
                "customer_text": "How do I bake a chocolate cake with bananas and pineapples?",
                "intent": "other_unclear",
                "confidence": 0.20
            }
        }
    ]

    print("==================================================")
    print("Testing Standalone Retrieval Node (retrieve.py)")
    print("==================================================")

    for tc in test_cases:
        print(f"\n--- Test: {tc['desc']} ---")
        print(f"Customer Input: \"{tc['state']['customer_text']}\"")
        print(f"Input Intent: {tc['state']['intent']} (Conf: {tc['state']['confidence'] * 100:.1f}%)")

        output = retrieve_precedents(tc["state"])
        matches = output.get("retrieved", [])
        print(f"Retrieved Count: {len(matches)}")

        if matches:
            top_match = matches[0]
            print(f"Top Match Similarity: {top_match['similarity'] * 100:.1f}% [Thread: {top_match['thread_id']}]")
            print(f"  Historical Cust: \"{top_match['customer_text']}\"")
            print(f"  Brand Resolution: \"{top_match['brand_text']}\"")
        else:
            print("  Result: Empty list (Below floor or no precedent found) -> Triggers ESCALATION signal.")

    print("\n==================================================")
    print("Retrieval Node Test Complete!")
