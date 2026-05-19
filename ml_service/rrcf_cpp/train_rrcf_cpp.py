#!/usr/bin/env python3
"""
train_rrcf_cpp.py — Drop-in replacement functions for train_rrcf_gpu_mp_v2.py
Uses C++ rrcf_cpp for 30-50x faster tree building.
"""
import numpy as np
import _rrcf_core as rrcf_cpp


def train_rrcf_cpp_on_X(X, num_trees=150, tree_size=1024, random_seed=0):
    """
    Drop-in replacement for train_rrcf_on_X() / build_forest_sequential().
    Returns a list of rrcf_cpp.RCTree objects.
    """
    if X is None or X.size == 0:
        return []
    n, d = X.shape
    X = np.ascontiguousarray(X, dtype=np.float64)
    # Add tiny jitter to avoid numerical ties
    X = X + np.random.normal(scale=1e-12, size=X.shape)

    forest = []
    use_tree_size = int(min(tree_size, max(2, n)))
    rng = np.random.RandomState(random_seed)

    while len(forest) < num_trees:
        seed = int(rng.randint(0, 2**32))
        if n <= use_tree_size:
            labels = np.arange(n, dtype=np.int64)
            tree = rrcf_cpp.RCTree(X, labels, seed=seed)
            forest.append(tree)
        else:
            idxs = rng.choice(n, size=use_tree_size, replace=False)
            X_sub = np.ascontiguousarray(X[idxs], dtype=np.float64)
            labels = idxs.astype(np.int64)
            tree = rrcf_cpp.RCTree(X_sub, labels, seed=seed)
            forest.append(tree)
    return forest[:num_trees]


def compute_mean_std_codisp_cpp(forest, n):
    """
    Drop-in replacement for compute_mean_std_codisp().
    """
    avg_codisp = np.zeros(n, dtype=np.float64)
    counts = np.zeros(n, dtype=np.int64)
    for tree in forest:
        for idx in tree.get_leaf_indices():
            idx_int = int(idx)
            if 0 <= idx_int < n:
                avg_codisp[idx_int] += tree.codisp(idx)
                counts[idx_int] += 1
    mask = counts > 0
    if mask.sum() == 0:
        return 0.0, 0.0
    avg_codisp[mask] /= counts[mask]
    return float(avg_codisp[mask].mean()), float(avg_codisp[mask].std(ddof=0))


if __name__ == "__main__":
    print("Testing C++ RRCF training...")
    X = np.random.randn(1000, 20).astype(np.float64)
    forest = train_rrcf_cpp_on_X(X, num_trees=50, tree_size=256, random_seed=42)
    mean_c, std_c = compute_mean_std_codisp_cpp(forest, X.shape[0])
    print(f"  Built {len(forest)} trees on {X.shape[0]}x{X.shape[1]} data")
    print(f"  Mean codisp: {mean_c:.4f}, Std codisp: {std_c:.4f}")
    print("C++ RRCF training works!")
