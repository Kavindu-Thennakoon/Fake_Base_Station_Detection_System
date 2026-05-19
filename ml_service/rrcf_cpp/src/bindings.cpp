#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>
#include "../include/rctree.hpp"

namespace py = pybind11;

class PyRCTree {
public:
    rrcf::RCTree tree;
    PyRCTree() = default;
    PyRCTree(py::array_t<double> X, py::array_t<int64_t> labels, uint64_t seed = 0) {
        auto xbuf = X.request();
        if (xbuf.ndim != 2) throw std::runtime_error("X must be 2-D");
        int n = (int)xbuf.shape[0];
        int d = (int)xbuf.shape[1];
        double* xptr = static_cast<double*>(xbuf.ptr);
        auto lbuf = labels.request();
        int64_t* lptr = (lbuf.size > 0) ? static_cast<int64_t*>(lbuf.ptr) : nullptr;
        tree = rrcf::RCTree(xptr, n, d, lptr, seed);
    }
    void insert_point(py::array_t<double> point, int64_t index) {
        auto buf = point.request();
        double* ptr = static_cast<double*>(buf.ptr);
        std::vector<double> pt(ptr, ptr + buf.size);
        tree.insert_point(pt, index);
    }
    void forget_point(int64_t index) { tree.forget_point(index); }
    double codisp(int64_t index) { return tree.codisp(index); }
    py::list get_leaf_indices() {
        py::list result;
        for (auto& [k, v] : tree.leaves) result.append(k);
        return result;
    }
    int num_leaves() { return (int)tree.leaves.size(); }
};

PYBIND11_MODULE(_rrcf_core, m) {
    m.doc() = "C++ RRCF with batch scoring";
    py::class_<PyRCTree>(m, "RCTree")
        .def(py::init<>())
        .def(py::init<py::array_t<double>, py::array_t<int64_t>, uint64_t>(),
             py::arg("X"), py::arg("index_labels"), py::arg("seed") = 0)
        .def("insert_point",     &PyRCTree::insert_point)
        .def("forget_point",     &PyRCTree::forget_point)
        .def("codisp",           &PyRCTree::codisp)
        .def("get_leaf_indices", &PyRCTree::get_leaf_indices)
        .def_property_readonly("num_leaves", &PyRCTree::num_leaves);

    m.def("score_batch", [](py::list forest_list, py::array_t<double, py::array::c_style | py::array::forcecast> X_np) -> py::array_t<double> {
        auto buf = X_np.request();
        if (buf.ndim != 2) throw std::runtime_error("X must be 2-D");
        int n_rows = (int)buf.shape[0];
        int d = (int)buf.shape[1];
        double* data = static_cast<double*>(buf.ptr);
        std::vector<PyRCTree*> forest;
        forest.reserve(forest_list.size());
        for (auto& item : forest_list)
            forest.push_back(item.cast<PyRCTree*>());
        int n_trees = (int)forest.size();
        auto result = py::array_t<double>(n_rows);
        auto rbuf = result.request();
        double* out = static_cast<double*>(rbuf.ptr);
        int64_t temp_base = 900000000LL;
        for (int i = 0; i < n_rows; i++) {
            std::vector<double> pt(data + i * d, data + (i + 1) * d);
            double total = 0.0;
            int count = 0;
            int64_t temp_idx = temp_base + i;
            for (int t = 0; t < n_trees; t++) {
                auto* leaf = forest[t]->tree.insert_point(pt, temp_idx);
                if (leaf) {
                    total += forest[t]->tree.codisp(temp_idx);
                    count++;
                }
                forest[t]->tree.forget_point(temp_idx);
            }
            out[i] = (count > 0) ? total / count : 0.0;
        }
        return result;
    }, py::arg("forest"), py::arg("X"), "Score all rows at once");
}
