#!/usr/bin/env python3
"""
train_rrcf_gpu_mp_v3.py  – Cache-Pattern + Cell-ID Validation (v4.0)
========================================================
Source of truth  : cell_meta/serving_<sid>_rrcf.pkl   (per-cell)
Training data    : training_data/X_<sid>.npz          (per-cell)
Detection cache  : combined_meta.pkl                  (rebuilt after training)

Layout:
  model/
  ├── cell_meta/                  ← per-cell .pkl (source of truth)
  │   ├── serving_439061_rrcf.pkl
  │   └── ...
  ├── training_data/              ← per-cell .npz
  │   ├── X_439061.npz
  │   └── ...
  └── combined_meta.pkl           ← CACHE (rebuilt post-training)

Safe for continuous retraining – crash only loses 1 cell.
Detection reads combined_meta.pkl for fast 1-file load.
"""

# ── Suppress warnings BEFORE anything else ──
import os as _os
_os.environ["PYTHONWARNINGS"] = "ignore::UserWarning,ignore::DeprecationWarning"

# ── GPU activation (must be before pandas import) ──
if _os.environ.get("USE_CUDF_PANDAS", "0") == "1":
    try:
        import cudf.pandas
        cudf.pandas.install()
        print("[GPU] cudf.pandas activated -- pandas ops will use GPU where possible")
    except Exception as _e:
        print(f"[GPU] cudf.pandas not available ({_e}), falling back to CPU pandas")

import warnings
warnings.filterwarnings("ignore")

import os
import sys
import argparse
import time
from collections import defaultdict, Counter
import gc
import glob
import traceback

import pandas as pd
import numpy as np
import joblib

# ── C++ RRCF backend (25x faster) with Python fallback ──
sys.path.insert(0, '/tmp/rrcf_build')
try:
    import _rrcf_core
    USE_CPP_RRCF = True
    print("[C++ RRCF] _rrcf_core loaded — using C++ backend (25x faster)")
except ImportError:
    USE_CPP_RRCF = False
    print("[C++ RRCF] _rrcf_core not found — falling back to Python rrcf")
    import rrcf

try:
    from tqdm import tqdm
except Exception:
    tqdm = None

try:
    import cloudpickle
except Exception:
    cloudpickle = None


# ─────────────────────────────────────────────────────────────────────────────
# neighbor columns
# ─────────────────────────────────────────────────────────────────────────────
def get_neighbor_columns():
    nbr_id_cols   = ['nbr_cell_1_id','nbr_cell_2_id','nbr_cell_3_id','nbr_cell_4_id']
    nbr_rsrp_cols = ['nbr_cell_1_rsrp','nbr_cell_2_rsrp','nbr_cell_3_rsrp','nbr_cell_4_rsrp']
    nbr_rsrq_cols = ['nbr_cell_1_rsrq','nbr_cell_2_rsrq','nbr_cell_3_rsrq','nbr_cell_4_rsrq']
    return nbr_id_cols, nbr_rsrp_cols, nbr_rsrq_cols


# ─────────────────────────────────────────────────────────────────────────────
# cell-id validation helpers (same logic as detection script)
# ─────────────────────────────────────────────────────────────────────────────
def normalize_cell_id(v):
    if pd.isna(v): return ''
    s = str(v).strip()
    if s == '' or s.lower() == 'nan': return ''
    return s.split('.')[0]


def load_valid_global_cellids(cell_details_file):
    """Load valid Global_Cellid values from Cell_Details file."""
    if not cell_details_file or not os.path.exists(cell_details_file):
        return set()
    ext = os.path.splitext(cell_details_file)[1].lower()
    try:
        df = pd.read_csv(cell_details_file, dtype=str, low_memory=False) if ext == '.csv' else pd.read_excel(cell_details_file, dtype=str, engine='openpyxl')
    except Exception:
        try:
            df = pd.read_excel(cell_details_file, dtype=str)
        except Exception:
            return set()
    cols = {str(c).strip().lower(): c for c in df.columns}
    raw_col = cols.get('global_cellid')
    if raw_col is None:
        return set()
    valid = set()
    for v in df[raw_col]:
        n = normalize_cell_id(v)
        if n:
            valid.add(n)
    print(f"Loaded {len(valid)} valid Global_Cellid values from {cell_details_file}")
    return valid


