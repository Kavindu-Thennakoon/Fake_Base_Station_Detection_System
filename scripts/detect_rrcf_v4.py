#!/usr/bin/env python3
"""
detect_rrcf_v4.py – Cache Pattern + OR-logic detection (v4.0)
=============================================================
Based on detect_rrcf_v3.py (v3.0 Cache Pattern).

v4.0 changes:
  - Vectorized cell-ID validation (30-60x faster on large datasets)
  - Progress bars for PHASE 2 scoring (tqdm)
  - Per-phase timing breakdown
  - Tasks sorted by row count for better load balancing

Expected layout:
  model_dir/
  ├── cell_meta/                ← per-cell .pkl (source of truth)
  ├── training_data/            ← per-cell .npz
  └── combined_meta.pkl         ← CACHE (fast load)
"""

# ── Suppress warnings BEFORE anything else ──
import os as _os
_os.environ["PYTHONWARNINGS"] = "ignore::UserWarning,ignore::DeprecationWarning"

# ── GPU activation (must be before pandas import) ──
if _os.environ.get("USE_CUDF_PANDAS", "0") == "1":
    try:
        import cudf.pandas
        cudf.pandas.install()
        print("[GPU] cudf.pandas activated")
    except Exception as _e:
        print(f"[GPU] cudf.pandas not available ({_e}), falling back to CPU")

import warnings
warnings.filterwarnings("ignore")

import os, sys, argparse, glob, json, csv, gc, time, traceback
from datetime import datetime
from collections import defaultdict

import pandas as pd
import numpy as np
import joblib

# ── C++ RRCF backend ──
sys.path.insert(0, '/tmp/rrcf_build')
try:
    import _rrcf_core
    USE_CPP_RRCF = True
    print("[C++ RRCF] _rrcf_core loaded — 25x faster")
except ImportError:
    USE_CPP_RRCF = False
    print("[C++ RRCF] not found — Python fallback")
    import rrcf


# ── cuDF/cuPy GPU compatibility ──
def _to_pandas(obj):
    """Convert cuDF object to pandas if needed."""
    if hasattr(obj, 'to_pandas'):
        return obj.to_pandas()
    return obj

def _get_xp():
    """Return cupy if available (GPU), else numpy (CPU)."""
    try:
        import cupy as cp
        return cp, True
    except ImportError:
        return np, False

try:
    from tqdm import tqdm
except Exception:
    tqdm = None
try:
    import cloudpickle
except Exception:
    cloudpickle = None


def get_neighbor_columns():
    return (['nbr_cell_1_id','nbr_cell_2_id','nbr_cell_3_id','nbr_cell_4_id'],
            ['nbr_cell_1_rsrp','nbr_cell_2_rsrp','nbr_cell_3_rsrp','nbr_cell_4_rsrp'],
            ['nbr_cell_1_rsrq','nbr_cell_2_rsrq','nbr_cell_3_rsrq','nbr_cell_4_rsrq'])


def _build_single_tree_jittered(X, tree_size, seed):
    rng = np.random.RandomState(seed)
    n = X.shape[0]
    use_size = int(min(tree_size, max(2, n)))
    if n <= use_size:
        X_j = X + rng.normal(scale=1e-12, size=X.shape)
        return rrcf.RCTree(X_j, index_labels=list(range(n)))
    else:
        idxs = rng.choice(n, size=use_size, replace=False)
        X_sub = X[idxs] + rng.normal(scale=1e-12, size=(use_size, X.shape[1]))
        return rrcf.RCTree(X_sub, index_labels=[int(i) for i in idxs.tolist()])


def build_forest_sequential(X, num_trees=150, tree_size=1024, random_seed=0):
    if X is None or X.size == 0:
        return []
    X = np.ascontiguousarray(X, dtype=np.float64)
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
    rng = np.random.RandomState(random_seed)
    seeds = rng.randint(0, 2**31, size=num_trees).tolist()
    forest = []
    for s in seeds:
        try:
            forest.append(_build_single_tree_jittered(X, tree_size, s))
        except Exception:
            pass
    return forest


def score_batch(forest, X):
    N = X.shape[0]
    if N == 0:
        return np.zeros(0, dtype=np.float64)
    if USE_CPP_RRCF:
        return np.array(_rrcf_core.score_batch(forest, X), dtype=np.float64)
    scores = np.zeros(N, dtype=np.float64)
    counts = np.zeros(N, dtype=np.int64)
    for tree in forest:
        for i in range(N):
            temp_idx = ('__q', i)
            try:
                tree.insert_point(X[i], index=temp_idx)
                scores[i] += tree.codisp(temp_idx)
                counts[i] += 1
            except Exception:
                pass
            finally:
                try:
                    tree.forget_point(temp_idx)
                except Exception:
                    pass
    mask = counts > 0
    scores[mask] /= counts[mask]
    return scores


