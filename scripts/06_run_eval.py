"""
06_run_eval.py
CLI driver for the comparative evaluation harness.
Evaluates Trivial, Simple, and Full LangGraph Agent on the 160 golden set examples,
computes classification & routing metrics, runs the LLM-as-a-judge, and exports
markdown tables for REPORT.md.
"""

import sys
import json
import argparse
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from eval.harness import run_evaluation
from app.config import EVAL_RESULTS_DIR

def parse_args():
    parser = argparse.ArgumentParser(description="Run Support Agent Comparative Evaluation")
    parser.add_argument("--sample-limit", type=int, default=None, help="Limit number of evaluation samples")
    parser.add_argument("--judge-samples", type=int, default=20, help="Number of samples to score with LLM Judge")
    return parser.parse_args()

def main():
    args = parse_args()
    print("==================================================")
    print("Starting Comprehensive Evaluation Suite (06_run_eval.py)")
    print(f"Sample Limit: {args.sample_limit or 'Full 160 samples'}")
    print(f"LLM Judge Samples: {args.judge_samples}")
    print("==================================================")

    metrics = run_evaluation(
        sample_limit=args.sample_limit,
        judge_sample_size=args.judge_samples
    )

    print("\n==================================================")
    print("Evaluation Complete!")
    print(f"Artifacts saved to {EVAL_RESULTS_DIR}")
    print("==================================================")

if __name__ == "__main__":
    main()
