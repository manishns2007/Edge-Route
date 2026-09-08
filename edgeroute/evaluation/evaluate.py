"""
evaluation/evaluate.py
======================
Run the full EdgeRoute evaluation dataset through the routing pipeline
and compute classification metrics.

Metrics calculated:
  - Overall accuracy
  - Per-class: precision, recall, F1
  - Macro/weighted averages
  - Confusion matrix
  - Latency statistics (average, min, max, p50, p95)

Usage:
  py evaluation/evaluate.py                  # All 60 test cases
  py evaluation/evaluate.py --limit 20       # First 20 test cases
  py evaluation/evaluate.py --output results.json

Note: Requires Ollama to be running for SLM-based routing.
      Falls back to deterministic routing if Ollama is unavailable.
"""
from __future__ import annotations

import argparse
import json
import sys
import os
import time
from pathlib import Path

# Make edgeroute importable when run from the evaluation/ directory
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
)
from tabulate import tabulate

from router.classifier import route


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ROUTE_LABELS = ["LOCAL_SIMPLE", "LOCAL_COMMAND", "CLOUD_COMPLEX", "AMBIGUOUS"]


def load_test_cases(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _latency_stats(latencies: list[float]) -> dict:
    if not latencies:
        return {}
    arr = np.array(latencies)
    return {
        "count": len(arr),
        "mean_ms": float(np.mean(arr)),
        "min_ms": float(np.min(arr)),
        "max_ms": float(np.max(arr)),
        "p50_ms": float(np.percentile(arr, 50)),
        "p95_ms": float(np.percentile(arr, 95)),
        "std_ms": float(np.std(arr)),
    }


def _bar(fraction: float, width: int = 20) -> str:
    filled = int(round(fraction * width))
    return "█" * filled + "░" * (width - filled)


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def run_evaluation(
    test_cases: list[dict],
    verbose: bool = False,
) -> dict:
    """
    Run the routing pipeline for each test case and collect results.

    Returns a summary dict with metrics and per-case results.
    """
    y_true: list[str] = []
    y_pred: list[str] = []
    latencies: list[float] = []
    per_case_results: list[dict] = []
    ollama_available: bool | None = None

    print(f"\n{'='*60}")
    print("  EdgeRoute — Routing Evaluation")
    print(f"{'='*60}")
    print(f"  Test cases: {len(test_cases)}")
    print(f"  Running pipeline for each query...\n")

    for i, tc in enumerate(test_cases, 1):
        qid = tc.get("id", i)
        query = tc["query"]
        expected = tc["expected_route"]

        if verbose:
            print(f"  [{i:02d}/{len(test_cases)}] {query[:60]!r}")

        try:
            result = route(query)
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR on case {qid}: {exc}")
            result_route = "AMBIGUOUS"
            lat = 0.0
        else:
            result_route = result.final_route
            lat = result.latency_ms
            if ollama_available is None:
                ollama_available = result.ollama_available

        y_true.append(expected)
        y_pred.append(result_route)
        latencies.append(lat)

        correct = result_route == expected
        per_case_results.append({
            "id": qid,
            "query": query,
            "expected": expected,
            "predicted": result_route,
            "correct": correct,
            "latency_ms": round(lat, 2),
            "category": tc.get("category", ""),
        })

        if verbose:
            status = "✓" if correct else "✗"
            print(f"    {status} Expected={expected:<15} Got={result_route:<15} ({lat:.0f}ms)")

        # Progress indicator
        if not verbose and i % 10 == 0:
            pct = i / len(test_cases)
            print(f"  Progress: {_bar(pct)} {i}/{len(test_cases)} ({pct*100:.0f}%)")

    # ------------------------------------------------------------------
    # Compute metrics
    # ------------------------------------------------------------------
    accuracy = accuracy_score(y_true, y_pred)
    report = classification_report(
        y_true, y_pred,
        labels=ROUTE_LABELS,
        output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(y_true, y_pred, labels=ROUTE_LABELS)
    lat_stats = _latency_stats(latencies)

    # ------------------------------------------------------------------
    # Pretty-print report
    # ------------------------------------------------------------------
    print(f"\n{'='*60}")
    print("  ROUTING EVALUATION RESULTS")
    print(f"{'='*60}\n")

    print(f"  Ollama available : {'YES' if ollama_available else 'NO (deterministic fallback used)'}")
    print(f"  Total queries    : {len(test_cases)}")
    print(f"  Correct          : {sum(r['correct'] for r in per_case_results)}")
    print(f"  Accuracy         : {accuracy*100:.1f}%\n")

    # Per-route metrics table
    metric_rows = []
    for label in ROUTE_LABELS:
        if label in report:
            r = report[label]
            metric_rows.append([
                label,
                f"{r['precision']*100:.1f}%",
                f"{r['recall']*100:.1f}%",
                f"{r['f1-score']*100:.1f}%",
                int(r['support']),
            ])
    print(tabulate(
        metric_rows,
        headers=["Route", "Precision", "Recall", "F1", "Support"],
        tablefmt="rounded_outline",
    ))

    print(f"\n  Macro F1   : {report['macro avg']['f1-score']*100:.1f}%")
    print(f"  Weighted F1: {report['weighted avg']['f1-score']*100:.1f}%")

    # Confusion matrix
    print(f"\n  Confusion Matrix (rows=actual, cols=predicted):")
    cm_rows = []
    for i, label in enumerate(ROUTE_LABELS):
        short = label.replace("LOCAL_", "L_").replace("CLOUD_", "C_")
        cm_rows.append([short] + list(cm[i]))
    print(tabulate(
        cm_rows,
        headers=[""] + [l.replace("LOCAL_", "L_").replace("CLOUD_", "C_") for l in ROUTE_LABELS],
        tablefmt="rounded_outline",
    ))

    # Latency
    print(f"\n  Latency Statistics:")
    if lat_stats:
        print(f"    Average : {lat_stats['mean_ms']:.1f} ms")
        print(f"    Min     : {lat_stats['min_ms']:.1f} ms")
        print(f"    Max     : {lat_stats['max_ms']:.1f} ms")
        print(f"    P50     : {lat_stats['p50_ms']:.1f} ms")
        print(f"    P95     : {lat_stats['p95_ms']:.1f} ms")

    # Incorrect cases
    incorrect = [r for r in per_case_results if not r["correct"]]
    if incorrect:
        print(f"\n  Misclassified Cases ({len(incorrect)}):")
        for r in incorrect:
            print(f"    [{r['id']:02d}] {r['query'][:55]!r}")
            print(f"         Expected={r['expected']}, Got={r['predicted']}")
    else:
        print("\n  All cases correctly classified! ✓")

    print(f"\n{'='*60}\n")

    return {
        "accuracy": accuracy,
        "total": len(test_cases),
        "correct": sum(r["correct"] for r in per_case_results),
        "ollama_available": ollama_available,
        "report": report,
        "confusion_matrix": cm.tolist(),
        "labels": ROUTE_LABELS,
        "latency": lat_stats,
        "per_case": per_case_results,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="EdgeRoute Evaluation")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of test cases")
    parser.add_argument("--output", type=str, default=None, help="Save JSON results to file")
    parser.add_argument("--verbose", action="store_true", help="Show per-case details")
    args = parser.parse_args()

    test_path = Path(__file__).parent / "test_cases.json"
    test_cases = load_test_cases(test_path)

    if args.limit:
        test_cases = test_cases[: args.limit]

    summary = run_evaluation(test_cases, verbose=args.verbose)

    if args.output:
        out_path = Path(args.output)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"  Results saved to {out_path}")


if __name__ == "__main__":
    main()
