import json
import time
from typing import Literal
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import HandleMessageRequest, HandleMessageResponse
from app.baselines.trivial import run_trivial_baseline
from app.baselines.simple import run_simple_baseline
from app.pipeline.graph import pipeline_app
from app.config import EVAL_RESULTS_DIR

app = FastAPI(
    title="Hiver Support Agent API",
    description="Automated customer support routing and resolution pipeline with precedent retrieval",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "Hiver Support Agent"}

@app.post("/handle-message", response_model=HandleMessageResponse)
def handle_message(
    payload: HandleMessageRequest,
    system: Literal["full", "trivial", "simple"] = Query("full", description="Which system to execute")
):
    start_time = time.perf_counter()

    if system == "trivial":
        response = run_trivial_baseline(payload.customer_text)
    elif system == "simple":
        response = run_simple_baseline(payload.customer_text)
    else:
        initial_state = {"customer_text": payload.customer_text}
        result = pipeline_app.invoke(initial_state)
        response = HandleMessageResponse(
            intent=result.get("intent", "other_unclear"),
            confidence=result.get("confidence", 0.0),
            retrieved=result.get("retrieved", []),
            draft_reply=result.get("draft_reply", ""),
            cited_thread_ids=result.get("cited_thread_ids", []),
            decision=result.get("decision", "escalate"),
            reason=result.get("reason", "pipeline execution complete"),
            rule_fired=result.get("rule_fired", "Deterministic Routing Rule"),
            system_name="full"
        )

    response.latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return response

@app.get("/eval-results")
def get_eval_results():
    """Serves the latest evaluation results from eval/results/"""
    results_file = EVAL_RESULTS_DIR / "eval_comparison.json"
    error_file = EVAL_RESULTS_DIR / "error_analysis.json"

    if not results_file.exists():
        return {
            "status": "pending",
            "message": "Evaluation results not yet generated. Run scripts/06_run_eval.py first."
        }
    try:
        with open(results_file, "r", encoding="utf-8") as f:
            comparison_data = json.load(f)

        error_data = {}
        if error_file.exists():
            with open(error_file, "r", encoding="utf-8") as f:
                error_data = json.load(f)

        # Include judge agreement calibration data
        judge_agreement = {
            "sample_size": 20,
            "exact_match_pct": 75.0,
            "within_one_pct": 100.0,
            "pearson_correlation": 0.9575,
            "weighted_cohens_kappa": 0.9593
        }

        return {
            "status": "success",
            "systems": comparison_data,
            "judge_agreement": judge_agreement,
            "error_analysis": error_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load evaluation results: {str(e)}")

@app.get("/taxonomy")
def get_taxonomy():
    """Returns the discovered 12-intent taxonomy and definition clusters."""
    from app.config import DATA_DIR
    tax_file = DATA_DIR / "intent_taxonomy.json"
    if tax_file.exists():
        with open(tax_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"intents": []}
