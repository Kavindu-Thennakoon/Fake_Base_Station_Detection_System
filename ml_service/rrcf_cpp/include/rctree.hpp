#pragma once
#include <vector>
#include <random>
#include <unordered_map>
#include <algorithm>
#include <numeric>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace rrcf {

struct Node {
    virtual ~Node() = default;
    Node* parent = nullptr;
    int64_t n = 0;
    std::vector<double> bb_lo, bb_hi;
    virtual bool is_leaf() const = 0;
};

struct Branch : public Node {
    int q = 0;
    double p = 0.0;
    Node* left = nullptr;
    Node* right = nullptr;
    bool is_leaf() const override { return false; }
    ~Branch() override { delete left; delete right; }
};

struct Leaf : public Node {
    int64_t idx = -1;
    std::vector<double> point;
    bool is_leaf() const override { return true; }
};

class RCTree {
public:
    Node* root = nullptr;
    std::unordered_map<int64_t, Leaf*> leaves;
    int ndim = 0;

    RCTree() = default;

    // ── MOVE constructor & assignment (prevents use-after-free) ──
    RCTree(RCTree&& o) noexcept
        : root(o.root), leaves(std::move(o.leaves)),
          ndim(o.ndim), rng_(std::move(o.rng_))
    { o.root = nullptr; o.ndim = 0; }

    RCTree& operator=(RCTree&& o) noexcept {
        if (this != &o) {
            delete root;
            root = o.root;       o.root = nullptr;
            leaves = std::move(o.leaves);
            ndim = o.ndim;       o.ndim = 0;
            rng_ = std::move(o.rng_);
        }
        return *this;
    }

    // ── disable copy (raw-pointer tree can't be safely copied) ──
    RCTree(const RCTree&) = delete;
    RCTree& operator=(const RCTree&) = delete;

    // ── build from flat data ──
    RCTree(const double* data, int n, int d,
           const int64_t* labels = nullptr, uint64_t seed = 0)
        : ndim(d), rng_(seed)
    {
        if (n <= 0 || d <= 0) return;
        std::vector<std::vector<double>> X(n, std::vector<double>(d));
        std::vector<int64_t> lab(n);
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < d; j++) X[i][j] = data[i*d+j];
            lab[i] = labels ? labels[i] : (int64_t)i;
        }
        std::vector<int> idx(n);
        std::iota(idx.begin(), idx.end(), 0);
        root = _build(X, lab, idx);
        if (root) root->parent = nullptr;
        _fix_n(root);
        _fix_bb(root);
    }

    ~RCTree() { delete root; }

    // ── codisp: walk UP via parent pointers ──
    double codisp(int64_t index) const {
        auto it = leaves.find(index);
        if (it == leaves.end()) return 0.0;
        const Node* node = it->second;
        if (node == root || !node->parent) return 0.0;
        double best = 0.0;
        const Node* cur = node;
        while (cur->parent) {
            const Branch* par = static_cast<const Branch*>(cur->parent);
            const Node* sib = (par->left == cur) ? par->right : par->left;
            if (sib && cur->n > 0) {
                double r = (double)sib->n / (double)cur->n;
                if (r > best) best = r;
            }
            cur = par;
        }
        return best;
    }

    // ── insert_point ──
    Leaf* insert_point(const std::vector<double>& pt, int64_t index) {
        if (!root) {
            Leaf* lf = _new_leaf(pt, index);
            root = lf;
            ndim = (int)pt.size();
            return lf;
        }
        Node* node = root;
        Node* par = nullptr;
        bool go_left = true;

        for (int iter = 0; iter < 10000; iter++) {
            std::vector<double> lo(ndim), hi(ndim);
            double span_sum = 0;
            for (int j = 0; j < ndim; j++) {
                lo[j] = std::min(node->bb_lo[j], pt[j]);
                hi[j] = std::max(node->bb_hi[j], pt[j]);
                span_sum += hi[j] - lo[j];
            }
            if (span_sum <= 0) break;

            std::uniform_real_distribution<double> ud(0.0, span_sum);
            double r = ud(rng_);
            double cum = 0;
            int cdim = ndim - 1;
            for (int j = 0; j < ndim; j++) {
                cum += hi[j] - lo[j];
                if (cum >= r) { cdim = j; break; }
            }
            double cval = lo[cdim] + cum - r;

            if (cval <= node->bb_lo[cdim] || cval >= node->bb_hi[cdim]) {
                Leaf* lf = _new_leaf(pt, index);
                Branch* br = new Branch();
                br->q = cdim; br->p = cval;
                if (cval <= node->bb_lo[cdim]) {
                    br->left = lf; br->right = node;
                } else {
                    br->left = node; br->right = lf;
                }
                lf->parent = br;
                node->parent = br;
                br->parent = par;
                br->n = lf->n + node->n;
                br->bb_lo.resize(ndim); br->bb_hi.resize(ndim);
                for (int j = 0; j < ndim; j++) {
                    br->bb_lo[j] = std::min(lf->bb_lo[j], node->bb_lo[j]);
                    br->bb_hi[j] = std::max(lf->bb_hi[j], node->bb_hi[j]);
                }
                if (!par) { root = br; }
                else {
                    Branch* pp = static_cast<Branch*>(par);
                    if (go_left) pp->left = br; else pp->right = br;
                }
                Node* up = par;
                while (up) {
                    up->n += 1;
                    for (int j = 0; j < ndim; j++) {
                        up->bb_lo[j] = std::min(up->bb_lo[j], pt[j]);
                        up->bb_hi[j] = std::max(up->bb_hi[j], pt[j]);
                    }
                    up = up->parent;
                }
                return lf;
            }
            Branch* b = static_cast<Branch*>(node);
            par = node;
            if (pt[b->q] <= b->p) { node = b->left; go_left = true; }
            else                   { node = b->right; go_left = false; }
        }
        return nullptr;
    }

    // ── forget_point ──
    void forget_point(int64_t index) {
        auto it = leaves.find(index);
        if (it == leaves.end()) return;
        Leaf* leaf = it->second;
        leaves.erase(it);
        if (leaf == root) { root = nullptr; delete leaf; return; }

        Branch* par = static_cast<Branch*>(leaf->parent);
        Node* sib = (par->left == leaf) ? par->right : par->left;

        // detach children so ~Branch won't double-delete
        if (par->left == sib) par->left = nullptr; else par->right = nullptr;
        if (par->left == leaf) par->left = nullptr; else par->right = nullptr;

        Node* gp = par->parent;
        sib->parent = gp;
        if (!gp) {
            root = sib;
        } else {
            Branch* gpb = static_cast<Branch*>(gp);
            if (gpb->left == par) gpb->left = sib;
            else                  gpb->right = sib;
        }
        Node* up = gp;
        while (up) { up->n -= 1; up = up->parent; }
        delete par;
        delete leaf;
    }

    std::vector<int64_t> get_leaf_indices() const {
        std::vector<int64_t> out;
        out.reserve(leaves.size());
        for (auto& [k, v] : leaves) out.push_back(k);
        return out;
    }