def compute_neighbor_stats(X, neighbor_order, fill_value=-999.0, min_obs=1):
    stats = {}
    K = len(neighbor_order)
    if K == 0 or X is None or X.size == 0:
        return stats
    for i, nid in enumerate(neighbor_order):
        pm = X[:, i] == 1
        count = int(pm.sum())
        if count < min_obs:
            continue
        rp = X[pm, K+i]; rq = X[pm, 2*K+i]
        vp = rp[rp != fill_value]; vq = rq[rq != fill_value]
        if vp.size == 0 and vq.size == 0:
            continue
        stats[str(nid)] = {
            'count': count,
            'rsrp_mean': float(np.mean(vp)) if vp.size > 0 else None,
            'rsrp_std': float(np.std(vp, ddof=0)) if vp.size > 0 else None,
            'rsrq_mean': float(np.mean(vq)) if vq.size > 0 else None,
            'rsrq_std': float(np.std(vq, ddof=0)) if vq.size > 0 else None,
        }
    return stats


def detect_abnormal_neighbors(feature_vec, meta, z_thresh=2.0, min_std=0.1, fill_value=-999.0):
    neighbor_order = meta.get('neighbor_order', [])
    K = meta.get('K', len(neighbor_order))
    stats = meta.get('neighbor_stats', {}) or {}
    results = []
    eps = 1e-9
    for i, nid in enumerate(neighbor_order):
        if feature_vec[i] != 1:
            continue
        rsrp = feature_vec[K+i]; rsrq = feature_vec[2*K+i]
        sid = str(nid)
        s = stats.get(sid)
        if not s:
            continue
        comp = []; rp_z = 0.0; rq_z = 0.0; abn = False
        if s.get('rsrp_mean') is not None and rsrp != fill_value:
            d = s.get('rsrp_std', 0.0)
            d = d if d > 0 else min_std
            rp_z = abs(rsrp - s['rsrp_mean']) / (d + eps)
            comp.append(rp_z)
            if rp_z > z_thresh: abn = True
        if s.get('rsrq_mean') is not None and rsrq != fill_value:
            d = s.get('rsrq_std', 0.0)
            d = d if d > 0 else min_std
            rq_z = abs(rsrq - s['rsrq_mean']) / (d + eps)
            comp.append(rq_z)
            if rq_z > z_thresh: abn = True
        if not comp:
            continue
        ascore = float(np.sqrt(np.sum(np.square(np.array(comp)))))
        if ascore > z_thresh: abn = True
        if abn:
            results.append({'neighbor_id': sid,
                'rsrp': None if rsrp == fill_value else float(rsrp),
                'rsrq': None if rsrq == fill_value else float(rsrq),
                'rsrp_z': float(rp_z), 'rsrq_z': float(rq_z),
                'neighbor_count': int(s.get('count', 0)),
                'anomaly_score': float(ascore)})
    return sorted(results, key=lambda x: x['anomaly_score'], reverse=True)


def build_features_vectorised(df, neighbor_order, fill_value=-999.0):
    nbr_id, nbr_rp, nbr_rq = get_neighbor_columns()
    K = len(neighbor_order)
    if K == 0:
        return np.zeros((0, 0), dtype=np.float64)
    N = len(df)
    nid_to_pos = {str(nid): pos for pos, nid in enumerate(neighbor_order)}
    pres = np.zeros((N, K), dtype=np.float64)
    rp_arr = np.full((N, K), fill_value, dtype=np.float64)
    rq_arr = np.full((N, K), fill_value, dtype=np.float64)
    for id_col, rp_col, rq_col in zip(nbr_id, nbr_rp, nbr_rq):
        if id_col not in df.columns:
            continue
        raw = df[id_col].astype(str).str.split('.').str[0].str.strip()
        pos_s = raw.map(nid_to_pos)
        valid = pos_s.notna() & df[id_col].notna() & (raw != '') & (raw != 'nan')
        if not valid.any():
            continue
        pv = pos_s[valid].astype(int).values
        ri = np.arange(N)[valid.values]
        pres[ri, pv] = 1.0
        if rp_col in df.columns:
            rv = pd.to_numeric(df[rp_col], errors='coerce').values[valid.values]
            rv[np.isnan(rv)] = fill_value
            rp_arr[ri, pv] = rv
        if rq_col in df.columns:
            rv = pd.to_numeric(df[rq_col], errors='coerce').values[valid.values]
            rv[np.isnan(rv)] = fill_value
            rq_arr[ri, pv] = rv
    return np.ascontiguousarray(np.hstack([pres, rp_arr, rq_arr]), dtype=np.float64)


