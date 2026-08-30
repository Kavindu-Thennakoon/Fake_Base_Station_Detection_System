import argparse
import os
import subprocess
import sys
import time

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas required. pip install pandas")
    sys.exit(1)

def generate_dataset(base_csv_path, target_rows, output_path):
    print(f"Generating {target_rows:,} rows dataset...")
    df = pd.read_csv(base_csv_path)
    repeats = (target_rows // len(df)) + 1
    df_large = pd.concat([df] * repeats, ignore_index=True)
    df_large = df_large.head(target_rows)
    df_large.to_csv(output_path, index=False)
    return output_path

def run_test(csv_path, detect_script_path, model_dir, output_dir):
    cmd = [
        "python", detect_script_path,
        "--model-dir", model_dir,
        "--check-file", csv_path,
        "--output-dir", output_dir
    ]
    
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    end = time.time()
    
    if result.returncode != 0:
        print(f"Error running script:\n{result.stderr}")
        return -1
    return end - start

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "..", "data")
    output_dir = os.path.join(base_dir, "..", "output")
    model_dir = os.path.join(base_dir, "..", "model", "v4_model")
    
    base_csv = os.path.join(data_dir, "fbs_attack_test.csv")
    detect_script = os.path.join(base_dir, "detect_rrcf_v4.py")
    
    if not os.path.exists(base_csv):
        print(f"Base CSV {base_csv} not found.")
        sys.exit(1)
        
    os.makedirs(output_dir, exist_ok=True)
        
    sizes = [1000, 10000, 100000, 500000, 1000000]
    results = []
    
    print("\n" + "="*50)
    print(" SYSTEM OPTIMIZATION & LATENCY PROFILING ")
    print("="*50)
    
    for size in sizes:
        test_csv = os.path.join(output_dir, f"stress_test_{size}.csv")
        generate_dataset(base_csv, size, test_csv)
        
        print(f"Running detection pipeline on {size:,} rows...")
        elapsed = run_test(test_csv, detect_script, model_dir, output_dir)
        if elapsed < 0:
            print("Test failed. Aborting.")
            break
            
        rate = size / elapsed if elapsed > 0 else 0
        print(f"-> Completed in {elapsed:.2f} seconds ({rate:.0f} rows/sec)\n")
        results.append((size, elapsed))
        
        if os.path.exists(test_csv):
            os.remove(test_csv)
            
    print("="*50)
    print(" FINAL LATENCY PROFILING RESULTS ")
    print("="*50)
    print(f"{'Rows':<15} {'Processing Time (s)':<25} {'Rows/sec'}")
    for size, elapsed in results:
        rate = size / elapsed if elapsed > 0 else 0
        print(f"{size:<15,} {elapsed:<25.2f} {rate:.0f}")
        
    output_csv = os.path.join(output_dir, "latency_profiling_results.csv")
    pd.DataFrame(results, columns=["Rows", "Processing Time (s)"]).to_csv(output_csv, index=False)
    print(f"\nResults saved to {output_csv}")

if __name__ == "__main__":
    main()
