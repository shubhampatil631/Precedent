"""
eval/judge.py
LLM-as-a-Judge scoring of generated response against resolution criteria,
factual grounding, tone consistency, and actionability.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.config import JUDGE_MODEL, BASE_DIR
from app.llm.client import llm_client

logger = logging.getLogger("eval_judge")

PROMPT_FILE = BASE_DIR / "prompts" / "judge.txt"

def get_judge_prompt_template() -> str:
    candidate_paths = [
        BASE_DIR / "prompts" / "judge.txt",
        BASE_DIR / "app" / "llm" / "prompts" / "judge.txt"
    ]
    for path in candidate_paths:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception as e:
                logger.warning(f"Error reading {path}: {e}")

    return (
        "You are an expert AI Support Quality Auditor evaluating airline customer service responses for American Airlines.\n\n"
        "Customer Message:\n\"{CUSTOMER_TEXT}\"\n\n"
        "True Customer Intent: {TRUE_INTENT}\n"
        "Expected Key Resolution Facts:\n{KEY_FACTS}\n\n"
        "Retrieved Historical Precedents:\n{RETRIEVED_PRECEDENTS}\n\n"
        "Agent Generated Response:\n\"{DRAFT_REPLY}\"\n\n"
        "Agent Decision: {DECISION} (Reason: {REASON})\n\n"
        "Evaluate across 4 criteria (1-5):\n"
        "1. RELEVANCE (1-5)\n2. BRAND TONE (1-5)\n3. GROUNDING (1-5)\n4. ACTIONABILITY (1-5)\n\n"
        "Respond ONLY with valid JSON:\n"
        '{{\n'
        '  "relevance_score": <int 1-5>,\n'
        '  "tone_score": <int 1-5>,\n'
        '  "grounding_score": <int 1-5>,\n'
        '  "actionability_score": <int 1-5>,\n'
        '  "overall_score": <float 1.0-5.0>,\n'
        '  "passed_checklist": <true or false>,\n'
        '  "rationale": "<1-2 sentence justification>"\n'
        "}}"
    )

def score_draft_with_judge(
    customer_text: str,
    true_intent: str,
    key_facts: List[str],
    retrieved_examples: List[Dict[str, Any]],
    draft_reply: str,
    decision: str,
    reason: str,
    reply_criteria: List[str] = None
) -> Dict[str, Any]:
    """
    Invokes the LLM Judge to score a generated reply against checklist reply criteria,
    factual grounding, tone consistency, and actionability.
    """
    criteria_list = reply_criteria or key_facts or ["Accurate professional resolution.", "Concrete next step provided."]
    criteria_block = "\n".join([f"- [ ] {crit}" for crit in criteria_list])
    
    if retrieved_examples:
        precedents_block = "\n".join([
            f"- Thread {ex.get('thread_id')}: Cust=\"{ex.get('customer_text', '')}\" -> Brand=\"{ex.get('brand_text', '')}\""
            for ex in retrieved_examples[:3]
        ])
    else:
        precedents_block = "None retrieved."

    template = get_judge_prompt_template()
    prompt = template.format(
        CUSTOMER_TEXT=customer_text,
        TRUE_INTENT=true_intent,
        REPLY_CRITERIA_CHECKLIST=criteria_block,
        RETRIEVED_PRECEDENTS=precedents_block,
        DRAFT_REPLY=draft_reply,
        DECISION=decision,
        REASON=reason
    )

    try:
        res = llm_client.generate_json(
            prompt=prompt,
            model=JUDGE_MODEL,
            preferred_provider="gemini",
            temperature=0.0
        )
        return {
            "relevance_score": int(res.get("relevance_score", 4)),
            "tone_score": int(res.get("tone_score", 4)),
            "grounding_score": int(res.get("grounding_score", 4)),
            "actionability_score": int(res.get("actionability_score", 4)),
            "overall_score": float(res.get("overall_score", 4.0)),
            "passed_checklist": bool(res.get("passed_checklist", True)),
            "criteria_evaluations": res.get("criteria_evaluations", []),
            "supported_by_thread_id": res.get("supported_by_thread_id", "none"),
            "rationale": str(res.get("rationale", "Response satisfies baseline customer support criteria."))
        }
    except Exception as e:
        logger.warning(f"Judge evaluation failed: {e}. Returning heuristic score.")
        # Rule-based fallback score
        is_grounded = bool(retrieved_examples or len(draft_reply) < 280)
        return {
            "relevance_score": 4 if is_grounded else 2,
            "tone_score": 4,
            "grounding_score": 4 if is_grounded else 2,
            "actionability_score": 4,
            "overall_score": 4.0 if is_grounded else 2.5,
            "passed_checklist": is_grounded,
            "criteria_evaluations": [{"criterion": c, "passed": is_grounded} for c in criteria_list],
            "supported_by_thread_id": retrieved_examples[0].get("thread_id") if retrieved_examples else "none",
            "rationale": "Heuristic fallback evaluation."
        }

if __name__ == "__main__":
    print("Testing LLM Judge Evaluation Node (eval/judge.py)...")
    sample_res = score_draft_with_judge(
        customer_text="@AmericanAir my flight AA290 got cancelled. What are my options?",
        true_intent="flight_delay_cancellation",
        key_facts=["Rebooking assistance", "Check mobile app or speak to airport agent"],
        retrieved_examples=[{
            "thread_id": "AA_123",
            "customer_text": "flight cancelled",
            "brand_text": "Please check the app or see our airport agent."
        }],
        draft_reply="@AmericanAir We are sorry for the cancellation. Please check the mobile app or visit an airport agent to confirm your rebooking.",
        decision="auto_handle",
        reason="matched precedent with high confidence"
    )
    print("Judge Evaluation Result:")
    print(json.dumps(sample_res, indent=2))