def normalize_detection_chunk(chunk, serving_col='serving_cell_id'):
    chunk = _to_pandas(chunk)
    if serving_col not in chunk.columns and {'enodebid','cellid'}.issubset(set(chunk.columns)):
        enb = pd.to_numeric(chunk['enodebid'], errors='coerce')
        cid = pd.to_numeric(chunk['cellid'], errors='coerce')
        chunk[serving_col] = ((enb*256)+cid).round().astype('Int64').astype(str)
        chunk.loc[enb.isna()|cid.isna(), serving_col] = np.nan
    aliases = {'nbr_cell_1_id':'eutrancellid1','nbr_cell_2_id':'eutrancellid2',
        'nbr_cell_3_id':'eutrancellid3','nbr_cell_1_rsrp':'avg_dlrsrp_d1',
        'nbr_cell_2_rsrp':'avg_dlrsrp_d2','nbr_cell_3_rsrp':'avg_dlrsrp_d3',
        'nbr_cell_1_rsrq':'avg_dlrsrq_d1','nbr_cell_2_rsrq':'avg_dlrsrq_d2',
        'nbr_cell_3_rsrq':'avg_dlrsrq_d3'}
    for dst, src in aliases.items():
        if dst not in chunk.columns and src in chunk.columns:
            chunk[dst] = chunk[src]
    return chunk


def normalize_cell_id(v):
    if pd.isna(v): return ''
    s = str(v).strip()
    if s == '' or s.lower() == 'nan': return ''
    return s.split('.')[0]


# ═══════════════════════════════════════════════════════════════════════════════
# CACHE PATTERN: Load model metadata
# ═══════════════════════════════════════════════════════════════════════════════
def load_all_meta(model_dir):
    """Load all cell metadata using Cache Pattern priority:
    1. combined_meta.pkl (cache — fast)
    2. cell_meta/*.pkl (source of truth — rebuild)
    3. model_dir/*.pkl (legacy v2 layout — backward compat)
    """
    combined_path = os.path.join(model_dir, 'combined_meta.pkl')
    cell_meta_dir = os.path.join(model_dir, 'cell_meta')

    # Priority 1: combined cache
    if os.path.exists(combined_path):
        print(f"  Loading combined_meta.pkl (cache)...")
        all_meta = joblib.load(combined_path)
        print(f"  Loaded {len(all_meta)} cell models from cache")
        return all_meta

    # Priority 2: per-cell .pkl in cell_meta/
    if os.path.isdir(cell_meta_dir):
        print(f"  Cache not found, rebuilding from cell_meta/*.pkl...")
        all_meta = {}
        for p in glob.glob(os.path.join(cell_meta_dir, 'serving_*_rrcf.pkl')):
            sid = os.path.basename(p).replace('serving_','').replace('_rrcf.pkl','')
            try:
                all_meta[sid] = joblib.load(p)
            except Exception:
                pass
        print(f"  Loaded {len(all_meta)} cell models from per-cell .pkl")
        # Rebuild cache for next time
        if all_meta:
            try:
                joblib.dump(all_meta, combined_path)
                print(f"  Rebuilt combined_meta.pkl cache ({len(all_meta)} cells)")
            except Exception:
                pass
        return all_meta

    # Priority 3: legacy v2 layout (model_dir/*.pkl)
    print(f"  Legacy mode: loading per-cell .pkl from model_dir root...")
    all_meta = {}
    for p in glob.glob(os.path.join(model_dir, 'serving_*_rrcf.pkl')):
        sid = os.path.basename(p).replace('serving_','').replace('_rrcf.pkl','')
        try:
            all_meta[sid] = joblib.load(p)
        except Exception:
            pass
    print(f"  Loaded {len(all_meta)} cell models (legacy layout)")
    return all_meta


