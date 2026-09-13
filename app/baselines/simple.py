"""
Baseline 2: Simple Baseline (app/baselines/simple.py)
Logic:
- Scikit-learn TF-IDF Vectorizer (word + char n-grams).
- Logistic Regression intent classifier trained on grounding corpus & taxonomy examples.
- Nearest-neighbor TF-IDF retrieval for nearest historical brand resolution.
- Calibrated probability routing with safety intent escalation.
"""

import sys
import os
import json
import time
import pickle
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity

from app.config import (
    DATA_DIR,
    GROUNDING_DATA_DIR,
    MUST_ESCALATE_INTENTS,
    CONFIDENCE_THRESHOLD,
    SIMILARITY_FLOOR
)
from app.schemas import HandleMessageResponse, RetrievedExample

logger = logging.getLogger("simple_baseline")

MODEL_CACHE_PATH = DATA_DIR / "simple_baseline_model.pkl"

_SIMPLE_MODEL = None

class SimpleBaselineModel:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            sublinear_tf=True
        )
        self.classifier = LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            C=1.0
        )
        self.corpus_vectors = None
        self.corpus_records: List[Dict[str, Any]] = []
        self.classes_: List[str] = []

    def train(self, jsonl_path: Path, taxonomy_path: Path):
        texts = []
        labels = []
        records = []

        # 1. Load from grounding corpus
        if jsonl_path.exists():
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    cust = item.get("customer_text", "").strip()
                    intent = item.get("intent", "other_unclear")
                    if cust and intent:
                        texts.append(cust)
                        labels.append(intent)
                        records.append(item)

        # 2. Augment with taxonomy examples
        if taxonomy_path.exists():
            with open(taxonomy_path, "r", encoding="utf-8") as f:
                tax = json.load(f)
                for item in tax.get("intents", []):
                    intent_id = item["id"]
                    for ex in item.get("examples", []):
                        texts.append(ex)
                        labels.append(intent_id)
                        records.append({
                            "thread_id": f"tax_{intent_id}",
                            "customer_text": ex,
                            "brand_text": f"Thank you for contacting American Airlines regarding {item.get('label', intent_id)}. Please visit aa.com or contact our support team.",
                            "intent": intent_id
                        })

        if not texts:
            raise ValueError("No training data found to fit Simple Baseline model.")

        # Vectorize and train Logistic Regression
        X = self.vectorizer.fit_transform(texts)
        self.classifier.fit(X, labels)
        self.corpus_vectors = X
        self.corpus_records = records
        self.classes_ = list(self.classifier.classes_)

    def predict(self, query: str) -> Dict[str, Any]:
        q_vec = self.vectorizer.transform([query])

        # 1. Intent classification probabilities
        probs = self.classifier.predict_proba(q_vec)[0]
        max_idx = int(np.argmax(probs))
        pred_intent = self.classes_[max_idx]
        confidence = float(probs[max_idx])

        # 2. Nearest neighbor retrieval in TF-IDF space
        sims = cosine_similarity(q_vec, self.corpus_vectors)[0]
        top_k_indices = np.argsort(sims)[::-1][:3]

        retrieved: List[Dict[str, Any]] = []
        for idx in top_k_indices:
            rec = self.corpus_records[idx]
            sim = float(sims[idx])
            retrieved.append({
                "thread_id": rec.get("thread_id", f"rec_{idx}"),
                "customer_text": rec.get("customer_text", ""),
                "brand_text": rec.get("brand_text", ""),
                "similarity": round(sim, 4),
                "intent": rec.get("intent", "")
            })

        return {
            "intent": pred_intent,
            "confidence": round(confidence, 4),
            "retrieved": retrieved
        }

