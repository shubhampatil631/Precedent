import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from app.pipeline.classify import classify_intent
from app.pipeline.retrieve import retrieve_precedents
from app.pipeline.draft import draft_reply
from app.pipeline.route import route_decision

class AgentState(TypedDict):
    customer_text: str
    intent: Optional[str]
    confidence: Optional[float]
    raw_model_output: Optional[str]
    retrieved: Optional[List[Dict[str, Any]]]
    draft_reply: Optional[str]
    cited_thread_ids: Optional[List[str]]
    decision: Optional[str]
    reason: Optional[str]

def build_pipeline_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("classify", classify_intent)
    workflow.add_node("retrieve", retrieve_precedents)
    workflow.add_node("draft", draft_reply)
    workflow.add_node("route", route_decision)

    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "retrieve")
    workflow.add_edge("retrieve", "draft")
    workflow.add_edge("draft", "route")
    workflow.add_edge("route", END)

    return workflow.compile()

pipeline_app = build_pipeline_graph()

def run_agent_pipeline(customer_text: str) -> Dict[str, Any]:
    """
    Runs the full 4-node pipeline on a customer message and returns intermediate & final state.
    """
    initial_state = {
        "customer_text": customer_text,
        "intent": None,
        "confidence": None,
        "raw_model_output": None,
        "retrieved": None,
        "draft_reply": None,
        "cited_thread_ids": None,
        "decision": None,
        "reason": None
    }
    return pipeline_app.invoke(initial_state)

if __name__ == "__main__":
    import json

    test_queries = [
        "@AmericanAir my flight AA290 from DFW to ORD got cancelled and I have a connecting flight! What are my options?",
        "@AmericanAir landed in MIA but my checked bag didn't show up on carousel 4. Where do I file a claim?",
        "@AmericanAir someone made a severe safety threat on flight AA550! Call security immediately!",
        "How do I bake a chocolate cake with bananas and pineapples?"
    ]

    print("==================================================")
    print("Testing End-to-End LangGraph Support Agent Pipeline")
    print("==================================================")

    for q in test_queries:
        print(f"\n>>> Input Query: \"{q}\"")
        final_state = run_agent_pipeline(q)

        print(f"1. Classify Node: Intent='{final_state.get('intent')}', Confidence={final_state.get('confidence')}")
        print(f"2. Retrieve Node: Found {len(final_state.get('retrieved') or [])} precedents (Top Sim: {final_state.get('retrieved', [{}])[0].get('similarity') if final_state.get('retrieved') else 'N/A'})")
        print(f"3. Draft Node: Reply='{final_state.get('draft_reply')}' (Cited: {final_state.get('cited_thread_ids')})")
        print(f"4. Route Node: Decision='{final_state.get('decision')}', Reason='{final_state.get('reason')}'")