# ═══════════════════════════════════════════════════════════════════════════════
# CRITICAL FIX (v2.5): Z-score runs on ALL rows, not just RRCF-flagged
# Detection uses OR logic: RRCF flagged OR z-score flagged
# v3: Worker receives meta dict directly (no file I/O in worker)
# ═══════════════════════════════════════════════════════════════════════════════
def _detect_one_cell(sid, X_detect, dt_raw_list, orig_indices, meta_dict, args_dict):
    """Detect anomalies for one cell. v3: receives meta dict directly."""
    meta = meta_dict
    if not meta:
        return ([], [])
    no = meta.get('neighbor_order', [])
    if not no:
        return ([], [])
    fv = meta.get('fill_value', -999.0)
    xp = meta.get('training_X_path')
    if not xp or not os.path.exists(xp):
        return ([], [])
    try:
        X_train = np.load(xp, allow_pickle=False)['X'].astype(np.float64)
    except Exception:
        return ([], [])
    params = meta.get('params', {})
    forest = build_forest_sequential(X_train, num_trees=params.get('num_trees',150),
                                     tree_size=params.get('tree_size',1024),
                                     random_seed=params.get('random_seed',0))
    if not forest:
        return ([], [])
    if not meta.get('neighbor_stats'):
        meta['neighbor_stats'] = compute_neighbor_stats(X_train, no, fill_value=fv)

    scores = score_batch(forest, X_detect)
    thresh = meta.get('mean_codisp',0.0) + args_dict.get('threshold_mult',1.0)*meta.get('std_codisp',0.0)

    anom_rows, det_rows = [], []

    # ── FIX: Check EVERY row, not just RRCF-flagged rows ──
    N = X_detect.shape[0]
    for li in range(N):
        feat = X_detect[li]
        ac = float(scores[li])
        oi = orig_indices[li]; dt = dt_raw_list[li]
        rrcf_flagged = ac > thresh

        # Z-score check runs on ALL rows (not gated by RRCF)
        nbrs = detect_abnormal_neighbors(feat, meta,
                                         z_thresh=args_dict.get('z_thresh', 2.0),
                                         min_std=args_dict.get('min_std', 0.1),
                                         fill_value=fv)
        filt = [nb for nb in nbrs
                if float(nb.get('anomaly_score', 0)) > args_dict.get('min_anomaly_score', 4.0)]
        zscore_flagged = len(filt) > 0

        # ── OR logic: report if RRCF flagged OR z-score flagged ──
        if rrcf_flagged or zscore_flagged:
            anom_rows.append({
                'serving_cell_id': sid,
                'row_index': oi,
                'datetime_raw': dt,
                'avg_codisp': ac,
                'threshold': thresh,
                'rrcf_flagged': rrcf_flagged,
                'zscore_flagged': zscore_flagged,
                'abnormal_neighbors': json.dumps(filt, ensure_ascii=False)
            })
            for nb in filt:
                det_rows.append({
                    'serving_cell_id': sid,
                    'row_index': oi,
                    'datetime_raw': dt,
                    'neighbor_id': nb['neighbor_id'],
                    'anomaly_score': nb['anomaly_score'],
                    'rsrp': nb['rsrp'],
                    'rsrq': nb['rsrq'],
                    'rsrp_z': nb.get('rsrp_z', 0.0),
                    'rsrq_z': nb.get('rsrq_z', 0.0),
                    'neighbor_count': nb['neighbor_count']
                })

    del forest; gc.collect()
    return (anom_rows, det_rows)


def _safe_str(v):
    return '' if pd.isna(v) else str(v)

def make_run_output_dir(base):
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    c = os.path.join(base, f"run_{ts}")
    if not os.path.exists(c):
        os.makedirs(c, exist_ok=True); return c
    i = 1
    while True:
        a = os.path.join(base, f"run_{ts}_{i:02d}")
        if not os.path.exists(a):
            os.makedirs(a, exist_ok=True); return a
        i += 1

def load_valid_global_cellids(cell_details_file):
    if not cell_details_file or not os.path.exists(cell_details_file):
        return set()
    ext = os.path.splitext(cell_details_file)[1].lower()
    try:
        df = pd.read_csv(cell_details_file, dtype=str, low_memory=False) if ext=='.csv' else pd.read_excel(cell_details_file, dtype=str, engine='openpyxl')
    except Exception:
        try: df = pd.read_excel(cell_details_file, dtype=str)
        except Exception: return set()
    cols = {str(c).strip().lower(): c for c in df.columns}
    raw_col = cols.get('global_cellid')
    if raw_col is None: return set()
    valid = set()
    for v in df[raw_col]:
        n = normalize_cell_id(v)
        if n: valid.add(n)
    print(f"Loaded {len(valid)} valid Global_Cellid values")
    return valid

def build_invalid_cell_id_summary(inv_df):
    summary = {}
    if inv_df is None or inv_df.shape[0]==0:
        return pd.DataFrame(columns=['abnormal_cell_id','hit_count','source_columns','serving_cells','first_seen','last_seen'])
    for _, row in inv_df.iterrows():
        cl = [c.strip() for c in _safe_str(row.get('invalid_id_columns')).split(',') if c.strip()]
        vl = [v.strip() for v in _safe_str(row.get('invalid_id_values')).split(',') if v.strip()]
        if not cl or not vl: continue
        srv = normalize_cell_id(row.get('serving_cell_id'))
        dt = pd.to_datetime(row.get('_raw_dt', row.get('datetime_raw')), errors='coerce', utc=False)
        for col, val in zip(cl, vl):
            nid = normalize_cell_id(val)
            if not nid: continue
            if nid not in summary:
                summary[nid] = {'hit_count':0,'source_columns':set(),'serving_cells':set(),'first_seen':pd.NaT,'last_seen':pd.NaT}
            s = summary[nid]; s['hit_count'] += 1; s['source_columns'].add(col)
            if srv: s['serving_cells'].add(srv)
            if pd.notna(dt):
                if pd.isna(s['first_seen']) or dt<s['first_seen']: s['first_seen']=dt
                if pd.isna(s['last_seen']) or dt>s['last_seen']: s['last_seen']=dt
    rows = [{'abnormal_cell_id':nid,'hit_count':s['hit_count'],
        'source_columns':','.join(sorted(s['source_columns'])),
        'serving_cells':','.join(sorted(s['serving_cells'])),
        'first_seen':'' if pd.isna(s['first_seen']) else s['first_seen'].isoformat(),
        'last_seen':'' if pd.isna(s['last_seen']) else s['last_seen'].isoformat()} for nid,s in summary.items()]
    if not rows:
        return pd.DataFrame(columns=['abnormal_cell_id','hit_count','source_columns','serving_cells','first_seen','last_seen'])
    return pd.DataFrame(rows).sort_values(['hit_count','abnormal_cell_id'], ascending=[False,True])