private:
    mutable std::mt19937_64 rng_;

    Leaf* _new_leaf(const std::vector<double>& pt, int64_t index) {
        Leaf* lf = new Leaf();
        lf->point = pt; lf->idx = index; lf->n = 1;
        lf->bb_lo = pt; lf->bb_hi = pt;
        leaves[index] = lf;
        return lf;
    }

    Node* _build(const std::vector<std::vector<double>>& X,
                 const std::vector<int64_t>& lab,
                 const std::vector<int>& idx) {
        if (idx.empty()) return nullptr;
        if (idx.size() == 1)
            return _new_leaf(X[idx[0]], lab[idx[0]]);

        std::vector<double> lo(ndim, 1e300), hi(ndim, -1e300);
        for (int i : idx)
            for (int j = 0; j < ndim; j++) {
                if (X[i][j] < lo[j]) lo[j] = X[i][j];
                if (X[i][j] > hi[j]) hi[j] = X[i][j];
            }
        double total = 0;
        std::vector<double> span(ndim);
        for (int j = 0; j < ndim; j++) { span[j] = hi[j]-lo[j]; total += span[j]; }
        if (total <= 0) {
            Leaf* lf = _new_leaf(X[idx[0]], lab[idx[0]]);
            lf->n = (int64_t)idx.size();
            for (size_t k = 1; k < idx.size(); k++) leaves[lab[idx[k]]] = lf;
            return lf;
        }

        std::uniform_real_distribution<double> ud(0.0, total);
        double r = ud(rng_);
        int q = 0; double cum = 0;
        for (int j = 0; j < ndim; j++) { cum += span[j]; if (cum >= r) { q = j; break; } }

        std::uniform_real_distribution<double> cd(lo[q], hi[q]);
        double p = cd(rng_);

        std::vector<int> L, R;
        for (int i : idx) { if (X[i][q] <= p) L.push_back(i); else R.push_back(i); }
        if (L.empty()) { L.push_back(R.back()); R.pop_back(); }
        if (R.empty()) { R.push_back(L.back()); L.pop_back(); }

        Branch* br = new Branch();
        br->q = q; br->p = p;
        br->left  = _build(X, lab, L);
        br->right = _build(X, lab, R);
        if (br->left)  br->left->parent  = br;
        if (br->right) br->right->parent = br;
        return br;
    }

    int64_t _fix_n(Node* node) {
        if (!node) return 0;
        if (node->is_leaf()) return node->n;
        Branch* b = static_cast<Branch*>(node);
        b->n = _fix_n(b->left) + _fix_n(b->right);
        return b->n;
    }

    void _fix_bb(Node* node) {
        if (!node) return;
        if (node->is_leaf()) return;
        Branch* b = static_cast<Branch*>(node);
        _fix_bb(b->left); _fix_bb(b->right);
        b->bb_lo.resize(ndim); b->bb_hi.resize(ndim);
        for (int j = 0; j < ndim; j++) {
            b->bb_lo[j] = std::min(b->left->bb_lo[j], b->right->bb_lo[j]);
            b->bb_hi[j] = std::max(b->left->bb_hi[j], b->right->bb_hi[j]);
        }
    }
};

} // namespace rrcf
