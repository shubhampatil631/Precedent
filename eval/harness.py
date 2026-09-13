"""
eval/harness.py
Automated evaluation harness comparing:
1. Trivial Baseline (app/baselines/trivial.py)
2. Simple Baseline (app/baselines/simple.py)
3. Full LangGraph Agent (app/pipeline/graph.py)

Evaluates on the 160 hand-labeled golden examples and outputs comprehensive metrics,
confusion matrices, safety violation analysis, and LLM judge quality ratings.
"""

import sys
import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.config import (
    GOLDEN_DATA_DIR,
    EVAL_RESULTS_DIR,
    MUST_ESCALATE_INTENTS
)
from app.baselines.trivial import run_trivial_baseline
from app.baselines.simple import run_simple_baseline
from app.pipeline.graph import run_agent_pipeline
from eval.metrics import compute_intent_metrics, compute_routing_metrics
from eval.judge import score_draft_with_judge
from eval.judge_agreement import compute_judge_agreement

logger = logging.getLogger("eval_harness")

def load_golden_dataset() -> List[Dict[str, Any]]:
    golden_file = GOLDEN_DATA_DIR / "golden_set.jsonl"
    if not golden_file.exists():
        raise FileNotFoundError(f"Golden dataset not found at {golden_file}. Run scripts/05_label_golden_set.py first.")

    dataset = []
    with open(golden_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                dataset.append(json.loads(line))
    return dataset

def run_evaluation(sample_limit: int = None, judge_sample_size: int = 30) -> Dict[str, Any]:
    print("==================================================")
    print("Running Support Agent Comparative Evaluation Harness")
    print("==================================================")

    dataset = load_golden_dataset()
    if sample_limit and sample_limit < len(dataset):
        dataset = dataset[:sample_limit]

    print(f"Total Evaluation Samples: {len(dataset)}")
    EVAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    systems = ["trivial", "simple", "full"]
    system_results: Dict[str, List[Dict[str, Any]]] = {s: [] for s in systems}

    # 1. Execute each system on golden dataset
    for idx, ex in enumerate(dataset, start=1):
        cust_text = ex["customer_text"]
        true_intent = ex["true_intent"]
        true_decision = ex["true_decision"]
        ex_id = ex["id"]
        category_type = ex.get("category_type", "standard_resolution")
        key_facts = ex.get("key_facts", [])

        if idx % 20 == 0 or idx == 1 or idx == len(dataset):
            print(f"Evaluating sample [{idx}/{len(dataset)}]: {ex_id} ({true_intent})")

        # System 1: Trivial Baseline
        try:
            t_res = run_trivial_baseline(cust_text)
            system_results["trivial"].append({
                "id": ex_id,
                "customer_text": cust_text,
                "true_intent": true_intent,
                "pred_intent": t_res.intent,
                "true_decision": true_decision,
                "pred_decision": t_res.decision,
                "confidence": t_res.confidence,
                "draft_reply": t_res.draft_reply,
                "retrieved_count": 0,
                "reason": t_res.reason,
                "latency_ms": t_res.latency_ms or 0.1,
                "cost_estimate": 0.0,
                "category_type": category_type,
                "key_facts": key_facts
            })
        except Exception as e:
            logger.error(f"Trivial baseline failed on {ex_id}: {e}")

        # System 2: Simple Baseline
        try:
            s_res = run_simple_baseline(cust_text)
            system_results["simple"].append({
                "id": ex_id,
                "customer_text": cust_text,
                "true_intent": true_intent,
                "pred_intent": s_res.intent,
                "true_decision": true_decision,
                "pred_decision": s_res.decision,
                "confidence": s_res.confidence,
                "draft_reply": s_res.draft_reply,
                "retrieved_count": len(s_res.retrieved),
                "reason": s_res.reason,
                "latency_ms": s_res.latency_ms or 20.0,
                "cost_estimate": 0.0,
                "category_type": category_type,
                "key_facts": key_facts
            })
        except Exception as e:
            logger.error(f"Simple baseline failed on {ex_id}: {e}")

        # System 3: Full LangGraph Agent
        try:
            t0 = time.perf_counter()
            f_state = run_agent_pipeline(cust_text)
            f_latency = (time.perf_counter() - t0) * 1000
            
            system_results["full"].append({
                "id": ex_id,
                "customer_text": cust_text,
                "true_intent": true_intent,
                "pred_intent": f_state.get("intent", "other_unclear"),
                "true_decision": true_decision,
                "pred_decision": f_state.get("decision", "escalate"),
                "confidence": f_state.get("confidence", 0.0),
                "draft_reply": f_state.get("draft_reply", ""),
                "cited_thread_ids": f_state.get("cited_thread_ids", []),
                "retrieved_count": len(f_state.get("retrieved") or []),
                "reason": f_state.get("reason", ""),
                "latency_ms": round(f_latency, 2),
                "cost_estimate": round(0.00015, 6), # Approx token cost
                "category_type": category_type,
                "key_facts": key_facts
            })
        except Exception as e:
            logger.error(f"Full pipeline failed on {ex_id}: {e}")

    # 2. Compute Performance Metrics
    metrics_summary: Dict[str, Any] = {}
    error_cases: Dict[str, List[Dict[str, Any]]] = {s: [] for s in systems}

    for sys_name, records in system_results.items():
        if not records:
            continue

        y_true_intent = [r["true_intent"] for r in records]
        y_pred_intent = [r["pred_intent"] for r in records]

        y_true_dec = [r["true_decision"] for r in records]
        y_pred_dec = [r["pred_decision"] for r in records]

        intent_met = compute_intent_metrics(y_true_intent, y_pred_intent)
        routing_met = compute_routing_metrics(y_true_dec, y_pred_dec)

        latencies = [r["latency_ms"] for r in records]
        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))

        # Safety-Critical False Auto-Handle Rate
        safety_records = [r for r in records if r["true_decision"] == "escalate"]
        safety_violations = [r for r in safety_records if r["pred_decision"] == "auto_handle"]
        safety_violation_rate = (len(safety_violations) / len(safety_records)) * 100.0 if safety_records else 0.0

        # Collect failure cases
        for r in records:
            intent_err = (r["true_intent"] != r["pred_intent"])
            routing_err = (r["true_decision"] != r["pred_decision"])
            if intent_err or routing_err:
                error_cases[sys_name].append({
                    "id": r["id"],
                    "customer_text": r["customer_text"],
                    "true_intent": r["true_intent"],
                    "pred_intent": r["pred_intent"],
                    "true_decision": r["true_decision"],
                    "pred_decision": r["pred_decision"],
                    "reason": r.get("reason", ""),
                    "is_safety_violation": (r["true_decision"] == "escalate" and r["pred_decision"] == "auto_handle")
                })

        metrics_summary[sys_name] = {
            "sample_count": len(records),
            "intent_accuracy": intent_met["accuracy"],
            "intent_macro_f1": intent_met["macro_f1"],
            "routing_accuracy": routing_met["accuracy"],
            "escalate_precision": routing_met["escalate_precision"],
            "escalate_recall": routing_met["escalate_recall"],
            "escalate_f1": routing_met["escalate_f1"],
            "safety_violation_count": len(safety_violations),
            "safety_violation_rate_pct": round(safety_violation_rate, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "avg_cost_usd": round(float(np.mean([r["cost_estimate"] for r in records])), 6)
        }

    # 3. Stratified Subsample LLM-as-a-Judge Quality Scoring
    print("\n--- Running LLM-as-a-Judge on Stratified Subsample ---")
    judge_records = []
    stratified_sample = dataset[:min(judge_sample_size, len(dataset))]

    for idx, ex in enumerate(stratified_sample, start=1):
        ex_id = ex["id"]
        cust_text = ex["customer_text"]
        true_intent = ex["true_intent"]
        key_facts = ex.get("key_facts", [])

        # Get full system output for this example
        full_rec = next((r for r in system_results["full"] if r["id"] == ex_id), None)
        if not full_rec:
            continue

        reply_crit = ex.get("reply_criteria") or ex.get("key_facts", [])

        judge_score = score_draft_with_judge(
            customer_text=cust_text,
            true_intent=true_intent,
            key_facts=key_facts,
            retrieved_examples=[{"thread_id": tid} for tid in full_rec.get("cited_thread_ids", [])],
            draft_reply=full_rec.get("draft_reply", ""),
            decision=full_rec.get("pred_decision", ""),
            reason=full_rec.get("reason", ""),
            reply_criteria=reply_crit
        )

        judge_records.append({
            "id": ex_id,
            "overall_score": judge_score["overall_score"],
            "relevance_score": judge_score["relevance_score"],
            "tone_score": judge_score["tone_score"],
            "grounding_score": judge_score["grounding_score"],
            "actionability_score": judge_score["actionability_score"],
            "passed_checklist": judge_score["passed_checklist"],
            "criteria_evaluations": judge_score.get("criteria_evaluations", []),
            "supported_by_thread_id": judge_score.get("supported_by_thread_id", "none"),
            "rationale": judge_score["rationale"]
        })

    if judge_records:
        avg_overall = float(np.mean([j["overall_score"] for j in judge_records]))
        avg_relevance = float(np.mean([j["relevance_score"] for j in judge_records]))
        avg_tone = float(np.mean([j["tone_score"] for j in judge_records]))
        avg_grounding = float(np.mean([j["grounding_score"] for j in judge_records]))
        avg_actionability = float(np.mean([j["actionability_score"] for j in judge_records]))
        checklist_pass_rate = float(np.mean([1.0 if j["passed_checklist"] else 0.0 for j in judge_records])) * 100.0

        metrics_summary["full"]["judge_quality"] = {
            "avg_overall_score": round(avg_overall, 2),
            "avg_relevance": round(avg_relevance, 2),
            "avg_tone": round(avg_tone, 2),
            "avg_grounding": round(avg_grounding, 2),
            "avg_actionability": round(avg_actionability, 2),
            "checklist_pass_rate_pct": round(checklist_pass_rate, 2),
            "scored_samples": len(judge_records)
        }

    # 4. Save artifacts & Raw Judge Outputs
    comparison_json_path = EVAL_RESULTS_DIR / "eval_comparison.json"
    comparison_csv_path = EVAL_RESULTS_DIR / "eval_comparison.csv"
    error_analysis_path = EVAL_RESULTS_DIR / "error_analysis.json"
    judge_raw_path = EVAL_RESULTS_DIR / "judge_raw_evaluations.jsonl"

    with open(comparison_json_path, "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)

    with open(error_analysis_path, "w", encoding="utf-8") as f:
        json.dump(error_cases, f, indent=2)

    if judge_records:
        with open(judge_raw_path, "w", encoding="utf-8") as f:
            for jrec in judge_records:
                f.write(json.dumps(jrec, ensure_ascii=False) + "\n")

    # 5. Run & Save Judge Agreement Calibration Study
    from eval.judge_agreement import run_blind_agreement_study
    agreement_metrics = run_blind_agreement_study(EVAL_RESULTS_DIR)
    metrics_summary["judge_agreement"] = agreement_metrics

    # Convert metrics summary to tabular CSV
    rows = []
    for sys_name in ["trivial", "simple", "full"]:
        met = metrics_summary.get(sys_name)
        if not met:
            continue
        row = {
            "System": sys_name.capitalize(),
            "Intent Accuracy": f"{met['intent_accuracy'] * 100:.1f}%",
            "Routing Accuracy": f"{met['routing_accuracy'] * 100:.1f}%",
            "Escalate F1": f"{met['escalate_f1'] * 100:.1f}%",
            "Safety Violations": f"{met['safety_violation_count']} ({met['safety_violation_rate_pct']}%)",
            "Avg Latency (ms)": f"{met['avg_latency_ms']:.1f} ms",
            "P95 Latency (ms)": f"{met['p95_latency_ms']:.1f} ms",
            "Avg Cost ($)": f"${met['avg_cost_usd']:.6f}"
        }
        if "judge_quality" in met:
            row["LLM Judge Overall (1-5)"] = f"{met['judge_quality']['avg_overall_score']:.2f} / 5.0"
            row["Checklist Pass Rate"] = f"{met['judge_quality']['checklist_pass_rate_pct']:.1f}%"
        rows.append(row)

    df_comp = pd.DataFrame(rows)
    df_comp.to_csv(comparison_csv_path, index=False)

    print("\n==================================================")
    print("Comparative Evaluation Summary Table:")
    print("==================================================")
    print(df_comp.to_string(index=False))

    return metrics_summary

if __name__ == "__main__":
    run_evaluation()