def write_table_with_fallback(df, path, smsg, fmsg):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out = pd.DataFrame() if df is None else df
    try:
        if path.lower().endswith('.csv'): out.to_csv(path, index=False)
        else: out.to_excel(path, index=False)
        print(smsg.format(path=path, count=int(out.shape[0]))); return path
    except Exception as e:
        fb = os.path.splitext(path)[0]+'.csv'; out.to_csv(fb, index=False)
        print(fmsg.format(path=fb, error=e, count=int(out.shape[0]))); return fb

def read_tabular_with_fallback(p):
    if not p: return None, None
    cands = [p]
    b,e = os.path.splitext(p)
    if e.lower()=='.xlsx': cands.append(b+'.csv')
    elif e.lower()=='.csv': cands.append(b+'.xlsx')
    for c in cands:
        if not os.path.exists(c): continue
        try:
            if os.path.splitext(c)[1].lower()=='.csv': return pd.read_csv(c, dtype=str, low_memory=False), c
            return pd.read_excel(c, dtype=str, engine='openpyxl'), c
        except Exception:
            try: return pd.read_excel(c, dtype=str), c
            except Exception: pass
    return None, None

def build_final_abnormal_ids_from_records(rp, sp, ip):
    rd, up = read_tabular_with_fallback(rp)
    if rd is None: rd = pd.DataFrame(); up = rp
    sd = build_invalid_cell_id_summary(rd)
    io = sd[['abnormal_cell_id']].copy() if sd.shape[0]>0 else pd.DataFrame(columns=['abnormal_cell_id'])
    write_table_with_fallback(sd, sp, "Saved final abnormal ids ({count}) -> {path}", "Fallback -> {path}")
    write_table_with_fallback(io, ip, "Saved ids only ({count}) -> {path}", "Fallback -> {path}")

def apply_neighbor_window_filter(output_dir, window_minutes=30, min_count=10):
    ap = os.path.join(output_dir,'anomalies.csv')
    dp = os.path.join(output_dir,'neighbor_anomaly_details.csv')
    rp = os.path.join(output_dir,'neighbor_ranked.csv')
    anp = os.path.join(output_dir,'abnormal_neighbors.csv')
    amp = os.path.join(output_dir,'detected_abnormal_mrs.csv')
    wp = os.path.join(output_dir,'detected_windows.csv')
    empty = [anp, amp, wp]
    if not os.path.exists(dp):
        for p in empty: pd.DataFrame().to_csv(p, index=False)
        return
    det = pd.read_csv(dp, low_memory=False)
    if det.shape[0]==0:
        for p in [rp]+empty: pd.DataFrame().to_csv(p, index=False)
        return
    det = det.copy()
    det['_rid'] = np.arange(det.shape[0], dtype=int)
    det['_ts'] = pd.to_datetime(det.get('datetime_raw'), errors='coerce', utc=False)
    v = det[det['_ts'].notna()].copy()
    if v.shape[0]==0:
        for p in [rp]+empty: pd.DataFrame().to_csv(p, index=False)
        return
    w = pd.Timedelta(minutes=int(window_minutes))
    dw = []; keep = set()
    for nid, sub in v.groupby('neighbor_id', sort=False):
        sub = sub.sort_values('_ts')
        if sub.shape[0] < int(min_count): continue
        ts = sub['_ts'].tolist(); ri = sub['_rid'].tolist()
        l = 0
        for r in range(len(ts)):
            while l<=r and (ts[r]-ts[l])>=w: l+=1
            c = r-l+1
            if c>=int(min_count):
                for ii in range(l,r+1): keep.add(int(ri[ii]))
                dw.append({'neighbor_id':_safe_str(nid),'window_start':ts[l],'window_end':ts[l]+w,'anomaly_count':c})
                l+=1
    filt = det[det['_rid'].isin(keep)].drop(columns=['_rid','_ts'], errors='ignore')
    # ── Save filtered to NEW files, don't overwrite originals ──
    dp_filt = dp.replace('.csv', '_filtered.csv')
    filt.to_csv(dp_filt, index=False)
    wdf = pd.DataFrame(dw)
    if wdf.shape[0]>0: wdf = wdf.drop_duplicates().sort_values(['neighbor_id','window_start'])
    wdf.to_csv(wp, index=False)
    if filt.shape[0]==0:
        for p in [rp,anp,amp]: pd.DataFrame().to_csv(p, index=False)
        return
    filt['_sn'] = pd.to_numeric(filt.get('anomaly_score'), errors='coerce')
    filt['_ts'] = pd.to_datetime(filt.get('datetime_raw'), errors='coerce', utc=False)
    ns = filt.groupby('neighbor_id', dropna=False).agg(event_count=('neighbor_id','size'),
        avg_score=('_sn','mean'),max_score=('_sn','max'),first_seen=('_ts','min'),
        last_seen=('_ts','max')).reset_index().sort_values(['event_count','avg_score'],ascending=[False,False])
    ns.to_csv(anp, index=False)
    rk = filt.groupby('neighbor_id', dropna=False).agg(count=('neighbor_id','size'),
        sum_score=('_sn','sum'),avg_score=('_sn','mean'),max_score=('_sn','max')).reset_index()
    rk['examples']='[]'; rk.sort_values('sum_score',ascending=False).to_csv(rp, index=False)
    if os.path.exists(ap):
        an = pd.read_csv(ap, low_memory=False)
        if an.shape[0]>0:
            kc = ['serving_cell_id','row_index','datetime_raw']
            kp = an.merge(filt[kc].drop_duplicates(), on=kc, how='inner')
            # ── Save filtered anomalies to NEW file ──
            ap_filt = ap.replace('.csv', '_filtered.csv')
            kp.to_csv(ap_filt, index=False); kp.to_csv(amp, index=False)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 PROGRESS WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════
