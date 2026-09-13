"""
Baseline 1: Trivial Baseline (app/baselines/trivial.py)
Logic:
- Simple dictionary of canned responses per keyword match.
- Keyword escalation rules for safety, legal, and payment disputes.
- Fixed latency / zero LLM API cost.
"""

import sys
import time
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas import HandleMessageResponse, RetrievedExample

KEYWORD_INTENT_MAP = {
    "delay": ("flight_delay_cancellation", "We're sorry for the flight delay. Please check the American Airlines app or speak to an agent for update status."),
    "cancel": ("flight_delay_cancellation", "We apologize for the cancellation. Please visit an airport customer service desk or use the app to select a new flight."),
    "bag": ("baggage_luggage_issues", "We apologize for the baggage issue. Please file a claim with our Baggage Service Office or online at aa.com/baggage."),
    "luggage": ("baggage_luggage_issues", "Please visit our Baggage Service Office at the airport or file a report at aa.com/baggage."),
    "seat": ("seat_cabin_preferences", "You can manage seat selection and upgrades directly in the American Airlines app or at aa.com."),
    "wifi": ("inflight_experience_amenities", "High-speed Wi-Fi is available on select flights. Connect to 'aainflight.com' once onboard."),
    "food": ("inflight_experience_amenities", "Complimentary snacks and non-alcoholic drinks are served on flights over 250 miles."),
    "check in": ("checkin_boarding_process", "Online check-in opens 24 hours prior to departure on aa.com or through the mobile app."),
    "boarding": ("checkin_boarding_process", "Please be at the gate 30 minutes before domestic flights and 45 minutes before international flights."),
    "miles": ("loyalty_aadvantage_inquiries", "You can check your AAdvantage miles balance and award travel options at aa.com/aadvantage."),
    "praise": ("compliments_positive_feedback", "Thank you so much for the kind words! We love having you onboard. Safe travels!"),
    "great": ("compliments_positive_feedback", "Thank you for the wonderful feedback! We appreciate your loyalty and look forward to flying with you again.")
}

ESCALATION_KEYWORDS = [
    "sue", "lawyer", "attorney", "legal", "court",
    "police", "fbi", "security", "threat", "bomb", "emergency", "assault",
    "refund", "chargeback", "credit card", "dispute", "stolen", "dot complaint"
]

def run_trivial_baseline(customer_text: str) -> HandleMessageResponse:
    t0 = time.perf_counter()
    text_lower = customer_text.lower()

    # 1. Check for escalation keywords
    for kw in ESCALATION_KEYWORDS:
        if kw in text_lower:
            latency_ms = (time.perf_counter() - t0) * 1000
            return HandleMessageResponse(
                intent="safety_legal_escalation" if any(k in kw for k in ["sue", "lawyer", "threat", "bomb", "police"]) else "refund_compensation_claims",
                confidence=0.90,
                retrieved=[],
                draft_reply="Thanks for contacting us. A dedicated customer relations specialist will review your case and contact you directly.",
                cited_thread_ids=[],
                decision="escalate",
                reason=f"keyword heuristic matched high-risk term ('{kw}')",
                rule_fired=f"Keyword Escalation Rule ('{kw}')",
                system_name="trivial",
                latency_ms=round(latency_ms, 2),
                cost_estimate=0.0
            )

    # 2. Check keyword mapping for intent and canned reply
    for kw, (intent_id, canned_text) in KEYWORD_INTENT_MAP.items():
        if kw in text_lower:
            latency_ms = (time.perf_counter() - t0) * 1000
            return HandleMessageResponse(
                intent=intent_id,
                confidence=0.70,
                retrieved=[],
                draft_reply=canned_text,
                cited_thread_ids=[],
                decision="auto_handle",
                reason=f"keyword heuristic matched '{kw}'",
                rule_fired=f"Keyword Intent Match ('{kw}')",
                system_name="trivial",
                latency_ms=round(latency_ms, 2),
                cost_estimate=0.0
            )

    # 3. Default fallback
    latency_ms = (time.perf_counter() - t0) * 1000
    return HandleMessageResponse(
        intent="other_unclear",
        confidence=0.30,
        retrieved=[],
        draft_reply="Thanks for reaching out to American Airlines. How can we assist with your travel today?",
        cited_thread_ids=[],
        decision="escalate",
        reason="no matching keyword heuristic found",
        rule_fired="Fallback Keyword Rule (No keyword match)",
        system_name="trivial",
        latency_ms=round(latency_ms, 2),
        cost_estimate=0.0
    )

if __name__ == "__main__":
    test_queries = [
        "@AmericanAir my flight was delayed 3 hours, will I make my connection?",
        "@AmericanAir bag missing on carousel 2 at ORD",
        "@AmericanAir I will sue your airline in court for this!",
        "Random gibberish text here"
    ]

    print("==================================================")
    print("Testing Trivial Baseline (app/baselines/trivial.py)")
    print("==================================================")
    for q in test_queries:
        res = run_trivial_baseline(q)
        print(f"\nQuery: \"{q}\"")
        print(f"Intent: {res.intent} (Conf: {res.confidence}) | Decision: {res.decision} ({res.reason})")
        print(f"Draft Reply: \"{res.draft_reply}\"")
        print(f"Latency: {res.latency_ms} ms | Cost: ${res.cost_estimate}")
