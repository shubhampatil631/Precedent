"""
01_sample_data.py
Extracts and samples customer-brand conversation pairs for a target brand from Kaggle twcs.csv.

Vectorized and memory-efficient implementation for instant processing of millions of rows.
"""

import os
import sys
import json
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

# Configure UTF-8 for console output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure root dir is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.config import RAW_DATA_DIR, SAMPLE_DATA_DIR, BRAND_AUTHOR_ID

def parse_args():
    parser = argparse.ArgumentParser(description="Extract and sample brand threads from twcs.csv")
    parser.add_argument("--brand", type=str, default=BRAND_AUTHOR_ID, help="Target brand author_id (e.g. AmericanAir)")
    parser.add_argument("--raw-file", type=str, default=str(RAW_DATA_DIR / "twcs.csv"), help="Path to raw twcs.csv")
    parser.add_argument("--target-sample-size", type=int, default=6000, help="Target subsample size (between 3000-8000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    return parser.parse_args()

def process_brand_data(raw_file: Path, brand_id: str, target_sample_size: int, seed: int):
    print("==================================================")
    print(f"Processing Data for Brand: {brand_id}")
    print(f"Reading raw CSV: {raw_file}")
    print("==================================================")

    if not raw_file.exists():
        raise FileNotFoundError(f"Raw data file not found at {raw_file}. Please place twcs.csv in data/raw/")

    # 1. Read required columns
    columns = [
        "tweet_id", "author_id", "inbound", "created_at",
        "text", "response_tweet_id", "in_response_to_tweet_id"
    ]
    
    print("Loading CSV into DataFrame...")
    dtype_dict = {
        "tweet_id": "str",
        "author_id": "str",
        "inbound": "bool",
        "created_at": "str",
        "text": "str",
        "response_tweet_id": "str",
        "in_response_to_tweet_id": "str"
    }
    
    df = pd.read_csv(raw_file, usecols=columns, dtype=dtype_dict, low_memory=False)
    print(f"Total rows in twcs.csv: {len(df):,}")

    # Clean tweet IDs
    df["tweet_id"] = df["tweet_id"].astype(str).str.strip()
    df["in_response_to_tweet_id"] = df["in_response_to_tweet_id"].fillna("").astype(str).str.strip()
    df["response_tweet_id"] = df["response_tweet_id"].fillna("").astype(str).str.strip()

    # 2. Filter brand replies
    brand_mask = (df["author_id"] == brand_id) & (~df["inbound"]) & (df["in_response_to_tweet_id"] != "")
    brand_df = df[brand_mask].copy()
    print(f"Found {len(brand_df):,} replies by brand '{brand_id}'")

    if len(brand_df) == 0:
        available_brands = df[~df["inbound"]]["author_id"].value_counts().head(10)
        print(f"No tweets found for '{brand_id}'. Top available brands in dataset:")
        print(available_brands)
        return

    # 3. Vectorized join: match brand tweet to parent inbound customer tweet
    print("Joining brand replies with root customer tweets...")
    # Parent must be inbound (from customer)
    inbound_df = df[df["inbound"]].copy()

    merged = brand_df.merge(
        inbound_df,
        left_on="in_response_to_tweet_id",
        right_on="tweet_id",
        suffixes=("_brand", "_cust")
    )
    print(f"Successfully paired {len(merged):,} customer-brand threads.")

    # 4. Detect multi-turn interactions (if customer replied back to brand)
    print("Checking multi-turn conversation depth...")
    # Fast set of all tweets that responded to brand tweets
    inbound_parents_set = set(inbound_df["in_response_to_tweet_id"].values)
    
    # Check if brand_tweet_id was responded to by any inbound tweet
    merged["has_further_customer_reply"] = merged["tweet_id_brand"].isin(inbound_parents_set)

    # 5. Parse timestamps to compute response latency
    print("Calculating response latencies...")
    date_format = "%a %b %d %H:%M:%S %z %Y"
    merged["cust_dt"] = pd.to_datetime(merged["created_at_cust"], format=date_format, errors="coerce", utc=True)
    merged["brand_dt"] = pd.to_datetime(merged["created_at_brand"], format=date_format, errors="coerce", utc=True)
    merged["response_latency_seconds"] = (merged["brand_dt"] - merged["cust_dt"]).dt.total_seconds()

    valid_latencies = merged["response_latency_seconds"].dropna()
    valid_latencies = valid_latencies[valid_latencies >= 0]
    median_latency_sec = float(valid_latencies.median()) if len(valid_latencies) > 0 else 0.0
    mean_latency_sec = float(valid_latencies.mean()) if len(valid_latencies) > 0 else 0.0

    # Thread counts and percentages
    total_reconstructed = len(merged)
    multi_turn_count = int(merged["has_further_customer_reply"].sum())
    single_turn_count = total_reconstructed - multi_turn_count
    multi_turn_dropped_pct = round((multi_turn_count / total_reconstructed * 100), 2) if total_reconstructed > 0 else 0.0

    date_min = str(merged["cust_dt"].min())
    date_max = str(merged["cust_dt"].max())

    print("\n" + "="*50)
    print("DATASET & THREAD SUMMARY STATISTICS")
    print("="*50)
    print(f"Brand Target: {brand_id}")
    print(f"Total Reconstructed Threads: {total_reconstructed:,}")
    print(f"Single-Turn Threads: {single_turn_count:,} ({100 - multi_turn_dropped_pct:.2f}%)")
    print(f"Multi-Turn Threads (flagged / out-of-scope for v1): {multi_turn_count:,} ({multi_turn_dropped_pct:.2f}%)")
    print(f"Median Response Latency: {median_latency_sec / 60.0:.1f} minutes ({median_latency_sec:.0f} seconds)")
    print(f"Mean Response Latency: {mean_latency_sec / 60.0:.1f} minutes")
    print(f"Date Range: {date_min} to {date_max}")
    print("="*50)

    # 6. Format and Sample output dataset
    merged["thread_id"] = brand_id + "_" + merged["tweet_id_brand"]
    
    formatted_df = pd.DataFrame({
        "thread_id": merged["thread_id"],
        "customer_tweet_id": merged["tweet_id_cust"],
        "customer_text": merged["text_cust"].str.strip(),
        "customer_created_at": merged["created_at_cust"],
        "brand_tweet_id": merged["tweet_id_brand"],
        "brand_text": merged["text_brand"].str.strip(),
        "brand_created_at": merged["created_at_brand"],
        "has_further_customer_reply": merged["has_further_customer_reply"],
        "response_latency_seconds": merged["response_latency_seconds"]
    })

    # Drop empty or corrupted texts
    formatted_df = formatted_df.dropna(subset=["customer_text", "brand_text"])
    formatted_df = formatted_df[
        (formatted_df["customer_text"].str.len() > 5) & 
        (formatted_df["brand_text"].str.len() > 5)
    ]

    # Primary subsample: single-turn pairs
    single_turn_df = formatted_df[~formatted_df["has_further_customer_reply"]].copy()

    if len(single_turn_df) > target_sample_size:
        print(f"\nSubsampling {target_sample_size:,} single-turn threads (seed={seed})...")
        sample_df = single_turn_df.sample(n=target_sample_size, random_state=seed).reset_index(drop=True)
    else:
        print(f"\nUsing all available {len(single_turn_df):,} single-turn threads...")
        sample_df = single_turn_df.reset_index(drop=True)

    # Ensure output directories exist
    SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    parquet_path = SAMPLE_DATA_DIR / f"{brand_id}_threads.parquet"
    csv_path = SAMPLE_DATA_DIR / f"{brand_id}_threads.csv"
    stats_path = SAMPLE_DATA_DIR / f"{brand_id}_stats.json"

    print(f"\nSaving sampled dataset to {parquet_path}...")
    sample_df.to_parquet(parquet_path, index=False)
    sample_df.to_csv(csv_path, index=False)

    stats = {
        "brand": brand_id,
        "total_brand_replies_in_raw": len(brand_df),
        "total_reconstructed_threads": total_reconstructed,
        "single_turn_threads_count": single_turn_count,
        "multi_turn_threads_count": multi_turn_count,
        "multi_turn_dropped_pct": multi_turn_dropped_pct,
        "sample_size_saved": len(sample_df),
        "date_range": [date_min, date_max],
        "median_response_latency_seconds": round(median_latency_sec, 2),
        "median_response_latency_minutes": round(median_latency_sec / 60.0, 2),
        "mean_response_latency_minutes": round(mean_latency_sec / 60.0, 2),
        "target_sample_size": target_sample_size,
        "seed": seed
    }

    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"Saved stats to {stats_path}")
    print("\nStep 2.1 complete: 01_sample_data.py finished successfully!")
    return stats

if __name__ == "__main__":
    args = parse_args()
    process_brand_data(
        raw_file=Path(args.raw_file),
        brand_id=args.brand,
        target_sample_size=args.target_sample_size,
        seed=args.seed
    )