class _ProgressParallel(joblib.Parallel):
    """joblib.Parallel subclass with tqdm progress bar."""
    def __init__(self, total_tasks=0, total_rows=0, **kwargs):
        super().__init__(**kwargs)
        self._total_tasks = total_tasks
        self._total_rows = total_rows
        self._completed = 0
        self._rows_done = 0
        self._pbar = None
        self._start_time = time.time()

    def __call__(self, *args, **kwargs):
        if tqdm is not None and self._total_tasks > 0:
            self._pbar = tqdm(total=self._total_tasks,
                              desc="PHASE 2 Scoring",
                              unit="cell",
                              bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} cells [{elapsed}<{remaining}, {rate_fmt}]')
        return super().__call__(*args, **kwargs)

    def print_progress(self):
        if self._pbar is not None:
            self._pbar.update(self.n_completed_tasks - self._completed)
            self._completed = self.n_completed_tasks
        else:
            # Fallback: print text progress every 10 cells
            done = self.n_completed_tasks
            if done > self._completed and (done % 10 == 0 or done == self._total_tasks):
                elapsed = time.time() - self._start_time
                pct = 100.0 * done / max(self._total_tasks, 1)
                if done > 0:
                    eta = elapsed * (self._total_tasks - done) / done
                    print(f"  [{done}/{self._total_tasks}] {pct:.0f}% done, "
                          f"elapsed {elapsed:.0f}s, ETA ~{eta:.0f}s", flush=True)
                self._completed = done

    def _cleanup(self):
        if self._pbar is not None:
            self._pbar.close()