# ─────────────────────────────────────────────────────────────────────────────
# datetime helpers
# ─────────────────────────────────────────────────────────────────────────────
def parse_series_datetime(series, fmt=None):
    if fmt:
        return pd.to_datetime(series, format=fmt, errors='coerce')
    return pd.to_datetime(series, errors='coerce')


def row_in_window(ts, start_ts, end_ts):
    if pd.isna(ts):
        return False
    if start_ts is not None and ts < start_ts:
        return False
    if end_ts is not None and ts > end_ts:
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# CSV chunked reader with progress
# ─────────────────────────────────────────────────────────────────────────────
def iter_csv_chunks_with_progress(csv_path, chunk_size, desc):
    if tqdm is None:
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size, dtype=str, low_memory=False):
            yield chunk
        return
    try:
        total_bytes = os.path.getsize(csv_path)
    except Exception:
        total_bytes = None
    if not total_bytes:
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size, dtype=str, low_memory=False):
            yield chunk
        return
    with open(csv_path, 'rb') as f:
        reader = pd.read_csv(f, chunksize=chunk_size, dtype=str, low_memory=False)
        pbar = tqdm(total=total_bytes, desc=desc, unit='B', unit_scale=True)
        last_pos = 0
        try:
            for chunk in reader:
                try:
                    pos = f.tell()
                    if pos > last_pos:
                        pbar.update(pos - last_pos)
                        last_pos = pos
                except Exception:
                    pass
                yield chunk
        finally:
            if last_pos < total_bytes:
                pbar.update(total_bytes - last_pos)
            pbar.close()


# ─────────────────────────────────────────────────────────────────────────────
# schema normalization
# ─────────────────────────────────────────────────────────────────────────────
def normalize_training_chunk(chunk, serving_col='serving_cell_id'):
    if serving_col not in chunk.columns and {'enodebid','cellid'}.issubset(set(chunk.columns)):
        enb = pd.to_numeric(chunk['enodebid'], errors='coerce')
        cid = pd.to_numeric(chunk['cellid'], errors='coerce')
        sid = (enb * 256.0) + cid
        chunk[serving_col] = sid.round().astype('Int64').astype(str)
        chunk.loc[(enb.isna()) | (cid.isna()), serving_col] = np.nan
    aliases = {
        'nbr_cell_1_id':'eutrancellid1','nbr_cell_2_id':'eutrancellid2',
        'nbr_cell_3_id':'eutrancellid3',
        'nbr_cell_1_rsrp':'avg_dlrsrp_d1','nbr_cell_2_rsrp':'avg_dlrsrp_d2',
        'nbr_cell_3_rsrp':'avg_dlrsrp_d3',
        'nbr_cell_1_rsrq':'avg_dlrsrq_d1','nbr_cell_2_rsrq':'avg_dlrsrq_d2',
        'nbr_cell_3_rsrq':'avg_dlrsrq_d3',
    }
    for dst, src in aliases.items():
        if dst not in chunk.columns and src in chunk.columns:
            chunk[dst] = chunk[src]
    return chunk


