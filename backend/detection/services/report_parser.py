"""
Report Parser - Reads CSV output files from detect_rrcf_v4.py
and populates Django database models.

Output files parsed (from ml_service/output/run_YYYYMMDD_HHMMSS/):
    - anomalies.csv              → Anomaly model
    - neighbor_anomaly_details.csv → NeighborAnomalyDetail model
    - neighbor_ranked.csv        → SuspiciousNeighbor model
    - detected_windows.csv       → DetectedWindow model
    - abnormal_neighbors.csv     → AbnormalNeighbor model

Each parser method handles FileNotFoundError gracefully so that
missing files (e.g. 0 anomalies = no detected_windows.csv) do not
crash the pipeline.
"""

import os
import logging

import pandas as pd
from django.utils import timezone

from detection.models import (
    DetectionRun,
    Anomaly,
    NeighborAnomalyDetail,
    SuspiciousNeighbor,
    DetectedWindow,
    AbnormalNeighbor,
)

logger = logging.getLogger(__name__)


class ReportParser:
    """Parse ML pipeline output CSVs into Django DB."""

    def __init__(self, run: DetectionRun, output_dir: str):
        self.run = run
        self.output_dir = output_dir

    def parse_all(self):
        """Run all parsers in order."""
        logger.info("Parsing results from: %s", self.output_dir)
        self.parse_anomalies()
        self.parse_neighbor_details()
        self.parse_suspicious_neighbors()
        self.parse_detected_windows()
        self.parse_abnormal_neighbors()
        logger.info("Parsing complete for run: %s", self.run.run_id)

    # ------------------------------------------------------------------
    # anomalies.csv
    # Columns: serving_cell_id, row_index, datetime_raw,
    #          avg_codisp, threshold, rrcf_flagged, zscore_flagged
    # ------------------------------------------------------------------
    def parse_anomalies(self):
        """Parse anomalies.csv into Anomaly model records."""
        path = os.path.join(self.output_dir, "anomalies.csv")
        try:
            df = pd.read_csv(path)
        except FileNotFoundError:
            logger.warning("anomalies.csv not found at %s", path)
            return
        except Exception as e:
            logger.error("Error reading anomalies.csv: %s", e)
            return

        logger.info("Parsing %d anomaly rows", len(df))
        objects = []

        for _, row in df.iterrows():
            # Parse datetime safely
            dt_raw = None
            raw_val = row.get("datetime_raw")
            if pd.notna(raw_val):
                try:
                    dt_raw = pd.to_datetime(raw_val)
                    if dt_raw.tzinfo is None:
                        dt_raw = timezone.make_aware(dt_raw)
                except Exception:
                    dt_raw = None

            objects.append(
                Anomaly(
                    run=self.run,
                    serving_cell_id=str(row.get("serving_cell_id", "")),
                    row_index=int(row.get("row_index", 0)),
                    datetime_raw=dt_raw,
                    avg_codisp=float(row.get("avg_codisp", 0.0)),
                    threshold=float(row.get("threshold", 0.0)),
                    rrcf_flagged=bool(row.get("rrcf_flagged", False)),
                    zscore_flagged=bool(row.get("zscore_flagged", False)),
                )
            )

        Anomaly.objects.bulk_create(objects, batch_size=1000)

        # Update run stats
        self.run.total_anomalies = len(objects)
        self.run.save(update_fields=["total_anomalies"])
        logger.info("Created %d Anomaly records", len(objects))

    # ------------------------------------------------------------------
    # neighbor_anomaly_details.csv
    # Columns: serving_cell_id, row_index, neighbor_id, anomaly_score,
    #          rsrp, rsrq, rsrp_z, rsrq_z
    # ------------------------------------------------------------------
    def parse_neighbor_details(self):
        """Parse neighbor_anomaly_details.csv into NeighborAnomalyDetail records."""
        path = os.path.join(self.output_dir, "neighbor_anomaly_details.csv")
        try:
            df = pd.read_csv(path)
        except FileNotFoundError:
            logger.warning("neighbor_anomaly_details.csv not found at %s", path)
            return
        except Exception as e:
            logger.error("Error reading neighbor_anomaly_details.csv: %s", e)
            return

        logger.info("Parsing %d neighbor detail rows", len(df))

        # Build lookup: (serving_cell_id, row_index) → Anomaly object
        anomaly_lookup = {}
        for a in Anomaly.objects.filter(run=self.run):
            key = (str(a.serving_cell_id), a.row_index)
            anomaly_lookup[key] = a

        objects = []
        for _, row in df.iterrows():
            cell_id = str(row.get("serving_cell_id", ""))
            row_idx = (
                int(row.get("row_index", 0))
                if "row_index" in df.columns
                else 0
            )

            # Try exact match first
            anomaly = anomaly_lookup.get((cell_id, row_idx))

            # Fallback: find first anomaly for this serving cell
            if anomaly is None:
                fallback_key = next(
                    (k for k in anomaly_lookup if k[0] == cell_id),
                    None,
                )
                anomaly = anomaly_lookup.get(fallback_key)

            if anomaly is None:
                continue

            objects.append(
                NeighborAnomalyDetail(
                    anomaly=anomaly,
                    serving_cell_id=cell_id,
                    neighbor_id=str(row.get("neighbor_id", "")),
                    anomaly_score=float(row.get("anomaly_score", 0.0)),
                    rsrp=self._safe_float(row.get("rsrp")),
                    rsrq=self._safe_float(row.get("rsrq")),
                    rsrp_z=self._safe_float(row.get("rsrp_z")),
                    rsrq_z=self._safe_float(row.get("rsrq_z")),
                )
            )

        if objects:
            NeighborAnomalyDetail.objects.bulk_create(objects, batch_size=1000)
        logger.info("Created %d NeighborAnomalyDetail records", len(objects))

    # ------------------------------------------------------------------
    # neighbor_ranked.csv
    # Columns: neighbor_id, sum_score, count
    #          (+ possibly serving_cells as comma-separated string)
    # ------------------------------------------------------------------
    def parse_suspicious_neighbors(self):
        """Parse neighbor_ranked.csv into SuspiciousNeighbor records."""
        path = os.path.join(self.output_dir, "neighbor_ranked.csv")
        try:
            df = pd.read_csv(path)
        except FileNotFoundError:
            logger.warning("neighbor_ranked.csv not found at %s", path)
            return
        except Exception as e:
            logger.error("Error reading neighbor_ranked.csv: %s", e)
            return

        logger.info("Parsing %d suspicious neighbor rows", len(df))

        for _, row in df.iterrows():
            # Parse affected serving cells if column exists
            affected = []
            if "serving_cells" in df.columns and pd.notna(
                row.get("serving_cells")
            ):
                raw = str(row["serving_cells"])
                affected = [c.strip() for c in raw.split(",") if c.strip()]

            SuspiciousNeighbor.objects.create(
                run=self.run,
                neighbor_id=str(row.get("neighbor_id", "")),
                sum_score=float(row.get("sum_score", 0.0)),
                occurrence_count=int(row.get("count", 0)),
                affected_serving_cells=affected,
            )

        logger.info("Created %d SuspiciousNeighbor records", len(df))

    # ------------------------------------------------------------------
    # detected_windows.csv
    # Columns: serving_cell_id, neighbor_id, window_start,
    #          window_end, event_count
    # ------------------------------------------------------------------
    def parse_detected_windows(self):
        """Parse detected_windows.csv into DetectedWindow records."""
        path = os.path.join(self.output_dir, "detected_windows.csv")
        try:
            df = pd.read_csv(path)
        except FileNotFoundError:
            logger.warning("detected_windows.csv not found at %s", path)
            return
        except Exception as e:
            logger.error("Error reading detected_windows.csv: %s", e)
            return

        logger.info("Parsing %d detected window rows", len(df))

        for _, row in df.iterrows():
            ws = None
            we = None
            try:
                if pd.notna(row.get("window_start")):
                    ws = pd.to_datetime(row["window_start"])
                    if ws.tzinfo is None:
                        ws = timezone.make_aware(ws)
                if pd.notna(row.get("window_end")):
                    we = pd.to_datetime(row["window_end"])
                    if we.tzinfo is None:
                        we = timezone.make_aware(we)
            except Exception:
                pass

            DetectedWindow.objects.create(
                run=self.run,
                serving_cell_id=str(row.get("serving_cell_id", "")),
                neighbor_id=str(row.get("neighbor_id", "")),
                window_start=ws,
                window_end=we,
                event_count=int(row.get("event_count", 0)),
            )

        logger.info("Created %d DetectedWindow records", len(df))

    # ------------------------------------------------------------------
    # abnormal_neighbors.csv
    # Columns: serving_cell_id, neighbor_id, event_count, window_count
    # ------------------------------------------------------------------
    def parse_abnormal_neighbors(self):
        """Parse abnormal_neighbors.csv into AbnormalNeighbor records."""
        path = os.path.join(self.output_dir, "abnormal_neighbors.csv")
        try:
            df = pd.read_csv(path)
        except FileNotFoundError:
            logger.warning("abnormal_neighbors.csv not found at %s", path)
            return
        except Exception as e:
            logger.error("Error reading abnormal_neighbors.csv: %s", e)
            return

        logger.info("Parsing %d abnormal neighbor rows", len(df))

        for _, row in df.iterrows():
            AbnormalNeighbor.objects.create(
                run=self.run,
                serving_cell_id=str(row.get("serving_cell_id", "")),
                neighbor_id=str(row.get("neighbor_id", "")),
                event_count=int(row.get("event_count", 0)),
                window_count=int(row.get("window_count", 0)),
            )

        logger.info("Created %d AbnormalNeighbor records", len(df))

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_float(val):
        """
        Convert value to float, returning None for NaN, missing,
        or the -999.0 sentinel used by the ML pipeline for missing
        RSRP/RSRQ measurements.
        """
        try:
            v = float(val)
            if pd.isna(v) or v == -999.0:
                return None
            return v
        except (ValueError, TypeError):
            return None