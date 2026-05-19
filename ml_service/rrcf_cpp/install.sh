#!/bin/bash
set -e
echo "=== Installing C++ RRCF ==="
pip install pybind11 numpy
echo "=== Building C++ extension ==="
cd "$(dirname "$0")"
python setup.py build_ext --inplace
echo "=== Testing ==="
python test_rrcf_cpp.py
echo ""
echo "=== SUCCESS ==="
echo "Import with:  import rrcf_cpp"
echo "Usage:        tree = rrcf_cpp.RCTree(X, labels, seed=0)"
