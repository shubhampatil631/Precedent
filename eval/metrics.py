"""
eval/metrics.py
Helper functions for computing Accuracy, Precision, Recall, F1, and Confusion Matrices.
"""

from typing import List, Dict, Any
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support, accuracy_score

def compute_intent_metrics(y_true: List[str], y_pred: List[str]) -> Dict[str, Any]:
    acc = accuracy_score(y_true, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    matrix = confusion_matrix(y_true, y_pred).tolist()
    labels = sorted(list(set(y_true + y_pred)))
    return {
        "accuracy": round(acc, 4),
        "macro_precision": round(prec, 4),
        "macro_recall": round(rec, 4),
        "macro_f1": round(f1, 4),
        "confusion_matrix": matrix,
        "labels": labels
    }

def compute_routing_metrics(y_true: List[str], y_pred: List[str]) -> Dict[str, Any]:
    # Positive class is "escalate"
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, pos_label="escalate", average="binary", zero_division=0
    )
    acc = accuracy_score(y_true, y_pred)
    return {
        "accuracy": round(acc, 4),
        "escalate_precision": round(prec, 4),
        "escalate_recall": round(rec, 4),
        "escalate_f1": round(f1, 4)
    }
