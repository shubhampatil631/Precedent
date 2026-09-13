"""
03_build_grounding_corpus.py
Filters customer-brand threads to isolate genuine resolutions (removing handoffs/DM requests),
tags each resolved pair with an intent from intent_taxonomy.json using semantic similarity,
and outputs data/grounding/resolved_threads.jsonl.
"""

import os
import sys
import re
import json
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Configure UTF-8 for console output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure root dir is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.config import SAMPLE_DATA_DIR, GROUNDING_DATA_DIR, DATA_DIR, BRAND_AUTHOR_ID, EMBEDDING_MODEL_NAME

# Comprehensive handoff regex patterns (case-insensitive)
HANDOFF_PATTERNS = [
    r"\b(dm|direct\s*message|private\s*message)\b",
    r"send\s+(us\s+)?(a\s+)?(dm|direct\s*message|private\s*message)",
    r"send.*(info|details|confirmation|record\s*locator|pnr|booking\s*code|email|name|phone)",
    r"follow\s*(us\s*)?(back)?\s*(&|and)?\s*(dm|send)",
    r"please\s+(dm|message)\s+us",
    r"\b(call|contact)\s+(us\s+at|our\s+reservations|customer\s*relations|support\s*at)\b",
    r"\b(\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
    r"give\s+us\s+a\s+call",
    r"speak\s+with\s+(a\s+)?(representative|agent|specialist)",
    r"^please\s+provide\s+your\s+(record\s*locator|booking|flight\s*number|email)\b",
    r"^(what\s+is|can\s+you\s+share)\s+your\s+(record\s*locator|flight\s*number|ticket\s*number)\??$"
]

COMPILED_HANDOFF_REGEX = re.compile("|".join(HANDOFF_PATTERNS), re.IGNORECASE)

def parse_args():
    parser = argparse.ArgumentParser(description="Build resolved grounding corpus")
    parser.add_argument("--brand", type=str, default=BRAND_AUTHOR_ID, help="Target brand author_id")
    parser.add_argument("--max-grounding", type=int, default=2000, help="Maximum number of grounding pairs to keep")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    return parser.parse_args()

def is_handoff_reply(reply_text: str) -> bool:
    """Checks if a brand reply matches handoff regex patterns."""
    return bool(COMPILED_HANDOFF_REGEX.search(reply_text.strip()))

