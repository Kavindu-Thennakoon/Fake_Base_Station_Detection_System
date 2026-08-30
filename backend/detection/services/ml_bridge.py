"""
ML Bridge - Connects Django backend to the ml_service detection/training pipelines.

Modes:
    - PRODUCTION: calls detect_rrcf_v4.py / train_rrcf_gpu_mp_v4.py via subprocess
    - DEMO:       generates realistic fake data for frontend development & testing

Set ML_DEMO_MODE=True in settings.py to enable demo mode.
"""

import csv
import os
import random
import subprocess
import logging
from collections import defaultdict
from datetime import datetime, timedelta

import joblib
from django.conf import settings
from django.utils import timezone

from detection.models import (
    DetectionRun,
    TrainingRun,
    CellModel,
    Anomaly,
    NeighborAnomalyDetail,
    SuspiciousNeighbor,
    DetectedWindow,
    AbnormalNeighbor,
)
from detection.services.report_parser import ReportParser
from alerts.models import Alert

logger = logging.getLogger(__name__)


class MLBridge:
    """Bridge between Django REST API and the ml_service scripts."""

    def __init__(self):
        self.ml_service_dir = getattr(settings, "ML_SERVICE_DIR", "")
        self.model_dir = getattr(settings, "ML_MODEL_DIR", "")
        self.output_dir = getattr(settings, "ML_OUTPUT_DIR", "")
        self.scripts_dir = getattr(settings, "ML_SCRIPTS_DIR", "")
        self.data_dir = getattr(settings, "ML_DATA_DIR", "")
        self.demo_mode = getattr(settings, "ML_DEMO_MODE", True)

    # ==================================================================
    # DETECTION
    # ==================================================================
    def run_detection(
        self,
        check_file,
        threshold_mult=1.0,
        z_threshold=2.0,
        min_anomaly_score=4.0,
        n_jobs=-1,
    ):
        """
        Trigger the detection pipeline.

        DEMO mode:  generates realistic fake anomaly data directly in DB.
        PROD mode:  calls detect_rrcf_v4.py via subprocess, then parses CSVs.
        """
        if self.demo_mode:
            return self._run_detection_demo(
                check_file, threshold_mult, z_threshold, min_anomaly_score
            )
        return self._run_detection_production(
            check_file, threshold_mult, z_threshold, min_anomaly_score, n_jobs
        )

    # ==================================================================
    # TRAINING
    # ==================================================================
    def run_training(
        self,
        train_file,
        model_dir=None,
        num_trees=150,
        tree_size=1024,
        min_samples=50,
        n_jobs=4,
    ):
        """
        Trigger the training pipeline.

        DEMO mode:  generates fake CellModel records directly in DB.
        PROD mode:  calls train_rrcf_gpu_mp_v4.py via subprocess.
        """
        if self.demo_mode:
            return self._run_training_demo(
                train_file, num_trees, tree_size, min_samples
            )
        return self._run_training_production(
            train_file, model_dir, num_trees, tree_size, min_samples, n_jobs
        )

    # ==================================================================
    # MODEL STATUS
    # ==================================================================
    def get_model_status(self):
        """
        Return model health summary.

        DEMO mode:  returns status from DB CellModel records.
        PROD mode:  loads combined_meta.pkl from disk.
        """
        if self.demo_mode:
            return self._get_model_status_demo()

        combined_path = os.path.join(self.model_dir, "combined_meta.pkl")

        if not os.path.exists(combined_path):
            return {
                "status": "no_model",
                "total_cells": 0,
                "model_path": combined_path,
                "cells": [],
            }

        try:
            meta = joblib.load(combined_path)
            cells_summary = []
            for cell_id, cell_data in meta.items():
                cells_summary.append({
                    "serving_cell_id": str(cell_id),
                    "K": cell_data.get("K", 0),
                    "mean_codisp": cell_data.get("mean_codisp", 0.0),
                    "std_codisp": cell_data.get("std_codisp", 0.0),
                    "num_neighbors": len(
                        cell_data.get("neighbor_order", [])
                    ),
                })
            return {
                "status": "loaded",
                "total_cells": len(meta),
                "model_path": combined_path,
                "model_size_mb": round(
                    os.path.getsize(combined_path) / (1024 * 1024), 2
                ),
                "cells": cells_summary,
            }
        except Exception as e:
            logger.exception("Failed to load combined_meta.pkl: %s", e)
            return {"status": "error", "total_cells": 0, "error": str(e)}

    # ==================================================================
    # PRODUCTION — DETECTION
    # ==================================================================
    def _run_detection_production(
        self, check_file, threshold_mult, z_threshold, min_anomaly_score, n_jobs
    ):
        """Call detect_rrcf_v4.py via subprocess."""
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        run = DetectionRun.objects.create(
            run_id=run_id,
            status="running",
            input_file=check_file,
            threshold_mult=threshold_mult,
            z_threshold=z_threshold,
            min_anomaly_score=min_anomaly_score,
        )

        cell_details = os.path.join(self.data_dir, "Cell_Details.csv")
        script = os.path.join(self.scripts_dir, "detect_rrcf_v4.py")

        cmd = [
            "python", script,
            "--model-dir", self.model_dir,
            "--check-file", check_file,
            "--output-dir", self.output_dir,
            "--threshold-mult", str(threshold_mult),
            "--z-threshold", str(z_threshold),
            "--min-anomaly-score", str(min_anomaly_score),
            "--n-jobs", str(n_jobs),
        ]
        
        if os.path.exists(cell_details):
            cmd.extend(["--cell-details-file", cell_details])

        try:
            logger.info("Starting detection: %s", " ".join(cmd))
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
                cwd=self.scripts_dir,
            )

            if result.returncode == 0:
                output_run_dir = self._find_latest_run_dir()
                run.output_dir = output_run_dir or ""
                run.status = "completed"
                run.completed_at = timezone.now()
                run.error_log = result.stdout[-2000:] if result.stdout else ""
                run.save()

                if output_run_dir:
                    parser = ReportParser(run, output_run_dir)
                    parser.parse_all()

                self._generate_alerts(run)
                logger.info("Detection completed: %s", run_id)
            else:
                run.status = "failed"
                run.error_log = (result.stderr or result.stdout or "")[-3000:]
                run.completed_at = timezone.now()
                run.save()
                logger.error("Detection failed: %s", result.stderr[:500])

        except subprocess.TimeoutExpired:
            run.status = "failed"
            run.error_log = "Detection timed out after 3600 seconds."
            run.completed_at = timezone.now()
            run.save()
        except Exception as e:
            run.status = "failed"
            run.error_log = str(e)[:3000]
            run.completed_at = timezone.now()
            run.save()
            logger.exception("Detection error: %s", e)

        return run

    # ==================================================================
    # PRODUCTION — TRAINING
    # ==================================================================
    def _run_training_production(
        self, train_file, model_dir, num_trees, tree_size, min_samples, n_jobs
    ):
        """Call train_rrcf_gpu_mp_v4.py via subprocess."""
        run_id = f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        target_model_dir = model_dir or self.model_dir

        run = TrainingRun.objects.create(
            run_id=run_id,
            status="running",
            train_file=train_file,
            model_dir=target_model_dir,
            num_trees=num_trees,
            tree_size=tree_size,
            min_samples=min_samples,
        )

        cell_details = os.path.join(self.data_dir, "Cell_Details.csv")
        script = os.path.join(self.scripts_dir, "train_rrcf_gpu_mp_v4.py")

        cmd = [
            "python", script,
            "--train-file", train_file,
            "--model-dir", target_model_dir,
            "--num-trees", str(num_trees),
            "--tree-size", str(tree_size),
            "--min-samples", str(min_samples),
            "--n-jobs", str(n_jobs),
        ]

        if os.path.exists(cell_details):
            cmd.extend(["--cell-details-file", cell_details])

        try:
            logger.info("Starting training: %s", " ".join(cmd))
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=7200,
                cwd=self.scripts_dir,
            )

            if result.returncode == 0:
                run.status = "completed"
                run.completed_at = timezone.now()
                run.error_log = result.stdout[-2000:] if result.stdout else ""
                run.save()

                self._sync_cell_models(target_model_dir)
                run.total_cells_trained = CellModel.objects.count()
                run.save()
                logger.info("Training completed: %s", run_id)
            else:
                run.status = "failed"
                run.error_log = (result.stderr or result.stdout or "")[-3000:]
                run.completed_at = timezone.now()
                run.save()

        except subprocess.TimeoutExpired:
            run.status = "failed"
            run.error_log = "Training timed out after 7200 seconds."
            run.completed_at = timezone.now()
            run.save()
        except Exception as e:
            run.status = "failed"
            run.error_log = str(e)[:3000]
            run.completed_at = timezone.now()
            run.save()
            logger.exception("Training error: %s", e)

        return run

    # ==================================================================
    # DEMO — DETECTION (reads uploaded CSV, scores against trained models)
    # ==================================================================
    def _run_detection_demo(
        self, check_file, threshold_mult, z_threshold, min_anomaly_score
    ):
        """
        Read the uploaded CSV and run Z-score detection against trained CellModels.

        For each row: look up the serving cell's trained model, compute per-neighbor
        Z-scores from the baseline stats, and flag rows where any neighbor exceeds
        min_anomaly_score. RRCF scores are simulated (would need the actual forest).
        Falls back to synthetic data only if CSV parsing fails.
        """
        import math

        run_id = f"demo_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        run = DetectionRun.objects.create(
            run_id=run_id,
            status="running",
            input_file=check_file,
            threshold_mult=threshold_mult,
            z_threshold=z_threshold,
            min_anomaly_score=min_anomaly_score,
        )

        try:
            result = self._detect_from_csv(
                run, check_file, threshold_mult, z_threshold, min_anomaly_score
            )
            run.status = "completed"
            run.completed_at = timezone.now()
            run.total_rows_scanned = result["rows_scanned"]
            run.total_anomalies = result["anomalies"]
            run.total_cells_scanned = result["cells_scanned"]
            run.output_dir = "DEMO_MODE"
            run.error_log = (
                f"Demo detection — parsed {check_file}, scanned {result['rows_scanned']} rows, "
                f"found {result['anomalies']} anomalies across {result['cells_scanned']} cells."
            )
            run.save()
        except Exception as e:
            logger.exception("CSV detection failed, falling back to synthetic: %s", e)
            self._detect_synthetic_fallback(run, threshold_mult)
            run.error_log = f"Demo detection — CSV parse failed ({e}), used synthetic fallback."
            run.save()

        self._build_suspicious_neighbors(run)
        self._build_windows(run)
        self._generate_alerts(run)

        logger.info(
            "DEMO detection complete: %s (%d anomalies, %d alerts)",
            run_id, run.total_anomalies, run.alerts.count(),
        )
        return run

    def _detect_from_csv(
        self, run, check_file, threshold_mult, z_threshold, min_anomaly_score
    ):
        """Read CSV, score each row against trained CellModel baselines."""
        import math

        models = {m.serving_cell_id: m for m in CellModel.objects.all()}
        if not models:
            raise ValueError("No trained CellModels in DB — train first")

        with open(check_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            header_map = {h.strip().lower(): h for h in (reader.fieldnames or [])}

            serving_col = self._resolve_column("serving_cell_id", header_map)
            enodeb_col = self._resolve_column("enodebid", header_map)
            cellid_col = self._resolve_column("cellid", header_map)
            dt_col = header_map.get("datetime_raw") or header_map.get("time_timestamp")

            nbr_id_cols = [self._resolve_column(f"nbr_cell_{i}_id", header_map) for i in range(1, 5)]
            nbr_rp_cols = [self._resolve_column(f"nbr_cell_{i}_rsrp", header_map) for i in range(1, 5)]
            nbr_rq_cols = [self._resolve_column(f"nbr_cell_{i}_rsrq", header_map) for i in range(1, 5)]

            rows_scanned = 0
            cells_seen = set()
            anomaly_objs = []
            detail_objs = []
            eps = 1e-6

            for row_idx, row in enumerate(reader):
                rows_scanned += 1
                sid = self._compute_serving_cell_id(row, serving_col, enodeb_col, cellid_col)
                if not sid:
                    continue

                model = models.get(sid)
                if not model:
                    continue

                cells_seen.add(sid)

                dt_str = row.get(dt_col, "") if dt_col else ""
                dt_val = None
                if dt_str:
                    try:
                        from django.utils.dateparse import parse_datetime
                        dt_val = parse_datetime(dt_str)
                        if dt_val is None:
                            dt_val = timezone.make_aware(
                                datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M:%S")
                            )
                    except Exception:
                        dt_val = None

                threshold = model.mean_codisp + threshold_mult * model.std_codisp
                avg_codisp = random.gauss(model.mean_codisp, model.std_codisp)
                rrcf_flagged = avg_codisp > threshold

                neighbor_details = []
                zscore_flagged = False

                for i in range(4):
                    id_col = nbr_id_cols[i]
                    rp_col = nbr_rp_cols[i]
                    rq_col = nbr_rq_cols[i]

                    nid = row.get(id_col, "").strip() if id_col else ""
                    if not nid or nid in ("", "nan", "NaN"):
                        continue
                    nid = nid.split(".")[0]

                    try:
                        rsrp = float(row.get(rp_col, "")) if rp_col else None
                    except (ValueError, TypeError):
                        rsrp = None
                    try:
                        rsrq = float(row.get(rq_col, "")) if rq_col else None
                    except (ValueError, TypeError):
                        rsrq = None

                    stats = model.neighbor_stats.get(nid, {})
                    rsrp_z = 0.0
                    rsrq_z = 0.0

                    if rsrp is not None and stats.get("rsrp_mean") is not None:
                        std = stats.get("rsrp_std", 0) or eps
                        rsrp_z = abs(rsrp - stats["rsrp_mean"]) / (std + eps)

                    if rsrq is not None and stats.get("rsrq_mean") is not None:
                        std = stats.get("rsrq_std", 0) or eps
                        rsrq_z = abs(rsrq - stats["rsrq_mean"]) / (std + eps)

                    combined = math.sqrt(rsrp_z**2 + rsrq_z**2)

                    if not stats:
                        combined = min_anomaly_score + 2.0
                        rsrp_z = z_threshold + 1.0

                    if combined >= min_anomaly_score:
                        zscore_flagged = True

                    neighbor_details.append({
                        "nid": nid, "rsrp": rsrp, "rsrq": rsrq,
                        "rsrp_z": rsrp_z, "rsrq_z": rsrq_z,
                        "score": combined,
                    })

                if not rrcf_flagged and not zscore_flagged:
                    continue

                anomaly = Anomaly(
                    run=run,
                    serving_cell_id=sid,
                    row_index=row_idx,
                    datetime_raw=dt_val,
                    avg_codisp=round(avg_codisp, 4),
                    threshold=round(threshold, 4),
                    rrcf_flagged=rrcf_flagged,
                    zscore_flagged=zscore_flagged,
                )
                anomaly_objs.append(anomaly)

        Anomaly.objects.bulk_create(anomaly_objs, batch_size=1000)

        created = list(Anomaly.objects.filter(run=run).order_by("id"))

        detail_idx = 0
        with open(check_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            header_map = {h.strip().lower(): h for h in (reader.fieldnames or [])}
            serving_col = self._resolve_column("serving_cell_id", header_map)
            enodeb_col = self._resolve_column("enodebid", header_map)
            cellid_col = self._resolve_column("cellid", header_map)
            nbr_id_cols = [self._resolve_column(f"nbr_cell_{i}_id", header_map) for i in range(1, 5)]
            nbr_rp_cols = [self._resolve_column(f"nbr_cell_{i}_rsrp", header_map) for i in range(1, 5)]
            nbr_rq_cols = [self._resolve_column(f"nbr_cell_{i}_rsrq", header_map) for i in range(1, 5)]

            anomaly_by_row = {a.row_index: a for a in created}

            for row_idx, row in enumerate(reader):
                if row_idx not in anomaly_by_row:
                    continue
                anomaly = anomaly_by_row[row_idx]
                sid = anomaly.serving_cell_id
                model = models.get(sid)

                for i in range(4):
                    id_col = nbr_id_cols[i]
                    rp_col = nbr_rp_cols[i]
                    rq_col = nbr_rq_cols[i]

                    nid = row.get(id_col, "").strip() if id_col else ""
                    if not nid or nid in ("", "nan", "NaN"):
                        continue
                    nid = nid.split(".")[0]

                    try:
                        rsrp = float(row.get(rp_col, "")) if rp_col else None
                    except (ValueError, TypeError):
                        rsrp = None
                    try:
                        rsrq = float(row.get(rq_col, "")) if rq_col else None
                    except (ValueError, TypeError):
                        rsrq = None

                    stats = (model.neighbor_stats or {}).get(nid, {}) if model else {}
                    rsrp_z = rsrq_z = 0.0
                    eps = 1e-6

                    if rsrp is not None and stats.get("rsrp_mean") is not None:
                        rsrp_z = abs(rsrp - stats["rsrp_mean"]) / ((stats.get("rsrp_std", 0) or eps) + eps)
                    if rsrq is not None and stats.get("rsrq_mean") is not None:
                        rsrq_z = abs(rsrq - stats["rsrq_mean"]) / ((stats.get("rsrq_std", 0) or eps) + eps)

                    import math
                    combined = math.sqrt(rsrp_z**2 + rsrq_z**2)
                    if not stats:
                        combined = min_anomaly_score + 2.0
                        rsrp_z = z_threshold + 1.0

                    detail_objs.append(NeighborAnomalyDetail(
                        anomaly=anomaly,
                        serving_cell_id=sid,
                        neighbor_id=nid,
                        anomaly_score=round(combined, 4),
                        rsrp=round(rsrp, 1) if rsrp is not None else None,
                        rsrq=round(rsrq, 1) if rsrq is not None else None,
                        rsrp_z=round(rsrp_z, 4),
                        rsrq_z=round(rsrq_z, 4),
                    ))

        if detail_objs:
            NeighborAnomalyDetail.objects.bulk_create(detail_objs, batch_size=1000)

        return {
            "rows_scanned": rows_scanned,
            "anomalies": len(created),
            "cells_scanned": len(cells_seen),
        }

    def _detect_synthetic_fallback(self, run, threshold_mult):
        """Fallback: generate synthetic anomalies if CSV parsing fails."""
        serving_cells = list(
            CellModel.objects.values_list("serving_cell_id", flat=True)[:10]
        ) or ["41301_12845", "41301_12846", "41301_33901"]

        base_time = timezone.now() - timedelta(hours=2)
        objs = []
        for i in range(random.randint(20, 50)):
            cell = random.choice(serving_cells)
            mean_c = random.uniform(3.0, 8.0)
            std_c = random.uniform(1.0, 3.0)
            threshold = mean_c + threshold_mult * std_c
            rrcf_flag = random.random() < 0.7
            avg_codisp = threshold + random.uniform(0.5, 10.0) if rrcf_flag else threshold - random.uniform(0.1, 1.0)
            objs.append(Anomaly(
                run=run, serving_cell_id=cell, row_index=i,
                datetime_raw=base_time + timedelta(minutes=random.randint(0, 120)),
                avg_codisp=round(avg_codisp, 4), threshold=round(threshold, 4),
                rrcf_flagged=rrcf_flag, zscore_flagged=random.random() < 0.5,
            ))
        Anomaly.objects.bulk_create(objs)
        run.status = "completed"
        run.completed_at = timezone.now()
        run.total_anomalies = len(objs)
        run.total_cells_scanned = len(set(a.serving_cell_id for a in objs))
        run.total_rows_scanned = len(objs)

    def _build_suspicious_neighbors(self, run):
        """Aggregate NeighborAnomalyDetail into SuspiciousNeighbor records."""
        agg = {}
        for d in NeighborAnomalyDetail.objects.filter(anomaly__run=run):
            if d.neighbor_id not in agg:
                agg[d.neighbor_id] = {"score": 0, "count": 0, "cells": set()}
            agg[d.neighbor_id]["score"] += d.anomaly_score
            agg[d.neighbor_id]["count"] += 1
            agg[d.neighbor_id]["cells"].add(d.serving_cell_id)

        for nbr_id, data in agg.items():
            SuspiciousNeighbor.objects.create(
                run=run, neighbor_id=nbr_id,
                sum_score=round(data["score"], 4),
                occurrence_count=data["count"],
                affected_serving_cells=sorted(data["cells"]),
            )

    def _build_windows(self, run):
        """Build DetectedWindow and AbnormalNeighbor from anomaly clusters."""
        suspicious = SuspiciousNeighbor.objects.filter(
            run=run, sum_score__gte=20
        )
        for sn in suspicious:
            details = NeighborAnomalyDetail.objects.filter(
                anomaly__run=run, neighbor_id=sn.neighbor_id
            ).select_related("anomaly")
            if details.count() < 3:
                continue
            times = sorted([
                d.anomaly.datetime_raw for d in details
                if d.anomaly.datetime_raw
            ])
            if not times:
                continue
            affected = set(d.serving_cell_id for d in details)
            for cell in list(affected)[:5]:
                cell_count = details.filter(serving_cell_id=cell).count()
                DetectedWindow.objects.create(
                    run=run, serving_cell_id=cell, neighbor_id=sn.neighbor_id,
                    window_start=times[0], window_end=times[-1],
                    event_count=cell_count,
                )
                AbnormalNeighbor.objects.create(
                    run=run, serving_cell_id=cell, neighbor_id=sn.neighbor_id,
                    event_count=cell_count, window_count=1,
                )

    # ==================================================================
    # DEMO — TRAINING
    # ==================================================================
    def _run_training_demo(
        self, train_file, num_trees, tree_size, min_samples
    ):
        """
        Process the uploaded CSV to build CellModel records in demo mode.

        Reads serving_cell_id and neighbor columns from the CSV, computes
        real per-cell statistics, and creates/updates CellModel entries.
        Falls back to synthetic data only if the CSV cannot be parsed.
        """
        run_id = f"demo_train_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        run = TrainingRun.objects.create(
            run_id=run_id,
            status="running",
            train_file=train_file,
            model_dir="DEMO_MODE",
            num_trees=num_trees,
            tree_size=tree_size,
            min_samples=min_samples,
        )

        cells_trained = 0
        error_msg = ""

        try:
            cells_trained = self._parse_csv_and_build_models(
                train_file, num_trees, tree_size, min_samples
            )
            error_msg = f"Demo mode — parsed {train_file} and built {cells_trained} cell models."
        except Exception as e:
            logger.warning("CSV parse failed (%s), falling back to synthetic data", e)
            cells_trained = self._build_synthetic_models(num_trees, tree_size)
            error_msg = f"Demo mode — CSV parse failed ({e}), used synthetic data."

        run.status = "completed"
        run.completed_at = timezone.now()
        run.total_cells_trained = cells_trained
        run.error_log = error_msg
        run.save()

        logger.info("DEMO training complete: %s (%d cells)", run_id, cells_trained)
        return run

    # Column aliases: maps normalized name → list of raw dataset alternatives
    COLUMN_ALIASES = {
        "serving_cell_id": ["serving_cell_id"],
        "nbr_cell_1_id": ["nbr_cell_1_id", "eutrancellid1"],
        "nbr_cell_2_id": ["nbr_cell_2_id", "eutrancellid2"],
        "nbr_cell_3_id": ["nbr_cell_3_id", "eutrancellid3"],
        "nbr_cell_4_id": ["nbr_cell_4_id", "eutrancellid4"],
        "nbr_cell_1_rsrp": ["nbr_cell_1_rsrp", "avg_dlrsrp_d1"],
        "nbr_cell_2_rsrp": ["nbr_cell_2_rsrp", "avg_dlrsrp_d2"],
        "nbr_cell_3_rsrp": ["nbr_cell_3_rsrp", "avg_dlrsrp_d3"],
        "nbr_cell_4_rsrp": ["nbr_cell_4_rsrp", "avg_dlrsrp_d4"],
        "nbr_cell_1_rsrq": ["nbr_cell_1_rsrq", "avg_dlrsrq_d1"],
        "nbr_cell_2_rsrq": ["nbr_cell_2_rsrq", "avg_dlrsrq_d2"],
        "nbr_cell_3_rsrq": ["nbr_cell_3_rsrq", "avg_dlrsrq_d3"],
        "nbr_cell_4_rsrq": ["nbr_cell_4_rsrq", "avg_dlrsrq_d4"],
        "enodebid": ["enodebid"],
        "cellid": ["cellid"],
    }

    def _resolve_column(self, target, header_map):
        """Find the actual CSV column name for a target field, checking aliases."""
        for alias in self.COLUMN_ALIASES.get(target, [target]):
            if alias.lower() in header_map:
                return header_map[alias.lower()]
        return None

    def _compute_serving_cell_id(self, row, serving_col, enodeb_col, cellid_col):
        """Get serving_cell_id — directly or computed from enodebid*256+cellid."""
        if serving_col:
            val = row.get(serving_col, "").strip()
            if val:
                return val.split(".")[0]

        if enodeb_col and cellid_col:
            try:
                enb = int(float(row.get(enodeb_col, "")))
                cid = int(float(row.get(cellid_col, "")))
                return str(enb * 256 + cid)
            except (ValueError, TypeError):
                pass
        return ""

    def _parse_csv_and_build_models(
        self, train_file, num_trees, tree_size, min_samples
    ):
        """Read the uploaded CSV and build real CellModel records from its data."""
        import statistics

        cell_data = defaultdict(lambda: {
            "rows": 0,
            "neighbors": defaultdict(lambda: {"rsrp": [], "rsrq": []}),
        })

        with open(train_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            header_map = {h.strip().lower(): h for h in (reader.fieldnames or [])}

            serving_col = self._resolve_column("serving_cell_id", header_map)
            enodeb_col = self._resolve_column("enodebid", header_map)
            cellid_col = self._resolve_column("cellid", header_map)

            if not serving_col and not (enodeb_col and cellid_col):
                raise ValueError(
                    "CSV needs 'serving_cell_id' or 'enodebid'+'cellid' columns"
                )

            nbr_id_cols = [self._resolve_column(f"nbr_cell_{i}_id", header_map) for i in range(1, 5)]
            nbr_rp_cols = [self._resolve_column(f"nbr_cell_{i}_rsrp", header_map) for i in range(1, 5)]
            nbr_rq_cols = [self._resolve_column(f"nbr_cell_{i}_rsrq", header_map) for i in range(1, 5)]

            for row in reader:
                sid = self._compute_serving_cell_id(row, serving_col, enodeb_col, cellid_col)
                if not sid:
                    continue
                cell_data[sid]["rows"] += 1

                for i in range(4):
                    id_col = nbr_id_cols[i]
                    rp_col = nbr_rp_cols[i]
                    rq_col = nbr_rq_cols[i]

                    nid = row.get(id_col, "").strip() if id_col else ""
                    if not nid or nid in ("", "nan", "NaN"):
                        continue
                    nid = nid.split(".")[0]

                    try:
                        rsrp = float(row.get(rp_col, "")) if rp_col else None
                    except (ValueError, TypeError):
                        rsrp = None
                    try:
                        rsrq = float(row.get(rq_col, "")) if rq_col else None
                    except (ValueError, TypeError):
                        rsrq = None

                    if rsrp is not None:
                        cell_data[sid]["neighbors"][nid]["rsrp"].append(rsrp)
                    if rsrq is not None:
                        cell_data[sid]["neighbors"][nid]["rsrq"].append(rsrq)

        cells_built = 0
        for sid, data in cell_data.items():
            if data["rows"] < min_samples:
                continue

            neighbor_order = sorted(data["neighbors"].keys())
            K = len(neighbor_order)
            if K == 0:
                continue

            neighbor_stats = {}
            for nid in neighbor_order:
                nd = data["neighbors"][nid]
                rp = nd["rsrp"]
                rq = nd["rsrq"]
                neighbor_stats[nid] = {
                    "rsrp_mean": round(statistics.mean(rp), 2) if rp else -85.0,
                    "rsrp_std": round(statistics.stdev(rp), 2) if len(rp) > 1 else 5.0,
                    "rsrq_mean": round(statistics.mean(rq), 2) if rq else -10.0,
                    "rsrq_std": round(statistics.stdev(rq), 2) if len(rq) > 1 else 2.5,
                }

            mean_codisp = round(random.uniform(3.0, 8.0), 4)
            std_codisp = round(random.uniform(1.0, 3.0), 4)

            CellModel.objects.update_or_create(
                serving_cell_id=sid,
                defaults={
                    "K": K,
                    "mean_codisp": mean_codisp,
                    "std_codisp": std_codisp,
                    "training_rows": data["rows"],
                    "neighbor_order": neighbor_order,
                    "neighbor_stats": neighbor_stats,
                    "num_trees": num_trees,
                    "tree_size": tree_size,
                },
            )
            cells_built += 1

        if cells_built == 0:
            raise ValueError(f"No cells met min_samples={min_samples} threshold")

        return cells_built

    def _build_synthetic_models(self, num_trees, tree_size):
        """Fallback: generate synthetic CellModel records."""
        demo_cells = [
            "41301_12845", "41301_12846", "41301_12847",
            "41301_33901", "41301_33902", "41301_44510",
            "41301_44511", "41301_55620", "41301_55621",
            "41301_66730",
        ]
        all_neighbors = [
            "41301_12900", "41301_12901", "41301_12902",
            "41301_33950", "41301_33951", "41301_44560",
            "41301_44561", "41301_55670", "41301_55671",
            "41301_66780", "41301_66781", "41301_77800",
        ]

        for cell_id in demo_cells:
            K = random.randint(4, 10)
            neighbors = random.sample(all_neighbors, min(K, len(all_neighbors)))
            neighbor_stats = {}
            for nbr in neighbors:
                neighbor_stats[nbr] = {
                    "rsrp_mean": round(random.uniform(-95, -70), 2),
                    "rsrp_std": round(random.uniform(3.0, 8.0), 2),
                    "rsrq_mean": round(random.uniform(-14, -6), 2),
                    "rsrq_std": round(random.uniform(1.5, 4.0), 2),
                }
            CellModel.objects.update_or_create(
                serving_cell_id=cell_id,
                defaults={
                    "K": K,
                    "mean_codisp": round(random.uniform(3.0, 8.0), 4),
                    "std_codisp": round(random.uniform(1.0, 3.0), 4),
                    "training_rows": random.randint(5000, 50000),
                    "neighbor_order": neighbors,
                    "neighbor_stats": neighbor_stats,
                    "num_trees": num_trees,
                    "tree_size": tree_size,
                },
            )
        return len(demo_cells)

    # ==================================================================
    # DEMO — MODEL STATUS
    # ==================================================================
    def _get_model_status_demo(self):
        """Return model status from DB CellModel records."""
        cells = CellModel.objects.all()

        if not cells.exists():
            return {
                "status": "no_model",
                "total_cells": 0,
                "model_path": "DEMO_MODE",
                "cells": [],
            }

        cells_summary = []
        for cell in cells:
            cells_summary.append({
                "serving_cell_id": cell.serving_cell_id,
                "K": cell.K,
                "mean_codisp": cell.mean_codisp,
                "std_codisp": cell.std_codisp,
                "num_neighbors": cell.K,
            })

        return {
            "status": "loaded",
            "total_cells": cells.count(),
            "model_path": "DEMO_MODE",
            "model_size_mb": 0,
            "cells": cells_summary,
        }

    # ==================================================================
    # SHARED HELPERS
    # ==================================================================
    def _find_latest_run_dir(self):
        """Find the most recent run_* directory in output."""
        if not os.path.exists(self.output_dir):
            return None
        run_dirs = sorted(
            [
                d for d in os.listdir(self.output_dir)
                if d.startswith("run_")
                and os.path.isdir(os.path.join(self.output_dir, d))
            ],
            reverse=True,
        )
        if run_dirs:
            return os.path.join(self.output_dir, run_dirs[0])
        return None

    def _sync_cell_models(self, model_dir=None):
        """Read combined_meta.pkl and sync CellModel records to DB."""
        target = model_dir or self.model_dir
        combined_path = os.path.join(target, "combined_meta.pkl")

        if not os.path.exists(combined_path):
            logger.warning("combined_meta.pkl not found at %s", combined_path)
            return

        try:
            meta = joblib.load(combined_path)
            logger.info("Syncing %d cell models to DB", len(meta))

            for cell_id, cell_data in meta.items():
                raw_stats = cell_data.get("neighbor_stats", {})
                safe_stats = {}
                for nbr_id, nbr_data in raw_stats.items():
                    safe_stats[str(nbr_id)] = {
                        k: float(v) if hasattr(v, "item") else v
                        for k, v in nbr_data.items()
                    }
                params = cell_data.get("params", {})

                CellModel.objects.update_or_create(
                    serving_cell_id=str(cell_id),
                    defaults={
                        "K": int(cell_data.get("K", 0)),
                        "mean_codisp": float(
                            cell_data.get("mean_codisp", 0.0)
                        ),
                        "std_codisp": float(
                            cell_data.get("std_codisp", 0.0)
                        ),
                        "training_rows": int(
                            cell_data.get("training_rows", 0)
                        ),
                        "neighbor_order": [
                            str(n)
                            for n in cell_data.get("neighbor_order", [])
                        ],
                        "neighbor_stats": safe_stats,
                        "num_trees": int(params.get("num_trees", 150)),
                        "tree_size": int(params.get("tree_size", 1024)),
                    },
                )
            logger.info("Cell model sync complete: %d cells", len(meta))
        except Exception as e:
            logger.exception("Failed to sync cell models: %s", e)

    def _generate_alerts(self, run):
        """Auto-generate Alert records from suspicious neighbors."""
        suspicious = SuspiciousNeighbor.objects.filter(run=run).order_by(
            "-sum_score"
        )

        for neighbor in suspicious:
            if neighbor.sum_score >= 50 or neighbor.occurrence_count >= 100:
                severity = "critical"
            elif neighbor.sum_score >= 20 or neighbor.occurrence_count >= 50:
                severity = "high"
            elif neighbor.sum_score >= 10 or neighbor.occurrence_count >= 20:
                severity = "medium"
            else:
                severity = "low"

            affected_count = (
                len(neighbor.affected_serving_cells)
                if neighbor.affected_serving_cells
                else 0
            )

            Alert.objects.create(
                run=run,
                neighbor_id=neighbor.neighbor_id,
                severity=severity,
                title=(
                    f"Suspicious neighbor cell {neighbor.neighbor_id} detected"
                ),
                description=(
                    f"Cell ID {neighbor.neighbor_id} was flagged "
                    f"{neighbor.occurrence_count} time(s) with a cumulative "
                    f"anomaly score of {neighbor.sum_score:.2f}. "
                    f"Affected serving cells: {affected_count}."
                ),
                affected_cells_count=affected_count,
                peak_anomaly_score=neighbor.sum_score,
            )

        logger.info(
            "Generated %d alerts for run %s",
            suspicious.count(), run.run_id,
        )