def get_simple_model() -> SimpleBaselineModel:
    global _SIMPLE_MODEL
    if _SIMPLE_MODEL is not None:
        return _SIMPLE_MODEL

    # Try loading from cache
    if MODEL_CACHE_PATH.exists():
        try:
            with open(MODEL_CACHE_PATH, "rb") as f:
                _SIMPLE_MODEL = pickle.load(f)
                return _SIMPLE_MODEL
        except Exception as e:
            logger.warning(f"Failed to load cached simple baseline model: {e}")

    # Otherwise train and cache
    model = SimpleBaselineModel()
    jsonl_path = GROUNDING_DATA_DIR / "resolved_threads.jsonl"
    tax_path = DATA_DIR / "intent_taxonomy.json"
    model.train(jsonl_path, tax_path)

    try:
        with open(MODEL_CACHE_PATH, "wb") as f:
            pickle.dump(model, f)
    except Exception as e:
        logger.warning(f"Failed to cache simple baseline model: {e}")

    _SIMPLE_MODEL = model
    return _SIMPLE_MODEL

def run_simple_baseline(customer_text: str) -> HandleMessageResponse:
    """
    Executes Simple Baseline on customer message.
    """
    t0 = time.perf_counter()
    model = get_simple_model()
    pred = model.predict(customer_text)

    intent = pred["intent"]
    confidence = pred["confidence"]
    retrieved_raw = pred["retrieved"]

    retrieved_examples = [
        RetrievedExample(
            thread_id=item["thread_id"],
            customer_text=item["customer_text"],
            brand_text=item["brand_text"],
            similarity=item["similarity"]
        )
        for item in retrieved_raw
    ]

    top_similarity = retrieved_raw[0]["similarity"] if retrieved_raw else 0.0

    # Nearest neighbor resolution text as canned reply
    if retrieved_raw and top_similarity >= 0.20:
        draft_reply = retrieved_raw[0]["brand_text"]
        cited_thread_ids = [retrieved_raw[0]["thread_id"]]
    else:
        draft_reply = "Thank you for contacting American Airlines. Our customer support team is reviewing your message."
        cited_thread_ids = []

    # Routing Decision
    if intent in MUST_ESCALATE_INTENTS:
        decision = "escalate"
        reason = "high-risk intent category"
        rule_fired = "Rule 1: High-Risk Category Escalation"
    elif confidence < 0.40:
        decision = "escalate"
        reason = f"low classification probability ({confidence:.2f} < 0.40)"
        rule_fired = f"Rule 2: Classification Probability Below 0.40 ({confidence:.2f})"
    elif top_similarity < 0.20:
        decision = "escalate"
        reason = f"no close historical match found (top sim: {top_similarity:.2f} < 0.20)"
        rule_fired = f"Rule 3: Nearest Neighbor Similarity Below 0.20 ({top_similarity:.2f})"
    else:
        decision = "auto_handle"
        reason = f"matched nearest historical precedent (sim: {top_similarity:.2f})"
        rule_fired = f"Rule 4: Nearest Precedent Auto-Handle ({top_similarity:.2f} ≥ 0.20)"

    latency_ms = (time.perf_counter() - t0) * 1000

    return HandleMessageResponse(
        intent=intent,
        confidence=confidence,
        retrieved=retrieved_examples,
        draft_reply=draft_reply,
        cited_thread_ids=cited_thread_ids,
        decision=decision,
        reason=reason,
        rule_fired=rule_fired,
        system_name="simple",
        latency_ms=round(latency_ms, 2),
        cost_estimate=0.0
    )

if __name__ == "__main__":
    test_queries = [
        "@AmericanAir my flight AA290 from DFW to ORD got cancelled and I have a connecting flight! What are my options?",
        "@AmericanAir landed in MIA but my checked bag didn't show up on carousel 4. Where do I file a claim?",
        "@AmericanAir a passenger made a bomb threat on flight AA550! Call security immediately!",
        "How do I bake a chocolate cake with bananas and pineapples?"
    ]

    print("==================================================")
    print("Testing Simple Baseline (app/baselines/simple.py)")
    print("==================================================")
    for q in test_queries:
        res = run_simple_baseline(q)
        print(f"\nQuery: \"{q}\"")
        print(f"Intent: {res.intent} (Conf: {res.confidence * 100:.1f}%) | Decision: {res.decision} ({res.reason})")
        print(f"Nearest Precedent Reply: \"{res.draft_reply}\"")
        print(f"Retrieved: {len(res.retrieved)} items (Top Sim: {res.retrieved[0].similarity if res.retrieved else 'N/A'})")
        print(f"Latency: {res.latency_ms} ms | Cost: ${res.cost_estimate}")
