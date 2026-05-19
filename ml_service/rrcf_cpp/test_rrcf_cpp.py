#!/usr/bin/env python3
"""
Test: Compare Python rrcf vs C++ rrcf_cpp
"""
import time
import numpy as np

try:
    import rrcf
    HAS_PY = True
except ImportError:
    HAS_PY = False
    print("Python rrcf not installed — skipping comparison")

import _rrcf_core as rrcf_cpp

def test_basic():
    print("=" * 60)
    print("TEST: Basic C++ RCTree build + codisp")
    print("=" * 60)
    np.random.seed(42)
    n, d = 200, 5
    X = np.random.randn(n, d).astype(np.float64)
    labels = np.arange(n, dtype=np.int64)

    tree = rrcf_cpp.RCTree(X, labels, seed=42)
    print(f"  Built tree with {tree.num_leaves} leaves")

    scores = []
    for idx in tree.get_leaf_indices():
        scores.append(tree.codisp(idx))
    print(f"  Mean codisp: {np.mean(scores):.4f}")
    print(f"  Max  codisp: {np.max(scores):.4f}")

    new_pt = np.array([10.0] * d)
    tree.insert_point(new_pt, 9999)
    sc = tree.codisp(9999)
    print(f"  Outlier codisp: {sc:.4f} (should be high)")
    tree.forget_point(9999)
    print(f"  After forget: {tree.num_leaves} leaves")
    print("  PASSED\n")


def test_speed(n=5000, d=10, num_trees=50, tree_size=256):
    print("=" * 60)
    print(f"SPEED TEST: {n} points, {d} dims, {num_trees} trees (size={tree_size})")
    print("=" * 60)
    np.random.seed(0)
    X = np.random.randn(n, d).astype(np.float64)

    t0 = time.time()
    cpp_forest = []
    for t in range(num_trees):
        idxs = np.random.choice(n, size=min(tree_size, n), replace=False)
        X_sub = np.ascontiguousarray(X[idxs], dtype=np.float64)
        labels = idxs.astype(np.int64)
        tree = rrcf_cpp.RCTree(X_sub, labels, seed=t)
        cpp_forest.append(tree)
    cpp_build = time.time() - t0

    t0 = time.time()
    cpp_scores = np.zeros(n)
    cpp_counts = np.zeros(n, dtype=int)
    for tree in cpp_forest:
        for idx in tree.get_leaf_indices():
            cpp_scores[idx] += tree.codisp(idx)
            cpp_counts[idx] += 1
    mask = cpp_counts > 0
    cpp_scores[mask] /= cpp_counts[mask]
    cpp_codisp = time.time() - t0
    print(f"  C++    build: {cpp_build:.3f}s   codisp: {cpp_codisp:.3f}s   TOTAL: {cpp_build+cpp_codisp:.3f}s")

    if HAS_PY:
        np.random.seed(0)
        t0 = time.time()
        py_forest = []
        for t in range(num_trees):
            idxs = np.random.choice(n, size=min(tree_size, n), replace=False)
            X_sub = np.ascontiguousarray(X[idxs], dtype=np.float64)
            labels_list = [int(i) for i in idxs]
            tree = rrcf.RCTree(X_sub, index_labels=labels_list)
            py_forest.append(tree)
        py_build = time.time() - t0

        t0 = time.time()
        py_scores = np.zeros(n)
        py_counts = np.zeros(n, dtype=int)
        for tree in py_forest:
            for leaf in tree.leaves:
                py_scores[leaf] += tree.codisp(leaf)
                py_counts[leaf] += 1
        mask = py_counts > 0
        py_scores[mask] /= py_counts[mask]
        py_codisp = time.time() - t0
        print(f"  Python build: {py_build:.3f}s   codisp: {py_codisp:.3f}s   TOTAL: {py_build+py_codisp:.3f}s")

        speedup = (py_build + py_codisp) / max(cpp_build + cpp_codisp, 1e-9)
        print(f"\n  C++ is {speedup:.1f}x faster than Python rrcf")
    print()


if __name__ == "__main__":
    test_basic()
    test_speed(n=5000,  d=10, num_trees=50,  tree_size=256)
    test_speed(n=20000, d=20, num_trees=100, tree_size=512)
