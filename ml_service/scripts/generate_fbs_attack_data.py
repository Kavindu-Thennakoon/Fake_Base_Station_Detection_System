"""
Generate synthetic MR data with injected FBS attacks for model evaluation.

Attack scenarios:
1. IMSI Catcher: Unknown cell ID with abnormally strong signal (-50 to -44 dBm)
2. Downgrade Attack: Known neighbor with degraded signal quality
3. Neighbor Spoofing: Known neighbor appearing with unusual signal characteristics

Output: labeled CSV with ground truth 'is_attack' column for precision/recall evaluation.

Usage:
    python generate_fbs_attack_data.py --output fbs_attack_test.csv --rows 5000 --attack-ratio 0.15
"""

import argparse
import random
import csv
from datetime import datetime, timedelta


SERVING_CELLS = [
    "41301_12845", "41301_12846", "41301_12847",
    "41301_33901", "41301_33902", "41301_44510",
]

LEGIT_NEIGHBORS = [
    "41301_12900", "41301_12901", "41301_12902",
    "41301_33950", "41301_33951", "41301_44560",
]

FBS_CELLS = ["99999_00001", "99999_00002", "88888_00003"]


def generate_normal_row(serving, ts):
    neighbors = random.sample(LEGIT_NEIGHBORS, min(3, len(LEGIT_NEIGHBORS)))
    rows = []
    for i, nbr in enumerate(neighbors, 1):
        rows.append({
            "serving_cell_id": serving,
            "datetime_raw": ts.strftime("%Y-%m-%d %H:%M:%S"),
            f"nbr_cell_{i}_id": nbr,
            f"nbr_cell_{i}_rsrp": round(random.gauss(-82, 6), 1),
            f"nbr_cell_{i}_rsrq": round(random.gauss(-10, 2.5), 1),
        })
    return merge_neighbor_rows(rows), False


def generate_imsi_catcher(serving, ts):
    """Attack Type 1: Unknown cell with abnormally strong signal."""
    fbs = random.choice(FBS_CELLS)
    legit = random.sample(LEGIT_NEIGHBORS, 2)
    row = {
        "serving_cell_id": serving,
        "datetime_raw": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "nbr_cell_1_id": fbs,
        "nbr_cell_1_rsrp": round(random.uniform(-52, -44), 1),
        "nbr_cell_1_rsrq": round(random.uniform(-5, -3), 1),
        "nbr_cell_2_id": legit[0],
        "nbr_cell_2_rsrp": round(random.gauss(-82, 6), 1),
        "nbr_cell_2_rsrq": round(random.gauss(-10, 2.5), 1),
        "nbr_cell_3_id": legit[1],
        "nbr_cell_3_rsrp": round(random.gauss(-82, 6), 1),
        "nbr_cell_3_rsrq": round(random.gauss(-10, 2.5), 1),
    }
    return row, True


def generate_downgrade_attack(serving, ts):
    """Attack Type 2: Known neighbor with severely degraded quality."""
    neighbors = random.sample(LEGIT_NEIGHBORS, 3)
    row = {
        "serving_cell_id": serving,
        "datetime_raw": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "nbr_cell_1_id": neighbors[0],
        "nbr_cell_1_rsrp": round(random.uniform(-120, -110), 1),
        "nbr_cell_1_rsrq": round(random.uniform(-18, -15), 1),
        "nbr_cell_2_id": neighbors[1],
        "nbr_cell_2_rsrp": round(random.gauss(-82, 6), 1),
        "nbr_cell_2_rsrq": round(random.gauss(-10, 2.5), 1),
        "nbr_cell_3_id": neighbors[2],
        "nbr_cell_3_rsrp": round(random.gauss(-82, 6), 1),
        "nbr_cell_3_rsrq": round(random.gauss(-10, 2.5), 1),
    }
    return row, True


def generate_neighbor_spoofing(serving, ts):
    """Attack Type 3: FBS masquerading with unexpected signal strength."""
    fbs = random.choice(FBS_CELLS)
    legit = random.sample(LEGIT_NEIGHBORS, 2)
    row = {
        "serving_cell_id": serving,
        "datetime_raw": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "nbr_cell_1_id": legit[0],
        "nbr_cell_1_rsrp": round(random.gauss(-82, 6), 1),
        "nbr_cell_1_rsrq": round(random.gauss(-10, 2.5), 1),
        "nbr_cell_2_id": fbs,
        "nbr_cell_2_rsrp": round(random.uniform(-60, -50), 1),
        "nbr_cell_2_rsrq": round(random.uniform(-6, -4), 1),
        "nbr_cell_3_id": legit[1],
        "nbr_cell_3_rsrp": round(random.gauss(-82, 6), 1),
        "nbr_cell_3_rsrq": round(random.gauss(-10, 2.5), 1),
    }
    return row, True


def merge_neighbor_rows(rows):
    merged = {}
    for r in rows:
        merged.update(r)
    return merged


ATTACK_GENERATORS = [
    generate_imsi_catcher,
    generate_downgrade_attack,
    generate_neighbor_spoofing,
]

COLUMNS = [
    "serving_cell_id", "datetime_raw",
    "nbr_cell_1_id", "nbr_cell_1_rsrp", "nbr_cell_1_rsrq",
    "nbr_cell_2_id", "nbr_cell_2_rsrp", "nbr_cell_2_rsrq",
    "nbr_cell_3_id", "nbr_cell_3_rsrp", "nbr_cell_3_rsrq",
    "is_attack", "attack_type",
]


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic FBS attack test data")
    parser.add_argument("--output", default="fbs_attack_test.csv")
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--attack-ratio", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    base_time = datetime(2026, 5, 20, 9, 0, 0)
    n_attacks = int(args.rows * args.attack_ratio)
    n_normal = args.rows - n_attacks

    data = []

    for i in range(n_normal):
        ts = base_time + timedelta(seconds=random.randint(0, 86400))
        serving = random.choice(SERVING_CELLS)
        row, _ = generate_normal_row(serving, ts)
        row["is_attack"] = 0
        row["attack_type"] = "none"
        data.append(row)

    attack_types = ["imsi_catcher", "downgrade", "neighbor_spoofing"]
    for i in range(n_attacks):
        ts = base_time + timedelta(seconds=random.randint(0, 86400))
        serving = random.choice(SERVING_CELLS)
        gen_idx = i % len(ATTACK_GENERATORS)
        row, _ = ATTACK_GENERATORS[gen_idx](serving, ts)
        row["is_attack"] = 1
        row["attack_type"] = attack_types[gen_idx]
        data.append(row)

    random.shuffle(data)

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(data)

    total = len(data)
    attacks = sum(1 for d in data if d["is_attack"] == 1)
    print(f"Generated {total} rows ({attacks} attacks, {total - attacks} normal)")
    print(f"Attack ratio: {attacks/total:.1%}")
    print(f"Attack types: {', '.join(attack_types)}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
