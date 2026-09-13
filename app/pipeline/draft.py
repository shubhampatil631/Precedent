"""
Node 3: Response Drafting Grounded in Historical Precedent (app/pipeline/draft.py)
Input: { "customer_text": str, "intent": str, "retrieved": list[dict] }
Output: { "draft_reply": str, "cited_thread_ids": list[str] }
"""

import sys
import os
import json
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
    BRAND_AUTHOR_ID,
    BRAND_NAME,
    BRAND_TONE_DESCRIPTION,
    DRAFT_MODEL,
    DATA_DIR
)
from app.llm.client import llm_client

logger = logging.getLogger("draft_node")

PROMPT_FILE = PROJECT_ROOT / "prompts" / "draft.txt"
TAXONOMY_FILE = DATA_DIR / "intent_taxonomy.json"

_TAXONOMY_MAP = None

def load_taxonomy_map() -> Dict[str, Dict[str, str]]:
    """Loads taxonomy map {intent_id: {label, description}}."""
    global _TAXONOMY_MAP
    if _TAXONOMY_MAP is not None:
        return _TAXONOMY_MAP

    _TAXONOMY_MAP = {}
    if TAXONOMY_FILE.exists():
        try:
            with open(TAXONOMY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("intents", []):
                    _TAXONOMY_MAP[item["id"]] = {
                        "label": item.get("label", item["id"]),
                        "description": item.get("description", "")
                    }
        except Exception as e:
            logger.warning(f"Could not load taxonomy file: {e}")

    # Fallback defaults if not found
    if "other_unclear" not in _TAXONOMY_MAP:
        _TAXONOMY_MAP["other_unclear"] = {
            "label": "Other or unclear inquiry",
            "description": "General question, ambiguous statement, or customer comment not matching specific airline workflows."
        }
    return _TAXONOMY_MAP

def get_draft_prompt_template() -> str:
    """Reads draft prompt template from prompts/draft.txt or app/llm/prompts/draft.txt."""
    candidate_paths = [
        PROJECT_ROOT / "prompts" / "draft.txt",
        PROJECT_ROOT / "app" / "llm" / "prompts" / "draft.txt"
    ]
    for path in candidate_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception as e:
                logger.warning(f"Error reading {path}: {e}")

    # Fallback prompt template
    return (
        "You are a support agent for {BRAND}. Match this tone: {TONE_DESCRIPTION}\n"
        "Customer intent: {INTENT_LABEL} - {INTENT_DESCRIPTION}\n\n"
        "Here is how similar issues were resolved before:\n"
        "{RETRIEVED_EXAMPLES}\n\n"
        "Customer's message: {CUSTOMER_TEXT}\n\n"
        "Write a short (<280 char), specific reply. Reference a concrete next step or resolution "
        "drawn from the examples above. If none of the examples actually apply, say so plainly instead of inventing a policy.\n\n"
        "Respond ONLY with a JSON object with keys 'draft_reply' and 'cited_thread_ids'. Example schema:\n"
        '{{\n'
        '  "draft_reply": "Write the actual tweet response here under 280 characters",\n'
        '  "cited_thread_ids": ["AmericanAir_12345"]\n'
        "}}"
    )

def format_retrieved_examples(retrieved: List[Dict[str, Any]]) -> str:
    """Formats retrieved resolution precedents for prompt injection."""
    if not retrieved:
        return "None found. No historical resolution examples matched this inquiry."

    lines = []
    for idx, item in enumerate(retrieved, start=1):
        thread_id = item.get("thread_id", f"example_{idx}")
        cust = item.get("customer_text", "").strip()
        brand = item.get("brand_text", "").strip()
        sim = item.get("similarity", 0.0)

        lines.append(
            f"Example {idx} [Thread ID: {thread_id}, Similarity: {sim:.2f}]:\n"
            f"  Customer: \"{cust}\"\n"
            f"  Resolution: \"{brand}\""
        )
    return "\n\n".join(lines)

def draft_reply(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Drafts a grounded brand response based on customer text, intent, and retrieved precedents.
    
    Input: { "customer_text": str, "intent": str, "retrieved": list[dict] }
    Output: { "draft_reply": str, "cited_thread_ids": list[str] }
    """
    customer_text = state.get("customer_text", "").strip()
    intent_id = state.get("intent", "other_unclear")
    retrieved = state.get("retrieved", [])

    if not customer_text:
        return {
            "draft_reply": f"Hello! How can we assist you with your travels today?",
            "cited_thread_ids": []
        }

    # 1. Resolve intent metadata
    tax_map = load_taxonomy_map()
    intent_info = tax_map.get(intent_id, {
        "label": intent_id.replace("_", " ").title(),
        "description": "Customer support inquiry."
    })

    # 2. Format retrieved precedents
    retrieved_block = format_retrieved_examples(retrieved)
    valid_thread_ids = {item.get("thread_id") for item in retrieved if item.get("thread_id")}

    # 3. Build prompt
    template = get_draft_prompt_template()
    prompt = template.format(
        BRAND=f"@{BRAND_AUTHOR_ID} ({BRAND_NAME})",
        TONE_DESCRIPTION=BRAND_TONE_DESCRIPTION,
        INTENT_LABEL=intent_info["label"],
        INTENT_DESCRIPTION=intent_info["description"],
        RETRIEVED_EXAMPLES=retrieved_block,
        CUSTOMER_TEXT=customer_text
    )

    system_prompt = (
        f"You are the official Twitter/X customer support assistant for @{BRAND_AUTHOR_ID}. "
        "Your responses must be grounded strictly in historical brand precedents, professional, empathetic, "
        "concise (<280 characters), and include concrete action steps. Output strictly valid JSON."
    )

    # 4. Generate draft using high-capability model
    try:
        full_prompt = f"{system_prompt}\n\n{prompt}"
        response_data = llm_client.generate_json(
            prompt=full_prompt,
            model=DRAFT_MODEL,
            temperature=0.3
        )

        draft_text = str(response_data.get("draft_reply", "")).strip()
        cited_ids_raw = response_data.get("cited_thread_ids", [])
        if isinstance(cited_ids_raw, str):
            cited_ids_raw = [cited_ids_raw]
        elif not isinstance(cited_ids_raw, list):
            cited_ids_raw = []

        # Filter cited thread IDs to those that exist in retrieved list
        cited_thread_ids = [tid for tid in cited_ids_raw if tid in valid_thread_ids]

        # If LLM didn't cite any IDs but we provided retrieved precedents, cite top-1
        if not cited_thread_ids and retrieved:
            top_id = retrieved[0].get("thread_id")
            if top_id:
                cited_thread_ids.append(top_id)

        # Enforce character count constraint (<280 chars)
        if len(draft_text) > 280:
            logger.warning(f"Draft reply exceeded 280 chars ({len(draft_text)}). Truncating gracefully.")
            # Trim at last sentence punctuation before 280 chars
            truncated = draft_text[:277]
            last_punct = max(truncated.rfind("."), truncated.rfind("!"), truncated.rfind("?"))
            if last_punct > 150:
                draft_text = truncated[:last_punct + 1]
            else:
                draft_text = truncated + "..."

        if not draft_text:
            draft_text = f"Thanks for contacting @{BRAND_AUTHOR_ID}. Please let us know your confirmation code so our team can assist."

        return {
            "draft_reply": draft_text,
            "cited_thread_ids": cited_thread_ids
        }

    except Exception as e:
        logger.error(f"Draft generation failed: {e}")
        # Rule-based fallback
        fallback_reply = (
            f"Thanks for reaching out to @{BRAND_AUTHOR_ID}. "
            "Our support team is reviewing your inquiry to assist you shortly."
        )
        return {
            "draft_reply": fallback_reply,
            "cited_thread_ids": []
        }

if __name__ == "__main__":
    # Standalone verification tests
    test_cases = [
        {
            "desc": "Cancelled flight rebooking with retrieved precedent",
            "state": {
                "customer_text": "@AmericanAir my flight AA290 from DFW to ORD got cancelled and I have a connecting flight! What are my options?",
                "intent": "flight_delay_cancellation",
                "retrieved": [
                    {
                        "thread_id": "AmericanAir_2637184",
                        "customer_text": "@AmericanAir my flight was cancelled 2 twice today!! Oppose to departing D R at 3:50p we now depart at 5:41p. Flight #1966.",
                        "brand_text": "@744338 Our agents will hold space as long as operationally possible. Check the mobile app or see an airport agent to confirm rebooking.",
                        "similarity": 0.68,
                        "intent": "flight_delay_cancellation"
                    }
                ]
            }
        },
        {
            "desc": "Lost baggage claim inquiry with retrieved precedent",
            "state": {
                "customer_text": "@AmericanAir landed in MIA but my checked bag didn't show up on carousel 4. Where do I file a claim?",
                "intent": "baggage_luggage_issues",
                "retrieved": [
                    {
                        "thread_id": "AmericanAir_400052",
                        "customer_text": ".@AmericanAir please find my bag. Scanned at claim, what gives?",
                        "brand_text": "Please file a report with our Baggage Service Office at the airport ASAP or visit aa.com/baggage to submit a claim.",
                        "similarity": 0.58,
                        "intent": "baggage_luggage_issues"
                    }
                ]
            }
        },
        {
            "desc": "No retrieved precedents (empty list)",
            "state": {
                "customer_text": "How do I bake a chocolate cake with bananas and pineapples?",
                "intent": "other_unclear",
                "retrieved": []
            }
        }
    ]

    print("==================================================")
    print("Testing Standalone Response Drafting Node (draft.py)")
    print("==================================================")

    for tc in test_cases:
        print(f"\n--- Test: {tc['desc']} ---")
        print(f"Customer Input: \"{tc['state']['customer_text']}\"")
        print(f"Intent: {tc['state']['intent']}")
        print(f"Retrieved Precedents Count: {len(tc['state']['retrieved'])}")

        result = draft_reply(tc["state"])
        reply = result.get("draft_reply", "")
        cited = result.get("cited_thread_ids", [])

        print(f"Draft Reply ({len(reply)} chars):")
        print(f"  \"{reply}\"")
        print(f"Cited Thread IDs: {cited}")
        print(f"Length Check: {'PASS (<280)' if len(reply) <= 280 else 'FAIL (>280)'}")

    print("\n==================================================")
    print("Draft Node Test Complete!")