# ─────────────────────────────────────────────────────────────────────────────
# PASS 1: neighbor counts
# ─────────────────────────────────────────────────────────────────────────────
def compute_neighbor_counts(train_file, serving_col='serving_cell_id', chunk_size=200000,
                            datetime_col=None, start_ts=None, end_ts=None, datetime_fmt=None,
                valid_ids=None):
    nbr_id_cols, _, _ = get_neighbor_columns()
    counts = defaultdict(Counter)
    for chunk in iter_csv_chunks_with_progress(train_file, chunk_size, desc='PASS1 neighbor counts'):
        chunk = normalize_training_chunk(chunk, serving_col=serving_col)
        if datetime_col and datetime_col in chunk.columns:
            parsed = parse_series_datetime(chunk[datetime_col].astype(str), fmt=datetime_fmt)
            chunk['_dt_parsed'] = parsed
            if start_ts is not None or end_ts is not None:
                mask = chunk['_dt_parsed'].apply(lambda t: row_in_window(t, start_ts, end_ts))
                chunk = chunk[mask]
        if chunk.shape[0] == 0:
            del chunk; gc.collect(); continue
        for col in nbr_id_cols:
            if col not in chunk.columns:
                continue
            tmp = chunk[[serving_col, col]].dropna()
            tmp = tmp[tmp[col].astype(str).str.strip() != '']
            for sid, nid in zip(tmp[serving_col].values, tmp[col].values):
                counts[str(sid)][str(nid)] += 1
        del chunk; gc.collect()
    return counts


def build_topk_map(neighbor_counts, top_k):
    topk = {}
    for sid, counter in neighbor_counts.items():
        ordered = [nid for nid, _ in counter.most_common()]
        if top_k and top_k > 0:
            ordered = ordered[:top_k]
        topk[sid] = ordered
    return topk


# ─────────────────────────────────────────────────────────────────────────────
# PRELOAD CSV into memory
# ─────────────────────────────────────────────────────────────────────────────
def preload_csv(train_file, serving_col='serving_cell_id', chunk_size=200000,
                datetime_col=None, start_ts=None, end_ts=None, datetime_fmt=None,
                valid_ids=None):
    print("PRELOAD: Reading entire CSV into memory (one-time cost)...")
    chunks = []
    for chunk in iter_csv_chunks_with_progress(train_file, chunk_size, desc='PRELOAD CSV'):
        chunk = normalize_training_chunk(chunk, serving_col=serving_col)
        if datetime_col and datetime_col in chunk.columns:
            parsed = parse_series_datetime(chunk[datetime_col].astype(str), fmt=datetime_fmt)
            chunk['_dt_parsed'] = parsed
            if start_ts is not None or end_ts is not None:
                mask = chunk['_dt_parsed'].apply(lambda t: row_in_window(t, start_ts, end_ts))
                chunk = chunk[mask]
        if chunk.shape[0] > 0:
            chunks.append(chunk)
    if len(chunks) == 0:
        print("PRELOAD: No data after filtering!")
        return {}
    df_all = pd.concat(chunks, ignore_index=True)
    del chunks; gc.collect()
    df_all[serving_col] = df_all[serving_col].astype(str).str.split('.').str[0]
    nbr_id_cols, _, _ = get_neighbor_columns()
    for col in nbr_id_cols:
        if col in df_all.columns:
            df_all[col] = df_all[col].astype(str).str.strip().str.split('.').str[0]
            df_all.loc[df_all[col].isin(['', 'nan', 'None', 'NaN', 'none']), col] = ''
    total_rows = df_all.shape[0]

    # ── v4: Remove MR records with invalid cell IDs (same logic as detection) ──
    if valid_ids and len(valid_ids) > 0:
        nbr_check_cols = [serving_col] + [col for col in nbr_id_cols if col in df_all.columns]
        invalid_mask = pd.Series(False, index=df_all.index)
        for col in nbr_check_cols:
            if col not in df_all.columns:
                continue
            nv = df_all[col].apply(normalize_cell_id)
            bad = (nv != '') & (~nv.isin(valid_ids))
            invalid_mask = invalid_mask | bad
        removed_count = int(invalid_mask.sum())
        if removed_count > 0:
            df_all = df_all.loc[~invalid_mask].copy()
            print(f"  Removed {removed_count:,} invalid cell-id rows "
                  f"({total_rows:,} -> {df_all.shape[0]:,})")
            total_rows = df_all.shape[0]
        else:
            print(f"  All {total_rows:,} rows have valid cell IDs")

    grouped = {str(sid): grp for sid, grp in df_all.groupby(serving_col, sort=False)}
    del df_all; gc.collect()
    print(f"PRELOAD: {total_rows:,} rows loaded, {len(grouped)} serving cells in memory.")
    return grouped