def main():
    parser = argparse.ArgumentParser(description='Cache Pattern + OR-logic RRCF detection v4.0')
    parser.add_argument('--model-dir', default='../model/model_150_1024')
    parser.add_argument('--check-file', default='../data/newnewdetect_30_filtered.csv')
    parser.add_argument('--datetime-col', default='time_timestamp')
    parser.add_argument('--output-dir', default='../output')
    parser.add_argument('--threshold-mult', type=float, default=1.0)
    parser.add_argument('--z-threshold', type=float, default=2.0)
    parser.add_argument('--min-std', type=float, default=0.1)
    parser.add_argument('--min-anomaly-score', type=float, default=4.0)
    parser.add_argument('--n-jobs', type=int, default=-1)
    parser.add_argument('--cell-details-file', default='../data/Cell_Details.csv')
    parser.add_argument('--invalid-id-xlsx', default=None)
    parser.add_argument('--invalid-id-ids-only-xlsx', default=None)
    args = parser.parse_args()

    t0 = time.time()
    od = make_run_output_dir(args.output_dir)
    print(f"Output: {od}")
    print(f"Backend: {'C++ _rrcf_core' if USE_CPP_RRCF else 'Python rrcf (SLOW)'}")
    print(f"Detection logic: RRCF OR z-score (v4.0 Cache Pattern)")

    # ═══ PHASE 1: Preload + features ═══
    print(f"\nPHASE 1: Loading {args.check_file}...")
    p1 = time.time()

    # Step 1a: Load valid cell IDs
    t_step = time.time()
    valid_ids = load_valid_global_cellids(args.cell_details_file)
    print(f"  [1a] Cell whitelist loaded in {time.time()-t_step:.1f}s")

    # Step 1b: Read CSV
    t_step = time.time()
    inv_rows = []
    df = pd.read_csv(args.check_file, dtype=str, low_memory=False)
    print(f"  [1b] {len(df):,} rows loaded in {time.time()-t_step:.1f}s")

    # Step 1c: Normalize columns
    t_step = time.time()
    df = normalize_detection_chunk(df)
    dc = args.datetime_col
    df['_raw_dt'] = df[dc].astype(str) if dc in df.columns else ''
    print(f"  [1c] Columns normalized in {time.time()-t_step:.1f}s")

    # Step 1d: Cell-ID validation (VECTORIZED — fast on 7M rows)
    if valid_ids:
        t_step = time.time()
        nbc, _, _ = get_neighbor_columns()
        ic = ['serving_cell_id'] + [c for c in nbc if c in df.columns]
        ia = pd.Series(False, index=df.index)
        bcm = defaultdict(list); bvm = defaultdict(list)
        for col in ic:
            if col not in df.columns: continue
            # ── VECTORIZED: no .apply() — 30-60x faster on 7M rows ──
            nv = _to_pandas(df[col]).astype(str).str.strip().str.split('.').str[0]
            nv = nv.where(~nv.isin(['', 'nan', 'None', 'NaN', 'none', '<NA>']), '')
            bm = (nv!='') & (~nv.isin(valid_ids))
            ia = ia | bm
            if bm.any():
                for bi in bm[bm].index.tolist():
                    bcm[bi].append(col); bvm[bi].append(nv.loc[bi])
        bc = int(ia.sum())
        if bc > 0:
            bd = df.loc[ia].copy()
            bd['invalid_id_columns'] = bd.index.map(lambda i: ','.join(bcm.get(i,[])))
            bd['invalid_id_values'] = bd.index.map(lambda i: ','.join(bvm.get(i,[])))
            inv_rows.append(bd)
            df = df.loc[~ia].copy()
            print(f"  [1d] Removed {bc:,} invalid cell-id rows in {time.time()-t_step:.1f}s")
        else:
            print(f"  [1d] Cell-ID validation OK ({len(df):,} rows kept) in {time.time()-t_step:.1f}s")

    if 'serving_cell_id' not in df.columns:
        print("ERROR: no serving_cell_id"); return
    df['serving_cell_id'] = df['serving_cell_id'].astype(str).str.split('.').str[0]

    # Step 1e: Load models
    t_step = time.time()
    all_meta = load_all_meta(args.model_dir)
    print(f"  [1e] Models loaded in {time.time()-t_step:.1f}s")

    # Step 1f: Build tasks (feature matrices per cell)
    t_step = time.time()
    tasks = []
    for sid, ds in df.groupby('serving_cell_id', sort=False):
        if sid not in all_meta: continue
        meta = all_meta[sid]
        no = meta.get('neighbor_order', [])
        if not no: continue
        fv = meta.get('fill_value', -999.0)
        dr = ds.reset_index()
        X = build_features_vectorised(dr, no, fill_value=fv)
        if X.shape[0]==0 or X.shape[1]==0: continue
        dtl = dr['_raw_dt'].tolist()
        oi = dr['index'].tolist() if 'index' in dr.columns else list(range(len(dr)))
        tasks.append((sid, X, dtl, oi, meta))

    # Sort tasks by row count DESCENDING for better load balancing
    tasks.sort(key=lambda t: t[1].shape[0], reverse=True)

    p1t = time.time()-p1
    tr = sum(t[1].shape[0] for t in tasks)
    print(f"  [1f] {len(tasks)} cells, {tr:,} rows prepared in {time.time()-t_step:.1f}s")
    print(f"PHASE 1 COMPLETE: {p1t:.1f}s total")

    # Show top-5 largest cells
    if tasks:
        print(f"\n  Top-5 largest cells:")
        for i, (s, X, _, _, _) in enumerate(tasks[:5]):
            print(f"    {i+1}. Cell {s}: {X.shape[0]:,} rows, {X.shape[1]} features")

    del df; gc.collect()

    # ═══ PHASE 2: Parallel scoring with PROGRESS BAR ═══
    nj = args.n_jobs
    if nj <= 0:
        import multiprocessing
        nj = max(1, multiprocessing.cpu_count()+1+nj)
    nj = max(1, nj)
    ad = {'threshold_mult':args.threshold_mult,'z_thresh':args.z_threshold,
          'min_std':args.min_std,'min_anomaly_score':args.min_anomaly_score}

    print(f"\nPHASE 2: Scoring {tr:,} rows across {len(tasks)} cells using {nj} workers...")
    print(f"  z-score checks ALL rows (catches poisoned RSRP/RSRQ)")
    print(f"  Backend: {'C++ _rrcf_core (25x fast)' if USE_CPP_RRCF else 'Python rrcf (slow)'}")
    p2 = time.time()

    # Use progress-aware parallel executor
    parallel = _ProgressParallel(
        total_tasks=len(tasks),
        total_rows=tr,
        n_jobs=nj,
        backend='loky',
        verbose=0  # We handle progress ourselves
    )
    results = parallel(
        joblib.delayed(_detect_one_cell)(s, X, d, o, m, ad)
        for s, X, d, o, m in tasks
    )
    # Cleanup progress bar
    parallel._cleanup()

    p2t = time.time()-p2
    rps = tr / max(p2t, 0.001)
    print(f"\nPHASE 2 COMPLETE: {p2t:.1f}s ({rps:,.0f} rows/sec)")

    # ═══ PHASE 3: Write results ═══
    print(f"\nPHASE 3: Writing results...")
    p3 = time.time()
    ap = os.path.join(od,'anomalies.csv')
    dp = os.path.join(od,'neighbor_anomaly_details.csv')
    ix = args.invalid_id_xlsx or os.path.join(od,'abnormal_cell_id_mr_records.xlsx')
    isx = os.path.splitext(ix)[0]+'_final_ids.xlsx'
    iox = args.invalid_id_ids_only_xlsx or os.path.splitext(ix)[0]+'_ids_only.xlsx'

    aa, ad_list = [], []
    for r in results:
        if r is None: continue
        aa.extend(r[0]); ad_list.extend(r[1])

    # Count detection types
    rrcf_only = sum(1 for a in aa if a.get('rrcf_flagged') and not a.get('zscore_flagged'))
    zscore_only = sum(1 for a in aa if not a.get('rrcf_flagged') and a.get('zscore_flagged'))
    both_flagged = sum(1 for a in aa if a.get('rrcf_flagged') and a.get('zscore_flagged'))

    (pd.DataFrame(aa) if aa else pd.DataFrame(columns=['serving_cell_id','row_index','datetime_raw',
        'avg_codisp','threshold','rrcf_flagged','zscore_flagged','abnormal_neighbors'])).to_csv(ap, index=False)
    (pd.DataFrame(ad_list) if ad_list else pd.DataFrame(columns=['serving_cell_id','row_index',
        'datetime_raw','neighbor_id','anomaly_score','rsrp','rsrq','rsrp_z','rsrq_z','neighbor_count'])).to_csv(dp, index=False)

    if ad_list:
        agg = defaultdict(lambda: {'count':0,'sum_score':0.0,'max_score':0.0})
        for d in ad_list:
            a = agg[d['neighbor_id']]; a['count']+=1
            a['sum_score']+=float(d['anomaly_score'])
            if float(d['anomaly_score'])>a['max_score']: a['max_score']=float(d['anomaly_score'])
        pd.DataFrame([{'neighbor_id':n,'count':v['count'],'sum_score':v['sum_score'],
            'avg_score':v['sum_score']/v['count'],'max_score':v['max_score'],'examples':'[]'}
            for n,v in agg.items()]).sort_values('sum_score',ascending=False).to_csv(
            os.path.join(od,'neighbor_ranked.csv'), index=False)

    rp_written = ix
    if inv_rows:
        idf = pd.concat(inv_rows, ignore_index=True)
        try: idf.to_excel(ix, index=False)
        except Exception:
            rp_written = os.path.splitext(ix)[0]+'.csv'; idf.to_csv(rp_written, index=False)
    else:
        try: pd.DataFrame().to_excel(ix, index=False)
        except Exception:
            rp_written = os.path.splitext(ix)[0]+'.csv'; pd.DataFrame().to_csv(rp_written, index=False)
    build_final_abnormal_ids_from_records(rp_written, isx, iox)
    apply_neighbor_window_filter(od, window_minutes=30, min_count=10)

    p3t = time.time() - p3
    tt = time.time()-t0
    rps_total = tr/max(tt, 0.001)
    print(f"\n{'='*60}")
    print(f"DETECTION COMPLETE (v4.0 — Cache + OR-logic + Progress)")
    print(f"{'='*60}")
    print(f"  Rows scored     : {tr:,}")
    print(f"  Total anomalies : {len(aa):,}")
    print(f"    RRCF only     : {rrcf_only:,}")
    print(f"    Z-score only  : {zscore_only:,}  <- catches poisoned RSRP")
    print(f"    Both flagged  : {both_flagged:,}")
    print(f"  Cells processed : {len(tasks)}")
    print(f"  Phase 1 (load)  : {p1t:.0f}s")
    print(f"  Phase 2 (score) : {p2t:.0f}s ({nj} workers)")
    print(f"  Phase 3 (write) : {p3t:.0f}s")
    print(f"  Total           : {tt:.1f}s ({rps_total:,.0f} rows/sec)")
    print(f"  Backend         : {'C++' if USE_CPP_RRCF else 'Python'}")
    print(f"  Model loading   : Cache Pattern (combined_meta.pkl)")
    print(f"  Output          : {od}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
