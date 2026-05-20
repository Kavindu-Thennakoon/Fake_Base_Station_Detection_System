"""
ML Bridge - Connects Django backend to the ml_service detection/training pipelines.

Modes:
    - PRODUCTION: calls detect_rrcf_v4.py / train_rrcf_gpu_mp_v4.py via subprocess
    - DEMO:       generates realistic fake data for frontend development & testing

Set ML_DEMO_MODE=True in settings.py to enable demo mode.
"""

import os
import random
import subprocess
import logging
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
            "--cell-details-file", cell_details,
            "--output-dir", self.output_dir,
            "--threshold-mult", str(threshold_mult),
            "--z-threshold", str(z_threshold),
            "--min-anomaly-score", str(min_anomaly_score),
            "--n-jobs", str(n_jobs),
        ]

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
            "--cell-details-file", cell_details,
            "--num-trees", str(num_trees),
            "--tree-size", str(tree_size),
            "--min-samples", str(min_samples),
            "--n-jobs", str(n_jobs),
        ]

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
    # DEMO — DETECTION (generates realistic fake data)
    # ==================================================================
    def _run_detection_demo(
        self, check_file, threshold_mult, z_threshold, min_anomaly_score
    ):
        """Generate realistic fake detection data directly in DB."""
        run_id = f"demo_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        run = DetectionRun.objects.create(
            run_id=run_id,
            status="running",
            input_file=check_file,
            threshold_mult=threshold_mult,
            z_threshold=z_threshold,
            min_anomaly_score=min_anomaly_score,
        )

        # --- Serving cells (realistic Sri Lankan cell IDs) ---
        serving_cells = [
            "41301_12845", "41301_12846", "41301_12847",
            "41301_33901", "41301_33902", "41301_44510",
            "41301_44511", "41301_55620", "41301_55621",
            "41301_66730",
        ]
        # Legitimate neighbor cells
        legit_neighbors = [
            "41301_12900", "41301_12901", "41301_12902",
            "41301_33950", "41301_33951", "41301_44560",
            "41301_44561", "41301_55670", "41301_55671",
            "41301_66780",
        ]
        # Fake base station cell IDs (the FBS!)
        fbs_cells = ["99999_00001", "99999_00002"]

        base_time = timezone.now() - timedelta(hours=2)
        anomaly_objects = []
        neighbor_detail_objects = []

        # --- Generate anomalies ---
        num_anomalies = random.randint(25, 60)
        for i in range(num_anomalies):
            cell = random.choice(serving_cells)
            dt = base_time + timedelta(minutes=random.randint(0, 120))

            # 60% flagged by both layers, 25% RRCF only, 15% Z-score only
            roll = random.random()
            if roll < 0.60:
                rrcf_flag, zscore_flag = True, True
            elif roll < 0.85:
                rrcf_flag, zscore_flag = True, False
            else:
                rrcf_flag, zscore_flag = False, True

            mean_c = random.uniform(3.0, 8.0)
            std_c = random.uniform(1.0, 3.0)
            threshold = mean_c + threshold_mult * std_c

            if rrcf_flag:
                avg_codisp = threshold + random.uniform(0.5, 12.0)
            else:
                avg_codisp = threshold - random.uniform(0.1, 1.0)

            anomaly_objects.append(
                Anomaly(
                    run=run,
                    serving_cell_id=cell,
                    row_index=random.randint(1000, 500000),
                    datetime_raw=dt,
                    avg_codisp=round(avg_codisp, 4),
                    threshold=round(threshold, 4),
                    rrcf_flagged=rrcf_flag,
                    zscore_flagged=zscore_flag,
                )
            )

        Anomaly.objects.bulk_create(anomaly_objects)

        # Refresh to get IDs
        created_anomalies = list(
            Anomaly.objects.filter(run=run).order_by("id")
        )

        # --- Generate neighbor details for each anomaly ---
        for anomaly in created_anomalies:
            # 1-3 legitimate neighbors (normal)
            num_legit = random.randint(1, 3)
            for _ in range(num_legit):
                nbr = random.choice(legit_neighbors)
                rsrp = random.uniform(-95, -75)
                rsrq = random.uniform(-12, -6)
                rsrp_z = random.uniform(-1.5, 1.5)
                rsrq_z = random.uniform(-1.5, 1.5)
                score = (rsrp_z**2 + rsrq_z**2) ** 0.5

                neighbor_detail_objects.append(
                    NeighborAnomalyDetail(
                        anomaly=anomaly,
                        serving_cell_id=anomaly.serving_cell_id,
                        neighbor_id=nbr,
                        anomaly_score=round(score, 4),
                        rsrp=round(rsrp, 1),
                        rsrq=round(rsrq, 1),
                        rsrp_z=round(rsrp_z, 4),
                        rsrq_z=round(rsrq_z, 4),
                    )
                )

            # 1 FBS neighbor (abnormal signal)
            if anomaly.zscore_flagged:
                fbs = random.choice(fbs_cells)
                rsrp = random.uniform(-55, -44)  # Abnormally strong
                rsrq = random.uniform(-5, -3)     # Abnormally good
                rsrp_z = random.uniform(4.0, 8.0)
                rsrq_z = random.uniform(3.5, 7.0)
                score = (rsrp_z**2 + rsrq_z**2) ** 0.5

                neighbor_detail_objects.append(
                    NeighborAnomalyDetail(
                        anomaly=anomaly,
                        serving_cell_id=anomaly.serving_cell_id,
                        neighbor_id=fbs,
                        anomaly_score=round(score, 4),
                        rsrp=round(rsrp, 1),
                        rsrq=round(rsrq, 1),
                        rsrp_z=round(rsrp_z, 4),
                        rsrq_z=round(rsrq_z, 4),
                    )
                )

        if neighbor_detail_objects:
            NeighborAnomalyDetail.objects.bulk_create(
                neighbor_detail_objects, batch_size=1000
            )

        # --- Suspicious neighbors (ranked) ---
        all_suspicious = {}
        for detail in NeighborAnomalyDetail.objects.filter(
            anomaly__run=run
        ):
            if detail.neighbor_id not in all_suspicious:
                all_suspicious[detail.neighbor_id] = {
                    "sum_score": 0,
                    "count": 0,
                    "cells": set(),
                }
            all_suspicious[detail.neighbor_id]["sum_score"] += (
                detail.anomaly_score
            )
            all_suspicious[detail.neighbor_id]["count"] += 1
            all_suspicious[detail.neighbor_id]["cells"].add(
                detail.serving_cell_id
            )

        for nbr_id, data in all_suspicious.items():
            SuspiciousNeighbor.objects.create(
                run=run,
                neighbor_id=nbr_id,
                sum_score=round(data["sum_score"], 4),
                occurrence_count=data["count"],
                affected_serving_cells=sorted(data["cells"]),
            )

        # --- Detected windows (for FBS cells only) ---
        for fbs in fbs_cells:
            fbs_anomalies = [
                a for a in created_anomalies
                if a.zscore_flagged
                and NeighborAnomalyDetail.objects.filter(
                    anomaly=a, neighbor_id=fbs
                ).exists()
            ]

            if len(fbs_anomalies) >= 3:
                times = sorted(
                    [a.datetime_raw for a in fbs_anomalies if a.datetime_raw]
                )
                if times:
                    for cell in serving_cells[:3]:
                        DetectedWindow.objects.create(
                            run=run,
                            serving_cell_id=cell,
                            neighbor_id=fbs,
                            window_start=times[0],
                            window_end=times[-1],
                            event_count=len(fbs_anomalies),
                        )

        # --- Abnormal neighbors (window-filtered) ---
        for fbs in fbs_cells:
            windows = DetectedWindow.objects.filter(run=run, neighbor_id=fbs)
            if windows.exists():
                affected_cells = windows.values_list(
                    "serving_cell_id", flat=True
                ).distinct()
                for cell in affected_cells:
                    cell_windows = windows.filter(serving_cell_id=cell)
                    total_events = sum(
                        w.event_count for w in cell_windows
                    )
                    AbnormalNeighbor.objects.create(
                        run=run,
                        serving_cell_id=cell,
                        neighbor_id=fbs,
                        event_count=total_events,
                        window_count=cell_windows.count(),
                    )

        # --- Finalize run ---
        run.status = "completed"
        run.completed_at = timezone.now()
        run.total_anomalies = num_anomalies
        run.total_cells_scanned = len(serving_cells)
        run.total_rows_scanned = random.randint(100000, 500000)
        run.output_dir = "DEMO_MODE"
        run.error_log = "Demo mode — no actual ML pipeline executed."
        run.save()

        # --- Auto-generate alerts ---
        self._generate_alerts(run)

        logger.info(
            "DEMO detection complete: %s (%d anomalies, %d alerts)",
            run_id, num_anomalies, run.alerts.count(),
        )
        return run

    # ==================================================================
    # DEMO — TRAINING
    # ==================================================================
    def _run_training_demo(
        self, train_file, num_trees, tree_size, min_samples
    ):
        """Generate fake CellModel records in DB."""
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

        run.status = "completed"
        run.completed_at = timezone.now()
        run.total_cells_trained = len(demo_cells)
        run.error_log = "Demo mode — no actual training executed."
        run.save()

        logger.info("DEMO training complete: %s (%d cells)", run_id, len(demo_cells))
        return run

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