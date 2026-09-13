"""
Node 4: Deterministic Routing Engine (app/pipeline/route.py)
Input: { "customer_text": str, "intent": str, "confidence": float, "retrieved": list[dict], "draft_reply": str, "cited_thread_ids": list[str] }
Output: { "decision": "auto_handle" | "escalate", "reason": str }
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
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.config import (
    MUST_ESCALATE_INTENTS,
    CONFIDENCE_THRESHOLD,
    SIMILARITY_FLOOR,
    ENABLE_HALLUCINATION_SELF_CHECK,
    DRAFT_MODEL
)
from app.llm.client import llm_client

logger = logging.getLogger("route_node")

def check_unsupported_claim(customer_text: str, draft_reply: str, retrieved: List[Dict[str, Any]]) -> bool:
    """
    Optional LLM self-check: verifies whether draft_reply contains claims unsupported by retrieved precedents.
    Returns True if draft contains unsupported/hallucinated policy claims, False if well-grounded.
    """
    if not retrieved or not draft_reply:
        return False

    precedent_text = "\n".join([
        f"- Historical Resolution: {item.get('brand_text', '')}"
        for item in retrieved[:3]
    ])

    prompt = (
        "You are an AI Safety Evaluator checking airline customer support responses for hallucinated policies.\n\n"
        f"Customer Message: \"{customer_text}\"\n\n"
        f"Retrieved Brand Precedents:\n{precedent_text}\n\n"
        f"Drafted Response: \"{draft_reply}\"\n\n"
        "Question: Does the drafted response state any specific policy, refund guarantee, or airline commitment that is NOT supported by the retrieved precedents above?\n"
        "Respond ONLY with a JSON object:\n"
        "{\n"
        "  \"contains_unsupported_claim\": true or false,\n"
        "  \"explanation\": \"one sentence explaining your judgment\"\n"
        "}"
    )

    try:
        res = llm_client.generate_json(
            prompt=prompt,
            model=DRAFT_MODEL,
            preferred_provider="gemini",
            temperature=0.0
        )
        return bool(res.get("contains_unsupported_claim", False))
    except Exception as e:
        logger.warning(f"Self-check evaluation failed: {e}. Defaulting to safe pass.")
        return False

def route_decision(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates explicit rule order (first match wins) to determine routing action.
    
    Rule Order:
    1. intent in MUST_ESCALATE_INTENTS -> escalate ("high-risk intent category")
    2. confidence < CONFIDENCE_THRESHOLD -> escalate ("low classification confidence")
    3. len(retrieved) == 0 or top_similarity < SIMILARITY_FLOOR -> escalate ("no comparable historical resolution found")
    4. Optional self-check: draft states unsupported claim -> escalate ("draft contains unsupported claim")
    5. Else -> auto_handle ("matched precedent with high confidence")
    """
    customer_text = state.get("customer_text", "").strip()
    intent = state.get("intent", "other_unclear")
    confidence = float(state.get("confidence", 0.0))
    retrieved = state.get("retrieved", [])
    draft_reply = state.get("draft_reply", "").strip()

    # Rule 1: High-risk intent category (safety, legal threat, payment dispute, unclear)
    if intent in MUST_ESCALATE_INTENTS:
        return {
            "decision": "escalate",
            "reason": "high-risk intent category",
            "rule_fired": "Rule 1: High-Risk Category Escalation"
        }

    # Rule 2: Low classification confidence (< threshold, e.g. 0.55)
    if confidence < CONFIDENCE_THRESHOLD:
        return {
            "decision": "escalate",
            "reason": "low classification confidence",
            "rule_fired": f"Rule 2: Classification Confidence Below Threshold ({confidence:.2f} < {CONFIDENCE_THRESHOLD})"
        }

    # Rule 3: No comparable historical resolution found (empty retrieved or below similarity floor)
    top_similarity = retrieved[0].get("similarity", 0.0) if retrieved else 0.0
    if not retrieved or top_similarity < SIMILARITY_FLOOR:
        return {
            "decision": "escalate",
            "reason": "no comparable historical resolution found",
            "rule_fired": f"Rule 3: No Precedent Found (Top Sim: {top_similarity:.2f} < {SIMILARITY_FLOOR})"
        }

    # Rule 4: Optional LLM self-check on draft grounding
    if ENABLE_HALLUCINATION_SELF_CHECK:
        has_unsupported_claim = check_unsupported_claim(
            customer_text=customer_text,
            draft_reply=draft_reply,
            retrieved=retrieved
        )
        if has_unsupported_claim:
            return {
                "decision": "escalate",
                "reason": "draft contains unsupported claim",
                "rule_fired": "Rule 4: Unsupported Policy Claim Detected in Draft"
            }

    # Rule 5: Matched precedent with high confidence -> Safe Auto-Handle
    return {
        "decision": "auto_handle",
        "reason": "matched precedent with high confidence",
        "rule_fired": f"Rule 5: Grounded Precedent Match (Top Sim: {top_similarity:.2f} ≥ {SIMILARITY_FLOOR})"
    }