# ─────────────────────────────────────────────────────────────────────────────
# VECTORIZED feature builder
# ─────────────────────────────────────────────────────────────────────────────
def build_features_from_df(df, neighbor_order, fill_value=-999.0, max_rows=None):
    nbr_id_cols, nbr_rsrp_cols, nbr_rsrq_cols = get_neighbor_columns()
    K = len(neighbor_order)
    if K == 0:
        return np.zeros((0, 0))
    if max_rows and df.shape[0] > max_rows:
        df = df.head(max_rows)
    n = df.shape[0]
    nid_to_idx = {str(nid): i for i, nid in enumerate(neighbor_order)}
    presence = np.zeros((n, K), dtype=np.float64)
    rsrp_arr = np.full((n, K), fill_value, dtype=np.float64)
    rsrq_arr = np.full((n, K), fill_value, dtype=np.float64)

    for id_col, rp_col, rq_col in zip(nbr_id_cols, nbr_rsrp_cols, nbr_rsrq_cols):
        if id_col not in df.columns:
            continue
        nids = df[id_col].values
        rp_vals = pd.to_numeric(df[rp_col], errors='coerce').values if rp_col in df.columns else np.full(n, np.nan)
        rq_vals = pd.to_numeric(df[rq_col], errors='coerce').values if rq_col in df.columns else np.full(n, np.nan)
        for row_idx in range(n):
            nid = str(nids[row_idx])
            if nid == '' or nid == 'nan':
                continue
            col_idx = nid_to_idx.get(nid)
            if col_idx is not None:
                presence[row_idx, col_idx] = 1.0
                rp = rp_vals[row_idx]
                rq = rq_vals[row_idx]
                if not np.isnan(rp):
                    rsrp_arr[row_idx, col_idx] = rp
                if not np.isnan(rq):
                    rsrq_arr[row_idx, col_idx] = rq
    return np.hstack([presence, rsrp_arr, rsrq_arr])


# ─────────────────────────────────────────────────────────────────────────────
# C++ accelerated tree building with Python fallback
# ─────────────────────────────────────────────────────────────────────────────
def _build_single_tree_jittered(X, tree_size, seed):
    """Build one RCTree with tiny jitter (Python fallback only)."""
    rng = np.random.RandomState(seed)
    n = X.shape[0]
    use_size = min(tree_size, max(2, n))

    if n <= use_size:
        X_for = X + rng.normal(scale=1e-9, size=X.shape)
        X_for = np.ascontiguousarray(X_for, dtype=np.float64)
        labels = list(range(n))
    else:
        idxs = rng.choice(n, size=use_size, replace=False)
        X_for = X[idxs] + rng.normal(scale=1e-9, size=(use_size, X.shape[1]))
        X_for = np.ascontiguousarray(X_for, dtype=np.float64)
        labels = [int(i) for i in idxs.tolist()]

    try:
        return rrcf.RCTree(X_for, index_labels=labels)
    except Exception:
        X_for = X_for + rng.normal(scale=1e-6, size=X_for.shape)
        return rrcf.RCTree(X_for, index_labels=labels)