def build_grounding_corpus(brand_id: str, max_grounding: int, seed: int):
    print("==================================================")
    print(f"Building Grounding Corpus for: {brand_id}")
    print("==================================================")

    # 1. Load sample dataset
    sample_file = SAMPLE_DATA_DIR / f"{brand_id}_threads.parquet"
    if not sample_file.exists():
        raise FileNotFoundError(f"Sample data file not found at {sample_file}. Run 01_sample_data.py first.")

    print(f"Loading candidate threads from {sample_file}...")
    df = pd.read_parquet(sample_file)
    total_candidates = len(df)
    print(f"Total candidate threads: {total_candidates:,}")

    # 2. Apply handoff filtering
    print("\nApplying handoff filter regex to isolate resolved interactions...")
    df["is_handoff"] = df["brand_text"].apply(is_handoff_reply)
    
    handoff_count = int(df["is_handoff"].sum())
    resolved_df = df[~df["is_handoff"]].copy().reset_index(drop=True)
    resolved_count = len(resolved_df)
    handoff_pct = (handoff_count / total_candidates) * 100.0

    print("-" * 50)
    print(f"Total Evaluated Threads: {total_candidates:,}")
    print(f"Handoff / Non-resolving Threads Filtered: {handoff_count:,} ({handoff_pct:.2f}%)")
    print(f"Genuine Resolved Threads Retained: {resolved_count:,} ({100.0 - handoff_pct:.2f}%)")
    print("-" * 50)

    # 3. Load intent taxonomy
    taxonomy_path = DATA_DIR / "intent_taxonomy.json"
    if not taxonomy_path.exists():
        raise FileNotFoundError(f"Taxonomy file not found at {taxonomy_path}. Run 02_build_taxonomy.py first.")

    with open(taxonomy_path, "r", encoding="utf-8") as f:
        taxonomy_data = json.load(f)

    intents = taxonomy_data["intents"]
    print(f"Loaded {len(intents)} intent categories from {taxonomy_path}.")

    # 4. Semantic Intent Tagging using SentenceTransformer
    print(f"\nEmbedding intent definitions and customer texts via '{EMBEDDING_MODEL_NAME}'...")
    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

    # Create composite intent representations (label + description + example queries)
    intent_ids = [intent["id"] for intent in intents]
    intent_texts = [
        f"{intent['label']}: {intent['description']} Examples: {' '.join(intent.get('examples', []))}"
        for intent in intents
    ]
    intent_embeddings = embedder.encode(intent_texts, normalize_embeddings=True)

    # Embed resolved customer messages
    print(f"Tagging {resolved_count:,} resolved queries with intent categories...")
    customer_texts = resolved_df["customer_text"].tolist()
    cust_embeddings = embedder.encode(customer_texts, show_progress_bar=False, normalize_embeddings=True)

    # Compute similarity and assign top intent
    similarity_matrix = cosine_similarity(cust_embeddings, intent_embeddings)
    top_intent_indices = np.argmax(similarity_matrix, axis=1)
    top_similarities = np.max(similarity_matrix, axis=1)

    resolved_df["intent"] = [intent_ids[idx] for idx in top_intent_indices]
    resolved_df["intent_confidence"] = top_similarities

    # 5. Cap or subsample if exceeding max_grounding while maintaining intent diversity
    if len(resolved_df) > max_grounding:
        print(f"\nSubsampling to target {max_grounding:,} grounding pairs with intent stratification...")
        stratified_samples = []
        for intent_id, group in resolved_df.groupby("intent"):
            n_intent = max(10, int(round((len(group) / len(resolved_df)) * max_grounding)))
            sampled_group = group.sample(n=min(n_intent, len(group)), random_state=seed)
            stratified_samples.append(sampled_group)
        
        final_df = pd.concat(stratified_samples).drop_duplicates(subset=["thread_id"])
        if len(final_df) > max_grounding:
            final_df = final_df.sample(n=max_grounding, random_state=seed).reset_index(drop=True)
        else:
            final_df = final_df.reset_index(drop=True)
    else:
        final_df = resolved_df.reset_index(drop=True)

    # 6. Save to data/grounding/resolved_threads.jsonl
    GROUNDING_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_jsonl_path = GROUNDING_DATA_DIR / "resolved_threads.jsonl"
    output_parquet_path = GROUNDING_DATA_DIR / "resolved_threads.parquet"

    print(f"\nWriting grounding corpus to {output_jsonl_path}...")
    output_records = []
    with open(output_jsonl_path, "w", encoding="utf-8") as f:
        for _, row in final_df.iterrows():
            record = {
                "thread_id": str(row["thread_id"]),
                "intent": str(row["intent"]),
                "customer_text": str(row["customer_text"]),
                "brand_text": str(row["brand_text"]),
                "intent_confidence": round(float(row.get("intent_confidence", 1.0)), 4)
            }
            output_records.append(record)
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    final_df.to_parquet(output_parquet_path, index=False)

    # 7. Print intent breakdown
    print("\n" + "="*50)
    print("GROUNDING CORPUS INTENT BREAKDOWN")
    print("="*50)
    intent_counts = final_df["intent"].value_counts()
    for intent_name, count in intent_counts.items():
        pct = (count / len(final_df)) * 100.0
        print(f"  {intent_name:<30}: {count:>5} ({pct:>5.1f}%)")
    print("="*50)
    print(f"Total Grounding Pairs Written: {len(final_df):,}")
    print(f"Filter Drop Rate: {handoff_pct:.2f}%")

    stats = {
        "brand": brand_id,
        "total_candidate_threads": total_candidates,
        "handoff_threads_filtered": handoff_count,
        "handoff_filter_drop_pct": round(handoff_pct, 2),
        "resolved_grounding_pairs_saved": len(final_df),
        "intent_distribution": intent_counts.to_dict()
    }

    stats_output = GROUNDING_DATA_DIR / "grounding_stats.json"
    with open(stats_output, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"Saved grounding stats to {stats_output}")
    print("\n✅ Step 2.3 complete: 03_build_grounding_corpus.py finished successfully!")
    return stats

if __name__ == "__main__":
    args = parse_args()
    build_grounding_corpus(
        brand_id=args.brand,
        max_grounding=args.max_grounding,
        seed=args.seed
    )
