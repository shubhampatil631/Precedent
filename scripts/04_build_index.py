"""
04_build_index.py
Builds a persistent ChromaDB vector index from data/grounding/resolved_threads.jsonl.
Embeds customer_text using sentence-transformers/all-MiniLM-L6-v2, stores metadata
(intent, brand_text, thread_id, customer_text), and performs 5 spot-check queries.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# Configure UTF-8 for console output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure root dir is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.config import GROUNDING_DATA_DIR, CHROMA_DB_DIR, EMBEDDING_MODEL_NAME

COLLECTION_NAME = "grounding_v1"

def parse_args():
    parser = argparse.ArgumentParser(description="Build ChromaDB grounding index")
    parser.add_argument("--jsonl-file", type=str, default=str(GROUNDING_DATA_DIR / "resolved_threads.jsonl"))
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for embedding and indexing")
    return parser.parse_args()

def build_index(jsonl_file: Path, batch_size: int):
    print("==================================================")
    print("Building ChromaDB Vector Index")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Storage path: {CHROMA_DB_DIR}")
    print(f"Embedding model: {EMBEDDING_MODEL_NAME}")
    print("==================================================")

    if not jsonl_file.exists():
        raise FileNotFoundError(f"Resolved threads file not found at {jsonl_file}. Run 03_build_grounding_corpus.py first.")

    # 1. Load grounding records
    print(f"Reading grounding pairs from {jsonl_file}...")
    records = []
    with open(jsonl_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Loaded {len(records):,} grounding resolution pairs.")

    # 2. Initialize ChromaDB client
    CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

    # Reset collection if exists to guarantee fresh rebuild
    existing_collections = [c.name for c in client.list_collections()]
    if COLLECTION_NAME in existing_collections:
        print(f"Collection '{COLLECTION_NAME}' already exists. Deleting for clean rebuild...")
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine", "description": "Resolved customer support threads grounding index"}
    )

    # 3. Load embedding model
    print(f"\nLoading SentenceTransformer: {EMBEDDING_MODEL_NAME}...")
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

    # 4. Batched indexing
    print(f"\nIndexing {len(records):,} documents into ChromaDB in batches of {batch_size}...")
    start_time = time.perf_counter()

    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        
        ids = [str(r["thread_id"]) for r in batch]
        documents = [str(r["customer_text"]) for r in batch]
        metadatas = [
            {
                "thread_id": str(r["thread_id"]),
                "intent": str(r["intent"]),
                "brand_text": str(r["brand_text"]),
                "customer_text": str(r["customer_text"]),
                "intent_confidence": float(r.get("intent_confidence", 1.0))
            }
            for r in batch
        ]

        # Generate embeddings
        embeddings = embedder.encode(documents, show_progress_bar=False, normalize_embeddings=True).tolist()

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        print(f"  Indexed batch {i + 1} - {min(i + len(batch), len(records))} / {len(records)}")

    elapsed = round(time.perf_counter() - start_time, 2)
    print(f"\nSuccessfully indexed {collection.count():,} items in {elapsed} seconds.")

    # 5. Spot-check 5 manual queries
    print("\n" + "="*60)
    print("SPOT-CHECK QUERY VERIFICATION (5 Test Queries)")
    print("="*60)

    test_queries = [
        {
            "query": "My flight from ORD to DFW was delayed 3 hours and I missed my connection",
            "intent": "flight_delay_cancellation"
        },
        {
            "query": "My checked bag is missing from carousel 4 in Miami airport",
            "intent": "baggage_luggage_issues"
        },
        {
            "query": "I was separated from my family and lost our assigned seats",
            "intent": "seat_cabin_comfort"
        },
        {
            "query": "How do I claim a refund for my cancelled flight voucher?",
            "intent": "refund_compensation_claims"
        },
        {
            "query": "Thank you so much to flight attendant Sarah for amazing service today!",
            "intent": "praise_feedback_gratitude"
        }
    ]

    for idx, test in enumerate(test_queries, 1):
        q_text = test["query"]
        q_intent = test["intent"]
        print(f"\n[Test Query {idx}]")
        print(f"Customer Input: \"{q_text}\"")
        print(f"Target Intent: {q_intent}")

        # Embed query
        q_emb = embedder.encode([q_text], normalize_embeddings=True).tolist()

        # Query ChromaDB (with intent filter)
        results = collection.query(
            query_embeddings=q_emb,
            n_results=2,
            where={"intent": q_intent}
        )

        if results and results["ids"] and len(results["ids"][0]) > 0:
            for r_idx in range(len(results["ids"][0])):
                doc_id = results["ids"][0][r_idx]
                dist = results["distances"][0][r_idx]
                sim = round(1.0 - dist, 4)  # cosine similarity
                meta = results["metadatas"][0][r_idx]
                print(f"  -> Match #{r_idx + 1} (Sim: {sim * 100:.1f}%) [Thread: {doc_id}]")
                print(f"     Historical Cust: \"{meta['customer_text']}\"")
                print(f"     Brand Resolution: \"{meta['brand_text']}\"")
        else:
            print("  -> No matches found.")

    print("\n" + "="*60)
    print("Step 2.4 complete: 04_build_index.py finished successfully!")
    return collection.count()

if __name__ == "__main__":
    args = parse_args()
    build_index(
        jsonl_file=Path(args.jsonl_file),
        batch_size=args.batch_size
    )