def build_forest_sequential(X, num_trees=150, tree_size=1024, random_seed=0):
    """Build forest — uses C++ backend if available, else Python rrcf."""
    if X is None or X.size == 0:
        return []
    X = np.ascontiguousarray(X, dtype=np.float64)

    # ── C++ fast path ──
    if USE_CPP_RRCF:
        rng = np.random.RandomState(random_seed)
        forest = []
        use_size = int(min(tree_size, max(2, X.shape[0])))
        n = X.shape[0]
        while len(forest) < num_trees:
            seed = int(rng.randint(0, 2**31))
            if n <= use_size:
                labels = np.arange(n, dtype=np.int64)
                tree = _rrcf_core.RCTree(X, labels, seed)
            else:
                idxs = rng.choice(n, size=use_size, replace=False)
                X_sub = np.ascontiguousarray(X[idxs], dtype=np.float64)
                labels = idxs.astype(np.int64)
                tree = _rrcf_core.RCTree(X_sub, labels, seed)
            forest.append(tree)
        return forest[:num_trees]

    # ── Python fallback ──
    rng = np.random.RandomState(random_seed)
    seeds = rng.randint(0, 2**31, size=num_trees).tolist()
    forest = []
    for s in seeds:
        try:
            tree = _build_single_tree_jittered(X, tree_size, s)
            forest.append(tree)
        except Exception:
            pass
    return forest


# ─────────────────────────────────────────────────────────────────────────────
# codisp computation (C++ or Python)
# ─────────────────────────────────────────────────────────────────────────────
def compute_mean_std_codisp(forest, n):
    """Compute mean & std of average collusive displacement."""
    total_codisp = np.zeros(n, dtype=np.float64)
    index_counts = np.zeros(n, dtype=np.int64)

    for tree in forest:
        try:
            if USE_CPP_RRCF and hasattr(tree, 'get_leaf_indices'):
                for idx in tree.get_leaf_indices():
                    idx_int = int(idx)
                    if 0 <= idx_int < n:
                        total_codisp[idx_int] += tree.codisp(idx)
                        index_counts[idx_int] += 1
            else:
                for leaf in tree.leaves:
                    try:
                        idx = int(leaf)
                    except Exception:
                        continue
                    if 0 <= idx < n:
                        total_codisp[idx] += tree.codisp(leaf)
                        index_counts[idx] += 1
        except Exception:
            pass

    mask = index_counts > 0
    if mask.sum() == 0:
        return 0.0, 0.0
    avg = total_codisp[mask] / index_counts[mask]
    return float(avg.mean()), float(np.std(avg, ddof=0))


# ─────────────────────────────────────────────────────────────────────────────
# neighbor stats
# ─────────────────────────────────────────────────────────────────────────────
def compute_neighbor_stats(X, neighbor_order, fill_value=-999.0, min_obs=1):
    stats = {}
    K = len(neighbor_order)
    if K == 0 or X is None or X.size == 0:
        return stats
    for i, nid in enumerate(neighbor_order):
        presence_mask = X[:, i] == 1
        count = int(presence_mask.sum())
        if count < min_obs:
            continue
        rsrp_vals = X[presence_mask, K + i]
        rsrq_vals = X[presence_mask, 2*K + i]
        valid_rsrp = rsrp_vals[rsrp_vals != fill_value]
        valid_rsrq = rsrq_vals[rsrq_vals != fill_value]
        if valid_rsrp.size == 0 and valid_rsrq.size == 0:
            continue
        stats[str(nid)] = {
            'count': count,
            'rsrp_mean': float(np.mean(valid_rsrp)) if valid_rsrp.size > 0 else None,
            'rsrp_std':  float(np.std(valid_rsrp, ddof=0)) if valid_rsrp.size > 0 else None,
            'rsrq_mean': float(np.mean(valid_rsrq)) if valid_rsrq.size > 0 else None,
            'rsrq_std':  float(np.std(valid_rsrq, ddof=0)) if valid_rsrq.size > 0 else None,
        }
    return stats


