"""
Node 1: Intent Classification (app/pipeline/classify.py)
Input: { "customer_text": str }
Output: { "intent": str, "confidence": float, "raw_model_output": str }
"""

import sys
import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import (
    DATA_DIR,
    BRAND_NAME,
    CLASSIFY_MODEL,
    BASE_DIR
)
from app.llm.client import llm_client

logger = logging.getLogger("classify_node")

_TAXONOMY_DATA = None
_PROMPT_TEMPLATE = None

def load_taxonomy() -> Dict[str, Any]:
    global _TAXONOMY_DATA
    if _TAXONOMY_DATA is None:
        taxonomy_file = DATA_DIR / "intent_taxonomy.json"
        if taxonomy_file.exists():
            with open(taxonomy_file, "r", encoding="utf-8") as f:
                _TAXONOMY_DATA = json.load(f)
        else:
            _TAXONOMY_DATA = {"intents": []}
    return _TAXONOMY_DATA

def load_prompt_template() -> str:
    global _PROMPT_TEMPLATE
    if _PROMPT_TEMPLATE is None:
        candidate_paths = [
            BASE_DIR / "app" / "llm" / "prompts" / "classify.txt",
            BASE_DIR / "prompts" / "classify.txt"
        ]
        for p in candidate_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        _PROMPT_TEMPLATE = f.read()
                        break
                except Exception as e:
                    logger.warning(f"Error reading {p}: {e}")
        if _PROMPT_TEMPLATE is None:
            _PROMPT_TEMPLATE = (
                "You are an intent classifier for {BRAND_NAME}. "
                "Classify the customer message into one of:\n{TAXONOMY_DEFINITIONS}\n\n"
                "Examples:\n{FEW_SHOT_EXAMPLES}\n\n"
                "Customer Message: \"{CUSTOMER_TEXT}\"\n\n"
                "Respond in JSON with 'intent' and 'confidence'."
            )
    return _PROMPT_TEMPLATE

def build_classify_prompt(customer_text: str) -> str:
    taxonomy = load_taxonomy()
    intents = taxonomy.get("intents", [])

    definitions_lines = []
    few_shot_lines = []

    for intent in intents:
        i_id = intent["id"]
        label = intent.get("label", i_id)
        desc = intent.get("description", "")
        definitions_lines.append(f"- **{i_id}** ({label}): {desc}")

        examples = intent.get("examples", [])
        if examples:
            for ex in examples[:2]:  # 1-2 few shots per intent
                few_shot_lines.append(f"Customer: \"{ex}\" -> {{\"intent\": \"{i_id}\", \"confidence\": 0.95}}")

    taxonomy_str = "\n".join(definitions_lines)
    few_shots_str = "\n".join(few_shot_lines)

    template = load_prompt_template()
    prompt = template.format(
        BRAND_NAME=BRAND_NAME,
        TAXONOMY_DEFINITIONS=taxonomy_str,
        FEW_SHOT_EXAMPLES=few_shots_str,
        CUSTOMER_TEXT=customer_text
    )
    return prompt

def classify_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classifies customer message into one of the canonical taxonomy intents with a confidence estimate.
    
    Input: state containing 'customer_text'
    Output: dict with 'intent', 'confidence', 'raw_model_output'
    """
    customer_text = state.get("customer_text", "").strip()
    if not customer_text:
        return {
            "intent": "other_unclear",
            "confidence": 0.0,
            "raw_model_output": "{\"intent\": \"other_unclear\", \"confidence\": 0.0}"
        }

    prompt = build_classify_prompt(customer_text)
    taxonomy = load_taxonomy()
    valid_intent_ids = {i["id"] for i in taxonomy.get("intents", [])}

    try:
        parsed_json = llm_client.generate_json(
            prompt=prompt,
            model=CLASSIFY_MODEL,
            temperature=0.1
        )
        raw_output = json.dumps(parsed_json)

        intent = str(parsed_json.get("intent", "other_unclear")).strip().lower()
        confidence = float(parsed_json.get("confidence", 0.75))
        confidence = max(0.0, min(1.0, confidence))

        if intent not in valid_intent_ids:
            matched = False
            for valid_id in valid_intent_ids:
                if intent in valid_id or valid_id in intent:
                    intent = valid_id
                    matched = True
                    break
            if not matched:
                intent = "other_unclear"
                confidence = min(confidence, 0.40)

        return {
            "intent": intent,
            "confidence": round(confidence, 3),
            "raw_model_output": raw_output
        }

    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return {
            "intent": "other_unclear",
            "confidence": 0.0,
            "raw_model_output": str(e)
        }

if __name__ == "__main__":
    test_queries = [
        ("Flight AA102 from JFK to LAX was delayed 4 hours, what about my connection?", "flight_delay_cancellation"),
        ("My luggage was destroyed and lost in Chicago airport!", "baggage_luggage_issues"),
        ("Can I switch my ticket to next Friday morning?", "rebooking_ticket_changes"),
        ("Why did you move my seat away from my daughter?", "seat_cabin_comfort"),
        ("The American Airlines app is crashing when I try to check in", "checkin_boarding_issues"),
        ("Where is my $400 ticket refund from last month?", "refund_compensation_claims"),
        ("How many AAdvantage miles do I need for a free ticket to Hawaii?", "frequent_flyer_loyalty"),
        ("What is your pet cabin travel fee and requirements?", "booking_reservation_inquiry"),
        ("Your gate agent was extremely rude and dismissive to everyone", "customer_service_complaint"),
        ("This is dangerous and illegal, I am suing you and contacting the FAA", "safety_legal_escalation"),
        ("Thank you Sarah and Captain Dave for an amazing flight!", "praise_feedback_gratitude"),
        ("hello???", "other_unclear")
    ]

    print("==================================================")
    print("Testing Standalone Intent Classification Node")
    print("==================================================")

    correct_count = 0
    for query, expected_intent in test_queries:
        result = classify_intent({"customer_text": query})
        is_match = (result["intent"] == expected_intent)
        if is_match:
            correct_count += 1
        status_str = "MATCH" if is_match else "MISMATCH"
        print(f"\nQuery: \"{query}\"")
        print(f"  Predicted: {result['intent']} (Conf: {result['confidence'] * 100:.1f}%) | Expected: {expected_intent} -> [{status_str}]")

    print("\n" + "="*50)
    print(f"Classification Node Test Score: {correct_count} / {len(test_queries)} ({correct_count/len(test_queries)*100:.1f}%)")
    print("="*50)