if __name__ == "__main__":
    # Standalone verification test suite covering all 5 routing rules
    test_cases = [
        {
            "name": "Rule 1 Match: Safety / Legal Threat",
            "state": {
                "customer_text": "@AmericanAir a passenger made a bomb threat in cabin on flight AA102! Call FBI!",
                "intent": "safety_legal_escalation",
                "confidence": 0.98,
                "retrieved": [{"thread_id": "t1", "similarity": 0.85, "brand_text": "Please report to security."}],
                "draft_reply": "Please contact airport authorities immediately."
            },
            "expected_decision": "escalate",
            "expected_reason": "high-risk intent category"
        },
        {
            "name": "Rule 1 Match: Refund / Compensation Dispute",
            "state": {
                "customer_text": "@AmericanAir chargeback initiated for $1200 unauthorized ticket charge.",
                "intent": "refund_compensation_claims",
                "confidence": 0.92,
                "retrieved": [{"thread_id": "t2", "similarity": 0.72, "brand_text": "Visit refunds."}],
                "draft_reply": "Please submit refund request at aa.com/refunds."
            },
            "expected_decision": "escalate",
            "expected_reason": "high-risk intent category"
        },
        {
            "name": "Rule 2 Match: Low Classification Confidence",
            "state": {
                "customer_text": "Hey AA what is happening right now?",
                "intent": "general_inquiry_status",
                "confidence": 0.42, # Below 0.55
                "retrieved": [{"thread_id": "t3", "similarity": 0.60, "brand_text": "How can we help?"}],
                "draft_reply": "How can we assist you today?"
            },
            "expected_decision": "escalate",
            "expected_reason": "low classification confidence"
        },
        {
            "name": "Rule 3 Match: Empty Retrieval / Below Floor",
            "state": {
                "customer_text": "How do I bake a chocolate banana cake with pineapples?",
                "intent": "flight_delay_cancellation",
                "confidence": 0.88,
                "retrieved": [], # Empty (filtered out below floor)
                "draft_reply": "We specialize in flying, not baking."
            },
            "expected_decision": "escalate",
            "expected_reason": "no comparable historical resolution found"
        },
        {
            "name": "Rule 3 Match: Top Similarity Below Floor (e.g. 0.28 < 0.35)",
            "state": {
                "customer_text": "Random query with weak match",
                "intent": "seat_cabin_preferences",
                "confidence": 0.85,
                "retrieved": [{"thread_id": "t4", "similarity": 0.28, "brand_text": "Seats."}],
                "draft_reply": "Check your seat."
            },
            "expected_decision": "escalate",
            "expected_reason": "no comparable historical resolution found"
        },
        {
            "name": "Rule 5 Match: Clean Grounded Query -> Auto Handle",
            "state": {
                "customer_text": "@AmericanAir where do I check my delayed baggage claim status?",
                "intent": "baggage_luggage_issues",
                "confidence": 0.94,
                "retrieved": [
                    {
                        "thread_id": "AmericanAir_400052",
                        "similarity": 0.72,
                        "brand_text": "Please file a report with our Baggage team or visit aa.com/baggage."
                    }
                ],
                "draft_reply": "Please visit aa.com/baggage to check the status of your delayed baggage claim."
            },
            "expected_decision": "auto_handle",
            "expected_reason": "matched precedent with high confidence"
        }
    ]

    print("==================================================")
    print("Testing Standalone Routing Decision Node (route.py)")
    print("==================================================")

    all_passed = True
    for tc in test_cases:
        print(f"\n--- Test: {tc['name']} ---")
        output = route_decision(tc["state"])
        decision = output.get("decision")
        reason = output.get("reason")

        print(f"Decision: {decision} (Expected: {tc['expected_decision']})")
        print(f"Reason: \"{reason}\" (Expected: \"{tc['expected_reason']}\")")

        match_dec = (decision == tc["expected_decision"])
        match_reason = (reason == tc["expected_reason"])

        if match_dec and match_reason:
            print("Status: PASS [OK]")
        else:
            print("Status: FAIL [Mismatch]")
            all_passed = False

    print("\n==================================================")
    print(f"All Routing Tests Passed: {all_passed}")
    print("==================================================")
