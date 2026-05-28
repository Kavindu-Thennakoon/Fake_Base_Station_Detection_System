"""
Evaluate FBS detection model performance on labeled test data.

Computes: Precision, Recall, F1-Score, False Positive Rate, Confusion Matrix.
Works with output from generate_fbs_attack_data.py.

Usage:
    python evaluate_model.py --test-data fbs_attack_test.csv --results-dir ../output/eval_run/
    python evaluate_model.py --test-data fbs_attack_test.csv --demo-mode

In demo mode, simulates detection results without running the actual ML pipeline.
"""

import argparse
import json
import os
import sys
from datetime import datetime

try:
    import pandas as pd
    import numpy as np
except ImportError:
    print("ERROR: pandas and numpy required. Install with: pip install pandas numpy")
    sys.exit(1)


def load_ground_truth(path):
    df = pd.read_csv(path)
    if "is_attack" not in df.columns:
        print("ERROR: test data must have 'is_attack' column")
        sys.exit(1)
    return df


def load_detection_results(results_dir):
    anomalies_path = os.path.join(results_dir, "anomalies.csv")
    if not os.path.exists(anomalies_path):
        print(f"ERROR: {anomalies_path} not found")
        sys.exit(1)

    anomalies = pd.read_csv(anomalies_path)
    detected_indices = set()
    if "row_index" in anomalies.columns:
        detected_indices = set(anomalies["row_index"].tolist())
    return detected_indices


def simulate_detection(test_df, tp_rate=0.85, fp_rate=0.05):
    """Simulate detection for demo mode — realistic performance approximation."""
    np.random.seed(42)
    detected = set()

    for idx, row in test_df.iterrows():
        is_attack = row.get("is_attack", 0) == 1
        attack_type = row.get("attack_type", "none")

        if is_attack:
            if attack_type == "imsi_catcher":
                detect_prob = 0.95
            elif attack_type == "downgrade":
                detect_prob = 0.75
            elif attack_type == "neighbor_spoofing":
                detect_prob = 0.85
            else:
                detect_prob = tp_rate

            if np.random.random() < detect_prob:
                detected.add(idx)
        else:
            if np.random.random() < fp_rate:
                detected.add(idx)

    return detected


def compute_metrics(y_true, y_pred):
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0.0

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "false_positive_rate": round(fpr, 4),
        "accuracy": round(accuracy, 4),
        "total_samples": len(y_true),
        "total_attacks": sum(y_true),
        "total_detected": sum(y_pred),
    }


def compute_per_attack_metrics(test_df, y_pred):
    results = {}
    for attack_type in test_df["attack_type"].unique():
        if attack_type == "none":
            continue
        mask = test_df["attack_type"] == attack_type
        y_true_sub = test_df.loc[mask, "is_attack"].tolist()
        y_pred_sub = [y_pred[i] for i in test_df.index[mask]]

        tp = sum(1 for t, p in zip(y_true_sub, y_pred_sub) if t == 1 and p == 1)
        fn = sum(1 for t, p in zip(y_true_sub, y_pred_sub) if t == 1 and p == 0)
        total = len(y_true_sub)
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        results[attack_type] = {
            "total": total,
            "detected": tp,
            "missed": fn,
            "recall": round(recall, 4),
        }
    return results


def print_report(metrics, per_attack, output_path=None):
    lines = []
    lines.append("=" * 60)
    lines.append("  FBS DETECTION MODEL — EVALUATION REPORT")
    lines.append(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")
    lines.append("CONFUSION MATRIX:")
    lines.append(f"                    Predicted Attack  Predicted Normal")
    lines.append(f"  Actual Attack     TP={metrics['true_positives']:<14d} FN={metrics['false_negatives']}")
    lines.append(f"  Actual Normal     FP={metrics['false_positives']:<14d} TN={metrics['true_negatives']}")
    lines.append("")
    lines.append("OVERALL METRICS:")
    lines.append(f"  Precision:           {metrics['precision']:.4f}")
    lines.append(f"  Recall:              {metrics['recall']:.4f}")
    lines.append(f"  F1-Score:            {metrics['f1_score']:.4f}")
    lines.append(f"  Accuracy:            {metrics['accuracy']:.4f}")
    lines.append(f"  False Positive Rate: {metrics['false_positive_rate']:.4f}")
    lines.append("")
    lines.append(f"  Total Samples:       {metrics['total_samples']}")
    lines.append(f"  Total Attacks:       {metrics['total_attacks']}")
    lines.append(f"  Total Detected:      {metrics['total_detected']}")
    lines.append("")

    if per_attack:
        lines.append("PER-ATTACK-TYPE RECALL:")
        for atype, data in sorted(per_attack.items()):
            lines.append(f"  {atype:<25s} {data['detected']}/{data['total']} detected  (recall={data['recall']:.4f})")

    lines.append("")
    lines.append("=" * 60)

    report = "\n".join(lines)
    print(report)

    if output_path:
        with open(output_path, "w") as f:
            f.write(report)
        json_path = output_path.replace(".txt", ".json")
        with open(json_path, "w") as f:
            json.dump({"metrics": metrics, "per_attack": per_attack}, f, indent=2)
        print(f"\nReport saved to: {output_path}")
        print(f"JSON saved to:   {json_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate FBS detection model")
    parser.add_argument("--test-data", required=True, help="Path to labeled test CSV")
    parser.add_argument("--results-dir", help="Detection output directory (anomalies.csv)")
    parser.add_argument("--demo-mode", action="store_true", help="Simulate detection results")
    parser.add_argument("--output", default="evaluation_report.txt", help="Output report file")
    args = parser.parse_args()

    print(f"Loading test data from: {args.test_data}")
    test_df = load_ground_truth(args.test_data)
    y_true = test_df["is_attack"].tolist()

    if args.demo_mode:
        print("Running in DEMO mode (simulated detection)...")
        detected_indices = simulate_detection(test_df)
    elif args.results_dir:
        print(f"Loading detection results from: {args.results_dir}")
        detected_indices = load_detection_results(args.results_dir)
    else:
        print("ERROR: specify --results-dir or --demo-mode")
        sys.exit(1)

    y_pred = [1 if i in detected_indices else 0 for i in range(len(test_df))]

    metrics = compute_metrics(y_true, y_pred)
    per_attack = compute_per_attack_metrics(test_df, y_pred)

    print_report(metrics, per_attack, args.output)


if __name__ == "__main__":
    main()