def save_meta(meta, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(meta, path)


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE REBUILD: Rebuild combined_meta.pkl from per-cell .pkl files
# ═══════════════════════════════════════════════════════════════════════════════
def rebuild_combined_cache(model_dir):
    """Rebuild combined_meta.pkl from all per-cell .pkl files in cell_meta/."""
    cell_meta_dir = os.path.join(model_dir, 'cell_meta')
    cache_path = os.path.join(model_dir, 'combined_meta.pkl')

    if not os.path.isdir(cell_meta_dir):
        print(f"[CACHE] No cell_meta/ directory found at {cell_meta_dir}")
        return 0

    pkl_files = glob.glob(os.path.join(cell_meta_dir, 'serving_*_rrcf.pkl'))
    if not pkl_files:
        print("[CACHE] No per-cell .pkl files found — skipping cache rebuild")
        return 0

    print(f"[CACHE] Rebuilding combined_meta.pkl from {len(pkl_files)} per-cell .pkl files...")
    t0 = time.time()
    combined = {}
    errors = 0
    for pkl_path in pkl_files:
        try:
            sid = os.path.basename(pkl_path).replace('serving_', '').replace('_rrcf.pkl', '')
            meta = joblib.load(pkl_path)
            combined[sid] = meta
        except Exception:
            errors += 1

    # Atomic write: write to temp file first, then rename
    tmp_path = cache_path + '.tmp'
    joblib.dump(combined, tmp_path)
    os.replace(tmp_path, cache_path)  # atomic on most OS

    elapsed = time.time() - t0
    print(f"[CACHE] Rebuilt combined_meta.pkl: {len(combined)} cells, "
          f"{errors} errors, {elapsed:.1f}s")
    print(f"[CACHE] Saved: {cache_path} ({os.path.getsize(cache_path)/1024/1024:.1f} MB)")
    return len(combined)


# ─────────────────────────────────────────────────────────────────────────────
# TRAIN ONE CELL (worker — receives only numpy array, not DataFrame!)
# ─────────────────────────────────────────────────────────────────────────────
def _train_one_cell(sid, neighbor_order, X, args_dict):
    """Train a single serving cell end-to-end.
    Saves per-cell .pkl to cell_meta/ and per-cell .npz to training_data/.
    Returns result tuple or None."""
    cell_t0 = time.time()

    fill_value = args_dict['fill_value']
    num_trees = args_dict['num_trees']
    tree_size = args_dict['tree_size']
    random_seed = args_dict['random_seed']
    model_dir = args_dict['model_dir']
    min_neighbor_obs = args_dict.get('min_neighbor_obs', 1)
    save_forest_mode = args_dict.get('save_forest', 'none')

    # ── Directory paths (Cache Pattern) ──
    cell_meta_dir = os.path.join(model_dir, 'cell_meta')
    training_data_dir = os.path.join(model_dir, 'training_data')
    os.makedirs(cell_meta_dir, exist_ok=True)
    os.makedirs(training_data_dir, exist_ok=True)

    # Build forest (sequential — no subprocess overhead inside worker)
    forest = build_forest_sequential(X, num_trees=num_trees, tree_size=tree_size,
                                     random_seed=random_seed)
    if len(forest) == 0:
        return None

    # Codisp
    mean_c, std_c = compute_mean_std_codisp(forest, X.shape[0])

    # Neighbor stats
    neighbor_stats = compute_neighbor_stats(X, neighbor_order,
                                            fill_value=fill_value,
                                            min_obs=min_neighbor_obs)

    # ── Save training data (.npz) to training_data/ ──
    x_path = os.path.join(training_data_dir, f"X_{sid}.npz")
    np.savez_compressed(x_path, X=X)

    # ── Build metadata ──
    meta = {
        'serving_cell_id': str(sid),
        'neighbor_order': neighbor_order,
        'K': len(neighbor_order),
        'fill_value': fill_value,
        'training_X_path': x_path,
        'mean_codisp': mean_c,
        'std_codisp': std_c,
        'neighbor_stats': neighbor_stats,
        'params': {'num_trees': num_trees, 'tree_size': tree_size,
                   'random_seed': random_seed}
    }

    if save_forest_mode == 'cloudpickle' and cloudpickle is not None:
        fp = os.path.join(model_dir, f"serving_{sid}_forest.pkl")
        with open(fp, 'wb') as f:
            cloudpickle.dump(forest, f)
        meta['forest_path'] = fp

    # ── Save per-cell meta (.pkl) to cell_meta/ (source of truth) ──
    meta_path = os.path.join(cell_meta_dir, f"serving_{sid}_rrcf.pkl")
    save_meta(meta, meta_path)
    elapsed = time.time() - cell_t0

    return (str(sid), meta_path, elapsed, X.shape[0], X.shape[1],
            len(forest), mean_c, std_c)


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--train-file',        default='../data/train_70.csv')
    p.add_argument('--model-dir',         default='../model/model_150_1024')
    p.add_argument('--datetime-col',      default='time_timestamp')
    p.add_argument('--datetime-format',   default=None)
    p.add_argument('--train-start',       default=None)
    p.add_argument('--train-end',         default=None)
    p.add_argument('--history-days',      type=int, default=None)
    p.add_argument('--top-k',             type=int, default=0)
    p.add_argument('--num-trees',         type=int, default=150)
    p.add_argument('--tree-size',         type=int, default=1024)
    p.add_argument('--min-samples',       type=int, default=50)
    p.add_argument('--chunk-size',        type=int, default=200000)
    p.add_argument('--random-seed',       type=int, default=0)
    p.add_argument('--fill-value',        type=float, default=-999.0)
    p.add_argument('--save-forest',       choices=['none','cloudpickle'], default='none')
    p.add_argument('--min-neighbor-obs',  type=int, default=1)
    p.add_argument('--max-rows-per-cell', type=int, default=None)
    p.add_argument('--n-jobs',            type=int, default=4)
    p.add_argument('--cell-details-file', default='../data/Cell_Details.csv',
                   help='CSV/XLSX with valid Global_Cellid column for filtering')
    p.add_argument('--skip-cache-rebuild', action='store_true',
                   help='Skip rebuilding combined_meta.pkl after training')
    args = p.parse_args()

    os.makedirs(args.model_dir, exist_ok=True)

    start_ts = pd.to_datetime(args.train_start) if args.train_start else None
    end_ts   = pd.to_datetime(args.train_end)   if args.train_end   else None

    if args.history_days:
        max_ts = None
        for chunk in iter_csv_chunks_with_progress(args.train_file, args.chunk_size, desc='Scan max datetime'):
            if args.datetime_col in chunk.columns:
                parsed = parse_series_datetime(chunk[args.datetime_col].astype(str), fmt=args.datetime_format)
                if parsed.notna().any():
                    cmax = parsed.max()
                    if max_ts is None or cmax > max_ts:
                        max_ts = cmax
            del chunk; gc.collect()
        if max_ts is None:
            raise ValueError("history-days set but no valid datetimes found.")
        end_ts   = max_ts
        start_ts = end_ts - pd.Timedelta(days=int(args.history_days))

    # ── PASS 1: neighbor counts ──
    print("PASS1: computing neighbor counts (time window)", start_ts, end_ts)
    neighbor_counts = compute_neighbor_counts(
        args.train_file, chunk_size=args.chunk_size,
        datetime_col=args.datetime_col, start_ts=start_ts, end_ts=end_ts,
        datetime_fmt=args.datetime_format)
    print(f"Found {len(neighbor_counts)} serving cells")
    topk_map = build_topk_map(neighbor_counts, args.top_k)

    # ── Load valid cell IDs for filtering (v4) ──
    valid_ids = load_valid_global_cellids(args.cell_details_file)

    # ── PRELOAD CSV (one-time) ──
    serving_groups = preload_csv(
        args.train_file, chunk_size=args.chunk_size,
        datetime_col=args.datetime_col, start_ts=start_ts, end_ts=end_ts,
        datetime_fmt=args.datetime_format,
        valid_ids=valid_ids)

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 1: Pre-compute ALL feature matrices (serial, from memory — fast)
    # ═══════════════════════════════════════════════════════════════════════════
    print(f"\nPHASE 1: Pre-computing features for {len(topk_map)} cells...")
    phase1_t0 = time.time()
    tasks = []
    skipped = 0

    cell_items = list(topk_map.items())
    if tqdm is not None:
        cell_items_bar = tqdm(cell_items, desc="Building features", unit="cell")
    else:
        cell_items_bar = cell_items

    for sid, neighbor_order in cell_items_bar:
        if len(neighbor_order) == 0:
            skipped += 1
            continue
        df_serv = serving_groups.get(str(sid))
        if df_serv is None or df_serv.shape[0] == 0:
            skipped += 1
            continue

        X = build_features_from_df(df_serv, neighbor_order,
                                   fill_value=args.fill_value,
                                   max_rows=args.max_rows_per_cell)
        if X.size == 0 or X.shape[0] < args.min_samples:
            skipped += 1
            continue

        # Preprocess: replace NaN/Inf (keep ALL columns for correct index math)
        X = np.where(np.isfinite(X), X, args.fill_value).astype(np.float64)
        if X.shape[1] == 0:
            skipped += 1
            continue
        X = np.ascontiguousarray(X, dtype=np.float64)

        tasks.append((str(sid), neighbor_order, X))

    # Free preloaded DataFrames — we only need numpy arrays now
    del serving_groups
    gc.collect()

    phase1_time = time.time() - phase1_t0
    print(f"PHASE 1 done: {len(tasks)} cells ready, {skipped} skipped, took {phase1_time:.1f}s")

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 2: Train forests in PARALLEL (loky processes — true multi-core)
    # ═══════════════════════════════════════════════════════════════════════════
    n_jobs = args.n_jobs
    if n_jobs <= 0:
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        n_jobs = max(1, cpu_count + 1 + n_jobs)
    n_jobs = max(1, n_jobs)

    args_dict = {
        'fill_value': args.fill_value,
        'num_trees': args.num_trees,
        'tree_size': args.tree_size,
        'random_seed': args.random_seed,
        'model_dir': args.model_dir,
        'min_neighbor_obs': args.min_neighbor_obs,
        'save_forest': args.save_forest,
    }

    print(f"\nPHASE 2: Training {len(tasks)} cells using {n_jobs} parallel workers (loky)...")
    phase2_t0 = time.time()

    results = joblib.Parallel(n_jobs=n_jobs, backend='loky', verbose=10)(
        joblib.delayed(_train_one_cell)(sid, neighbor_order, X, args_dict)
        for sid, neighbor_order, X in tasks
    )

    # ── Report results ──
    phase2_time = time.time() - phase2_t0
    total = 0
    for r in results:
        if r is not None:
            sid, meta_path, elapsed, n_rows, n_dim, n_trees, mean_c, std_c = r
            total += 1

    # ═══════════════════════════════════════════════════════════════════════════
    # PHASE 3: Rebuild combined_meta.pkl cache
    # ═══════════════════════════════════════════════════════════════════════════
    phase3_t0 = time.time()
    if not args.skip_cache_rebuild:
        cache_count = rebuild_combined_cache(args.model_dir)
    else:
        print("[CACHE] Skipped cache rebuild (--skip-cache-rebuild)")
        cache_count = 0
    phase3_time = time.time() - phase3_t0

    total_elapsed = phase1_time + phase2_time + phase3_time
    print(f"\n{'='*60}")
    print(f"DONE. Saved {total}/{len(tasks)} models (Cache Pattern v3)")
    print(f"  Phase 1 (features)     : {phase1_time:.0f}s")
    print(f"  Phase 2 (training)     : {phase2_time:.0f}s  ({n_jobs} workers)")
    print(f"  Phase 3 (cache rebuild): {phase3_time:.0f}s  ({cache_count} cells cached)")
    print(f"  TOTAL                  : {total_elapsed:.0f}s ({total_elapsed/60:.1f} min)")
    print(f"  Layout:")
    print(f"    cell_meta/     → {total} per-cell .pkl (source of truth)")
    print(f"    training_data/ → {total} per-cell .npz")
    print(f"    combined_meta.pkl → detection cache")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
