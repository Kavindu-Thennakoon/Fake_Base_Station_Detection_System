import os
import pandas as pd
import tempfile
import sys
import traceback

from scripts.detect_rrcf_v4 import main as detect_main


def run_detection(model_dir, input_file, cell_details_file,
                  output_dir=None,
                  threshold_mult=1.0,
                  z_threshold=2.0,
                  min_anomaly_score=4.0,
                  n_jobs=-1):

    try:
        # ✅ Step 1: output dir
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="fbs_output_")

        # ✅ Step 2: CLI args
        sys.argv = [
            "detect_rrcf_v4.py",
            "--model-dir", model_dir,
            "--check-file", input_file,
            "--cell-details-file", cell_details_file,
            "--output-dir", output_dir,
            "--threshold-mult", str(threshold_mult),
            "--z-threshold", str(z_threshold),
            "--min-anomaly-score", str(min_anomaly_score),
            "--n-jobs", str(n_jobs),
        ]

        # ✅ Step 3: run detection
        detect_main()

        # ✅ Step 4: safely find latest run
        latest_run = safe_get_latest_run(output_dir)

        # ✅ Step 5: safely load files (ALWAYS WORK)
        anomalies = safe_load_csv(os.path.join(latest_run, "anomalies.csv"))
        neighbor_details = safe_load_csv(os.path.join(latest_run, "neighbor_anomaly_details.csv"))
        ranked_neighbors = safe_load_csv(os.path.join(latest_run, "neighbor_ranked.csv"))

        return {
            "status": "success",
            "output_dir": latest_run,
            "total_anomalies": len(anomalies),
            "anomalies": anomalies,
            "neighbor_details": neighbor_details,
            "ranked_neighbors": ranked_neighbors
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()   # ✅ VERY IMPORTANT FOR DEBUG
        }
        
def safe_get_latest_run(base_output_dir):
    runs = [
        os.path.join(base_output_dir, d)
        for d in os.listdir(base_output_dir)
        if d.startswith("run_")
    ]

    if not runs:
        raise Exception("No run folders found")

    return max(runs, key=os.path.getmtime)


def safe_load_csv(path):
    # ✅ File does not exist
    if not os.path.exists(path):
        return []

    # ✅ File exists but empty
    try:
        df = pd.read_csv(path)
        if df.empty:
            return []
        return df.to_dict(orient="records")
    except:
        return []