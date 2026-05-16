import os
import sys
from scripts.train_rrcf_gpu_mp_v4 import main as train_main


def run_training(train_file, model_dir, cell_details_file,
                 num_trees=150,
                 tree_size=1024,
                 n_jobs=4):

    try:
        sys.argv = [
            "train_rrcf_gpu_mp_v4.py",
            "--train-file", train_file,
            "--model-dir", model_dir,
            "--cell-details-file", cell_details_file,
            "--num-trees", str(num_trees),
            "--tree-size", str(tree_size),
            "--n-jobs", str(n_jobs),
        ]

        train_main()

        return {
            "status": "success",
            "model_dir": model_dir
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
        
