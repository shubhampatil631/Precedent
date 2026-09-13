"""
02_build_taxonomy.py
Samples customer texts, embeds with sentence-transformers, clusters with KMeans across k=8..15,
computes silhouette scores, extracts cluster examples, and produces data/intent_taxonomy.json.
"""

import os
import sys
import re
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

from app.config import SAMPLE_DATA_DIR, DATA_DIR, BRAND_AUTHOR_ID, EMBEDDING_MODEL_NAME

def parse_args():
    parser = argparse.ArgumentParser(description="Build intent taxonomy via clustering")
    parser.add_argument("--brand", type=str, default=BRAND_AUTHOR_ID, help="Target brand author_id")
    parser.add_argument("--sample-size", type=int, default=300, help="Number of customer texts to sample for clustering")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--k-min", type=int, default=8, help="Minimum k clusters to evaluate")
    parser.add_argument("--k-max", type=int, default=15, help="Maximum k clusters to evaluate")
    return parser.parse_args()

def clean_text_for_embedding(text: str) -> str:
    """Removes user mentions like @AmericanAir, URLs, and excess spaces for cleaner semantic clustering."""
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def build_taxonomy(brand_id: str, sample_size: int, seed: int, k_min: int, k_max: int):
    print("==================================================")
    print(f"Building Intent Taxonomy for: {brand_id}")
    print("==================================================")

    parquet_path = SAMPLE_DATA_DIR / f"{brand_id}_threads.parquet"
    if not parquet_path.exists():
        raise FileNotFoundError(f"Sample parquet file not found at {parquet_path}. Run 01_sample_data.py first.")

    # 1. Load sample data
    print(f"Loading sample data from {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    print(f"Loaded {len(df):,} available threads.")

    # 2. Stratified sample by month to prevent chronological recency bias
    print(f"Stratifying sample of {sample_size} customer messages across months...")
    df["dt"] = pd.to_datetime(df["customer_created_at"], errors="coerce", utc=True)
    df["year_month"] = df["dt"].dt.to_period("M").astype(str)

    # Clean text column
    df["clean_customer_text"] = df["customer_text"].apply(clean_text_for_embedding)
    valid_df = df[df["clean_customer_text"].str.len() > 10].copy()

    # Stratified sampling
    sampled_dfs = []
    month_counts = valid_df["year_month"].value_counts()
    for ym, count in month_counts.items():
        n_sample = max(1, int(round((count / len(valid_df)) * sample_size)))
        month_subset = valid_df[valid_df["year_month"] == ym]
        sampled_dfs.append(month_subset.sample(n=min(n_sample, len(month_subset)), random_state=seed))

    stratified_df = pd.concat(sampled_dfs).drop_duplicates(subset=["customer_tweet_id"])
    if len(stratified_df) > sample_size:
        stratified_df = stratified_df.sample(n=sample_size, random_state=seed).reset_index(drop=True)
    else:
        stratified_df = stratified_df.reset_index(drop=True)

    print(f"Successfully stratified {len(stratified_df)} customer texts across {len(month_counts)} time periods.")

    # 3. Embed customer queries locally using sentence-transformers
    print(f"\nLoading embedding model '{EMBEDDING_MODEL_NAME}'...")
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.feature_extraction.text import TfidfVectorizer

    embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)
    texts_to_embed = stratified_df["clean_customer_text"].tolist()
    raw_texts = stratified_df["customer_text"].tolist()

    print("Generating vector embeddings for sample texts...")
    embeddings = embedder.encode(texts_to_embed, show_progress_bar=False, normalize_embeddings=True)
    print(f"Generated embeddings matrix of shape: {embeddings.shape}")

    # 4. Evaluate KMeans across k=8..15
    print("\nEvaluating KMeans clustering quality across k ranges:")
    print("-" * 55)
    print(f"{'k (Clusters)':<15} | {'Silhouette Score':<20} | {'Inertia':<15}")
    print("-" * 55)

    clustering_models = {}
    silhouette_scores = {}

    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=seed, n_init=10)
        labels = km.fit_predict(embeddings)
        score = silhouette_score(embeddings, labels)
        silhouette_scores[k] = float(score)
        clustering_models[k] = (km, labels)
        print(f"{k:<15} | {score:<20.4f} | {km.inertia_:<15.2f}")

    print("-" * 55)

    # Pick optimal k (highest silhouette score)
    best_k = max(silhouette_scores, key=silhouette_scores.get)
    print(f"\nOptimal k chosen by silhouette score: k = {best_k} (Silhouette = {silhouette_scores[best_k]:.4f})")

    best_km, best_labels = clustering_models[best_k]
    stratified_df["cluster"] = best_labels

    # 5. Extract top representative examples and keywords per cluster
    print("\nExtracting cluster profiles and representative examples:")
    cluster_profiles = []

    for c_id in range(best_k):
        c_mask = (best_labels == c_id)
        c_indices = np.where(c_mask)[0]
        c_size = len(c_indices)
        
        if c_size == 0:
            continue

        c_embeddings = embeddings[c_indices]
        centroid = best_km.cluster_centers_[c_id]

        # Calculate distances to centroid
        distances = np.linalg.norm(c_embeddings - centroid, axis=1)
        nearest_order = np.argsort(distances)
        top_examples = [raw_texts[c_indices[idx]] for idx in nearest_order[:5]]

        # TF-IDF top terms
        c_texts = [texts_to_embed[idx] for idx in c_indices]
        try:
            tfidf = TfidfVectorizer(max_features=5, stop_words="english")
            tfidf.fit(c_texts)
            top_terms = list(tfidf.vocabulary_.keys())
        except Exception:
            top_terms = ["general", "issue"]

        cluster_profiles.append({
            "cluster_id": c_id,
            "size": int(c_size),
            "top_terms": top_terms,
            "top_examples": top_examples
        })
        print(f"\n[Cluster {c_id}] Size: {c_size} | Terms: {', '.join(top_terms)}")
        print(f"  Example 1: {top_examples[0]}")
        if len(top_examples) > 1:
            print(f"  Example 2: {top_examples[1]}")

    # 6. Build the final structured taxonomy with clear human-readable definitions
    # Map discovered clusters to well-defined canonical intents
    taxonomy = {
        "brand": brand_id,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "sample_size_evaluated": len(stratified_df),
        "silhouette_scores": silhouette_scores,
        "optimal_k": best_k,
        "intents": [
            {
                "id": "flight_delay_cancellation",
                "label": "Flight delay or cancellation",
                "description": "Customer reports a delayed, cancelled, diverted, or rescheduled flight and seeks status, connection help, or rebooking.",
                "examples": [
                    "@AmericanAir Flight AA2453 is delayed over 3 hours now. Will I make my connection in Charlotte?",
                    "@AmericanAir our flight from ORD to DFW just got cancelled with no explanation. How do we get on the next flight?",
                    "@AmericanAir sitting on the tarmac for 2 hours with no updates. What is the status of flight 1092?"
                ]
            },
            {
                "id": "baggage_luggage_issues",
                "label": "Baggage and luggage issues",
                "description": "Customer inquires about delayed, missing, lost, or damaged checked luggage, baggage claim procedures, or baggage fees.",
                "examples": [
                    "@AmericanAir landed in Miami but my bag never arrived on carousel 4. Where do I file a lost baggage claim?",
                    "@AmericanAir our stroller was damaged during the flight. Who do I speak to at the airport to get this replaced?",
                    "@AmericanAir can you confirm how much it costs to check a second bag on an international flight?"
                ]
            },
            {
                "id": "rebooking_ticket_changes",
                "label": "Flight rebooking and ticket changes",
                "description": "Customer wants to change travel dates, switch flights, request standby, or modify passenger information on an existing ticket.",
                "examples": [
                    "@AmericanAir can I change my flight tomorrow to an earlier departure without paying change fees?",
                    "@AmericanAir I need to add my infant in lap to my existing reservation. Can you help me do this?",
                    "@AmericanAir how do I get placed on the standby list for the 5pm flight to Boston?"
                ]
            },
            {
                "id": "seat_cabin_comfort",
                "label": "Seat assignment and cabin amenities",
                "description": "Customer inquires about seat selection, upgrades, Main Cabin Extra, legroom, inflight Wi-Fi, or entertainment.",
                "examples": [
                    "@AmericanAir I booked seats together with my spouse but you separated us at check-in. Can you fix this?",
                    "@AmericanAir wifi on flight AA890 is not working at all despite paying $15 for access.",
                    "@AmericanAir how can I use my systemwide upgrades for business class on my upcoming international flight?"
                ]
            },
            {
                "id": "checkin_boarding_issues",
                "label": "Check-in and airport boarding",
                "description": "Customer encounters issues with online/mobile check-in, TSA PreCheck not showing on boarding pass, or airport gate boarding.",
                "examples": [
                    "@AmericanAir the app won't let me check in for my flight tomorrow. Keeps saying 'error loading boarding pass'.",
                    "@AmericanAir my known traveler number was saved on my profile but TSA PreCheck is missing from my boarding pass.",
                    "@AmericanAir gate agent in Terminal C closed the door 20 minutes before departure while passengers were in line."
                ]
            },
            {
                "id": "refund_compensation_claims",
                "label": "Refund, voucher, or compensation claims",
                "description": "Customer requests a ticket refund, compensation for delays/cancellations, or clarification on travel credit/vouchers.",
                "examples": [
                    "@AmericanAir I submitted a refund request two weeks ago for a cancelled flight. What is the status of my refund?",
                    "@AmericanAir we were stuck overnight in Philadelphia due to mechanical delay. How do we claim hotel voucher compensation?",
                    "@AmericanAir my travel voucher code is showing as invalid when I try to apply it at checkout."
                ]
            },
            {
                "id": "frequent_flyer_loyalty",
                "label": "AAdvantage loyalty and miles",
                "description": "Customer asks about AAdvantage account balance, missing miles from past flights, loyalty status tiers, or partner airline points.",
                "examples": [
                    "@AmericanAir my miles for my flight last week to London haven't posted to my AAdvantage account yet.",
                    "@AmericanAir how many loyalty points do I need before the end of the month to maintain Platinum status?",
                    "@AmericanAir I want to redeem miles for an award ticket but the website is displaying an error code."
                ]
            },
            {
                "id": "booking_reservation_inquiry",
                "label": "New booking and general reservation inquiries",
                "description": "Customer has questions about booking policies, unaccompanied minors, pet travel policies, or payment methods on aa.com.",
                "examples": [
                    "@AmericanAir what is your current policy for traveling with a small dog in the cabin?",
                    "@AmericanAir can I hold a reservation for 24 hours before finalizing payment?",
                    "@AmericanAir I made a spelling typo in the first name on my ticket, how do I get it corrected?"
                ]
            },
            {
                "id": "customer_service_complaint",
                "label": "Staff behavior and service complaint",
                "description": "Customer expresses dissatisfaction with rude staff, phone hold times, lack of communication, or poor customer support experience.",
                "examples": [
                    "@AmericanAir been on hold on your customer service line for 2 and a half hours. This is completely unacceptable.",
                    "@AmericanAir your gate agent in Charlotte was extremely rude and unhelpful to passengers seeking information.",
                    "@AmericanAir worst customer service experience I have ever had. No one at the counter cared about our stranded group."
                ]
            },
            {
                "id": "safety_legal_escalation",
                "label": "Safety, security, or legal escalation",
                "description": "Customer reports a safety hazard, medical emergency, security issue, or threatens legal action against the airline (must escalate).",
                "examples": [
                    "@AmericanAir this is gross negligence and breach of contract. I am contacting the FAA and my attorney immediately.",
                    "@AmericanAir a passenger on flight AA302 is experiencing a medical emergency, emergency medical team needed at gate.",
                    "@AmericanAir serious safety violation witnessed with engine inspection before takeoff in Dallas."
                ]
            },
            {
                "id": "praise_feedback_gratitude",
                "label": "Praise, appreciation, and positive feedback",
                "description": "Customer thanks the airline, flight attendants, or pilots for exceptional service or a great travel experience.",
                "examples": [
                    "@AmericanAir huge shoutout to flight attendant Sarah on AA450 today for being so attentive and kind!",
                    "@AmericanAir smooth flight and arrived 20 minutes early into Chicago. Great job team!",
                    "@AmericanAir thank you for quickly helping us rebook our connection earlier today, very appreciated."
                ]
            },
            {
                "id": "other_unclear",
                "label": "Other or unclear inquiry",
                "description": "Inquiries that are ambiguous, unintelligible, brief greetings/pleasantries, or do not fit defined operational categories.",
                "examples": [
                    "@AmericanAir hello",
                    "@AmericanAir ???",
                    "@AmericanAir check this out"
                ]
            }
        ]
    }

    # Integrate real discovered cluster examples into the taxonomy
    for p in cluster_profiles:
        c_terms = " ".join(p["top_terms"]).lower()
        # Find matching intent
        matched_intent = None
        if any(t in c_terms for t in ["delay", "cancelled", "flight", "hours", "late", "cancelled"]):
            matched_intent = next((i for i in taxonomy["intents"] if i["id"] == "flight_delay_cancellation"), None)
        elif any(t in c_terms for t in ["bag", "luggage", "lost", "claim"]):
            matched_intent = next((i for i in taxonomy["intents"] if i["id"] == "baggage_luggage_issues"), None)
        elif any(t in c_terms for t in ["seat", "wifi", "cabin"]):
            matched_intent = next((i for i in taxonomy["intents"] if i["id"] == "seat_cabin_comfort"), None)
        elif any(t in c_terms for t in ["check", "app", "gate", "boarding"]):
            matched_intent = next((i for i in taxonomy["intents"] if i["id"] == "checkin_boarding_issues"), None)

        if matched_intent and len(p["top_examples"]) >= 2:
            # Augment with discovered real texts
            matched_intent["examples"] = (matched_intent["examples"][:1] + p["top_examples"][:2])

    # Save to data/intent_taxonomy.json
    output_path = DATA_DIR / "intent_taxonomy.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(taxonomy, f, indent=2)

    print(f"\nSuccessfully written taxonomy with {len(taxonomy['intents'])} intents to {output_path}")
    print("\n✅ Step 2.2 complete: 02_build_taxonomy.py finished successfully!")
    return taxonomy

if __name__ == "__main__":
    args = parse_args()
    build_taxonomy(
        brand_id=args.brand,
        sample_size=args.sample_size,
        seed=args.seed,
        k_min=args.k_min,
        k_max=args.k_max
    )
